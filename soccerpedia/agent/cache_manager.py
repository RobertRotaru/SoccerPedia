# agent/cache_manager.py
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import hashlib


class CacheManager:
    """
    Manages in-memory and file-based caching to reduce API calls
    """
    
    def __init__(self, cache_dir: str = "cache", default_ttl: int = 3600):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl  # Time to live in seconds (1 hour default)
        self.memory_cache = {}
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _generate_cache_key(self, data: Dict[str, Any]) -> str:
        """Generate a unique cache key from request parameters"""
        # Sort the dictionary to ensure consistent keys
        sorted_data = json.dumps(data, sort_keys=True)
        return hashlib.md5(sorted_data.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> str:
        """Get the file path for a cache entry"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _is_cache_valid(self, timestamp: float, ttl: int = None) -> bool:
        """Check if cache entry is still valid"""
        ttl = ttl or self.default_ttl
        return time.time() - timestamp < ttl
    
    def get(self, cache_key: str, ttl: int = None) -> Optional[Any]:
        """Get data from cache (memory first, then file)"""
        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if self._is_cache_valid(entry['timestamp'], ttl):
                return entry['data']
            else:
                # Remove expired entry
                del self.memory_cache[cache_key]
        
        # Check file cache
        cache_file = self._get_cache_file_path(cache_key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                
                if self._is_cache_valid(entry['timestamp'], ttl):
                    # Load back to memory cache
                    self.memory_cache[cache_key] = entry
                    return entry['data']
                else:
                    # Remove expired file
                    os.remove(cache_file)
            except (json.JSONDecodeError, KeyError, OSError):
                # Remove corrupted cache file
                try:
                    os.remove(cache_file)
                except:
                    pass
        
        return None
    
    def set(self, cache_key: str, data: Any, ttl: int = None) -> None:
        """Set data in both memory and file cache"""
        entry = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl or self.default_ttl
        }
        
        # Store in memory
        self.memory_cache[cache_key] = entry
        
        # Store in file
        cache_file = self._get_cache_file_path(cache_key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not write to cache file {cache_file}: {e}")
    
    def get_or_fetch(self, params: Dict[str, Any], fetch_function, ttl: int = None):
        """Get data from cache or fetch it using the provided function"""
        cache_key = self._generate_cache_key(params)
        
        # Try to get from cache first
        cached_data = self.get(cache_key, ttl)
        if cached_data is not None:
            print(f"Cache hit for {cache_key[:8]}...")
            return cached_data
        
        # Cache miss - fetch data
        print(f"Cache miss for {cache_key[:8]}... fetching...")
        data = fetch_function(**params)
        
        # Cache the result if successful
        if data and not data.get('error'):
            self.set(cache_key, data, ttl)
        
        return data
    
    def clear_expired(self) -> int:
        """Clear expired cache entries and return count of cleared items"""
        cleared_count = 0
        current_time = time.time()
        
        # Clear memory cache
        expired_keys = []
        for key, entry in self.memory_cache.items():
            if not self._is_cache_valid(entry['timestamp'], entry.get('ttl')):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            cleared_count += 1
        
        # Clear file cache
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            entry = json.load(f)
                        
                        if not self._is_cache_valid(entry['timestamp'], entry.get('ttl')):
                            os.remove(filepath)
                            cleared_count += 1
                    except:
                        # Remove corrupted files
                        try:
                            os.remove(filepath)
                            cleared_count += 1
                        except:
                            pass
        
        return cleared_count
    
    def clear_all(self) -> None:
        """Clear all cache data"""
        self.memory_cache.clear()
        
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    os.remove(filepath)
                except:
                    pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        memory_count = len(self.memory_cache)
        file_count = 0
        
        if os.path.exists(self.cache_dir):
            file_count = len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')])
        
        return {
            'memory_entries': memory_count,
            'file_entries': file_count,
            'cache_dir': self.cache_dir
        }


class BatchDataFetcher:
    """
    Batches related data requests to minimize API calls
    """
    
    def __init__(self, data_manager, cache_manager: CacheManager):
        self.data_manager = data_manager
        self.cache_manager = cache_manager
    
    def get_comprehensive_league_data(self, league: str, season: str = None) -> Dict[str, Any]:
        """
        Fetch comprehensive data for a league in one go:
        - Recent matches
        - Upcoming matches  
        - Standings
        - Live matches
        """
        cache_params = {
            'type': 'comprehensive_league',
            'league': league,
            'season': season,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        def fetch_comprehensive_data(type, league, season, date):
            print(f"Fetching comprehensive data for {league}...")
            
            results = {
                'league': league,
                'season': season,
                'fetched_at': datetime.now().isoformat(),
                'data': {}
            }
            
            try:
                # Get recent finished matches (last 14 days)
                recent_matches = []
                for days_back in range(0, 15):
                    check_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                    match_result = self.data_manager.get_matches(league=league, date=check_date, status="finished")
                    if match_result.get("matches"):
                        recent_matches.extend(match_result["matches"])
                
                # Sort by date (most recent first)
                recent_matches.sort(key=lambda x: x.get("date", ""), reverse=True)
                results['data']['recent_matches'] = recent_matches[:20]  # Keep top 20
                
                # Get upcoming matches
                upcoming_result = self.data_manager.get_matches(league=league, status="scheduled")
                results['data']['upcoming_matches'] = upcoming_result.get("matches", [])[:10]
                
                # Get standings
                standings_result = self.data_manager.get_standings(league=league, season=season)
                results['data']['standings'] = standings_result.get("standings", [])
                
                # Get live matches
                live_result = self.data_manager.get_matches(league=league, status="live")
                results['data']['live_matches'] = live_result.get("matches", [])
                
                results['success'] = True
                return results
                
            except Exception as e:
                results['error'] = str(e)
                results['success'] = False
                return results
        
        # Use cache with 30 minute TTL for comprehensive data
        return self.cache_manager.get_or_fetch(cache_params, fetch_comprehensive_data, ttl=1800)
    
    def get_player_comparison_data(self, player1: str, player2: str) -> Dict[str, Any]:
        """
        Fetch comparison data for two players efficiently
        """
        cache_params = {
            'type': 'player_comparison',
            'player1': player1.lower(),
            'player2': player2.lower(),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        def fetch_comparison_data(type, player1, player2, date):
            print(f"Fetching comparison data for {player1} vs {player2}...")
            
            from .data_sources import WikipediaScraper, TransfermarktScraper
            
            wiki_scraper = WikipediaScraper()
            tm_scraper = TransfermarktScraper()
            
            results = {
                'player1': player1,
                'player2': player2,
                'fetched_at': datetime.now().isoformat(),
                'data': {}
            }
            
            try:
                # Get data for both players
                for i, player in enumerate([player1, player2], 1):
                    player_data = {}
                    
                    # Wikipedia data
                    wiki_data = wiki_scraper.search_player(player)
                    if not wiki_data.get("error"):
                        player_data['wikipedia'] = wiki_data
                    
                    # Transfermarkt data
                    tm_data = tm_scraper.search_player(player)
                    if not tm_data.get("error"):
                        player_data['transfermarkt'] = tm_data
                    
                    results['data'][f'player{i}'] = player_data
                
                results['success'] = True
                return results
                
            except Exception as e:
                results['error'] = str(e)
                results['success'] = False
                return results
        
        # Use cache with 6 hour TTL for player data (changes less frequently)
        return self.cache_manager.get_or_fetch(cache_params, fetch_comparison_data, ttl=21600)