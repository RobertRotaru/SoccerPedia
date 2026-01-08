# agent/data_sources.py
import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
import sys
sys.path.append('..')
from config import RATE_LIMIT_DELAY, MAX_REQUESTS_PER_MINUTE, RETRY_ATTEMPTS, RETRY_DELAY, LEAGUE_MAPPINGS
from .cache_manager import CacheManager


class DataSourceManager:
    """
    Centralized manager to decide which data source to use based on query type.
    Priority order: football-data.org -> api-football.com -> web scraping
    """
    
    def __init__(self):
        self.football_data_api_key = os.getenv("FOOTBALL_DATA_API_KEY", "98792b7d8bd64cc5a2c32ea06c7f0de9")
        self.api_football_key = os.getenv("API_FOOTBALL_KEY", "")
        
        # Initialize cache manager
        self.cache_manager = CacheManager(cache_dir="cache", default_ttl=1800)  # 30 minutes default
        
        # Rate limiting
        self.last_request_time = {}
        self.min_interval = RATE_LIMIT_DELAY  # Use config value
        self.request_count = {}  # Track number of requests per minute
        self.max_requests_per_minute = MAX_REQUESTS_PER_MINUTE  # Use config value
        
        # League mappings from config
        self.league_mappings = LEAGUE_MAPPINGS
    
    def _rate_limit(self, source: str):
        """Enhanced rate limiting with request counting"""
        now = time.time()
        current_minute = int(now // 60)
        
        # Initialize request count for this minute
        if source not in self.request_count:
            self.request_count[source] = {}
        
        # Clean old minute data
        self.request_count[source] = {
            minute: count for minute, count in self.request_count[source].items() 
            if minute >= current_minute - 1
        }
        
        # Check requests per minute
        current_requests = self.request_count[source].get(current_minute, 0)
        if current_requests >= self.max_requests_per_minute:
            sleep_time = 60 - (now % 60) + 1  # Wait until next minute
            print(f"Rate limit reached for {source}, waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
            current_minute = int(time.time() // 60)
            current_requests = 0
        
        # Check time-based rate limiting
        if source in self.last_request_time:
            time_since_last = now - self.last_request_time[source]
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                print(f"Time-based rate limiting {source}, sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        # Update counters
        self.last_request_time[source] = time.time()
        self.request_count[source][current_minute] = current_requests + 1
    
    def _make_request(self, url: str, headers: Dict[str, str], params: Dict[str, Any] = None, source: str = "default") -> Optional[Dict]:
        """Make HTTP request with error handling, retries, and rate limiting"""
        self._rate_limit(source)
        
        max_retries = RETRY_ATTEMPTS
        retry_delay = RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=15)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Too many requests
                    print(f"Rate limited by {source}, waiting...")
                    time.sleep(60 * (attempt + 1))  # Exponential backoff
                    continue
                elif response.status_code == 403:
                    print(f"Access forbidden for {source} - check API key")
                    return None
                elif response.status_code == 404:
                    print(f"Resource not found for {source}")
                    return None
                else:
                    print(f"API error {response.status_code}: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"Timeout error for {source}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return None
            except requests.exceptions.ConnectionError:
                print(f"Connection error for {source}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return None
            except requests.exceptions.RequestException as e:
                print(f"Request error for {source}: {e}")
                return None
            except ValueError as e:
                print(f"JSON decode error for {source}: {e}")
                return None
        
        return None
    
    def get_matches(self, league: str = None, date: str = None, status: str = "all", force_live: bool = False) -> Dict[str, Any]:
        """
        Get matches using the best available data source with intelligent fallbacks
        status: 'finished', 'scheduled', 'live', 'all'
        force_live: If True, bypasses cache and fetches fresh data
        """
        # For live data requirements, adjust cache strategy
        if force_live:
            # Bypass cache for live data
            errors = []
            
            # Try football-data.org first (more reliable for European leagues)
            try:
                result = self._get_matches_football_data(league, date, status)
                if result and result.get("matches"):
                    result["fetch_type"] = "live_fetch"
                    return result
                elif result and result.get("error"):
                    errors.append(f"football-data.org: {result['error']}")
            except Exception as e:
                errors.append(f"football-data.org: {str(e)}")
            
            # Fallback to api-football.com
            try:
                result = self._get_matches_api_football(league, date, status)
                if result and result.get("matches"):
                    result["fetch_type"] = "live_fetch"
                    return result
                elif result and result.get("error"):
                    errors.append(f"api-football.com: {result['error']}")
            except Exception as e:
                errors.append(f"api-football.com: {str(e)}")
            
            return {
                "matches": [], 
                "source": "none", 
                "error": "No live data available from any source",
                "detailed_errors": errors,
                "fetch_type": "live_fetch_failed"
            }
        
        # Create cache parameters for non-live requests
        cache_params = {
            'type': 'matches',
            'league': league,
            'date': date,
            'status': status
        }
        
        def fetch_matches_data(type, league, date, status):
            errors = []
            
            # Try football-data.org first (more reliable for European leagues)
            try:
                result = self._get_matches_football_data(league, date, status)
                if result and result.get("matches"):
                    result["fetch_type"] = "cached"
                    return result
                elif result and result.get("error"):
                    errors.append(f"football-data.org: {result['error']}")
            except Exception as e:
                errors.append(f"football-data.org: {str(e)}")
            
            # Fallback to api-football.com
            try:
                result = self._get_matches_api_football(league, date, status)
                if result and result.get("matches"):
                    result["fetch_type"] = "cached"
                    return result
                elif result and result.get("error"):
                    errors.append(f"api-football.com: {result['error']}")
            except Exception as e:
                errors.append(f"api-football.com: {str(e)}")
            
            # If specific date/league failed, try broader search
            if date and not league:
                try:
                    result = self._get_matches_football_data(None, None, status)
                    if result and result.get("matches"):
                        # Filter manually by date
                        filtered_matches = [m for m in result["matches"] if m.get("date") == date]
                        if filtered_matches:
                            result["matches"] = filtered_matches
                            result["source"] += " (filtered)"
                            result["fetch_type"] = "cached"
                            return result
                except Exception as e:
                    errors.append(f"fallback search: {str(e)}")
            
            return {
                "matches": [], 
                "source": "none", 
                "error": "No data available from any source",
                "detailed_errors": errors,
                "fetch_type": "cached"
            }
        
        # Use cache with different TTLs based on status
        if status == "live":
            ttl = 30  # Live matches update frequently - 30 second cache
        elif status == "finished":
            ttl = 1800  # Finished matches don't change - 30 minute cache
        else:
            ttl = 180  # General matches - 3 minute cache
            
        return self.cache_manager.get_or_fetch(cache_params, fetch_matches_data, ttl=ttl)
    
    def _get_matches_football_data(self, league: str = None, date: str = None, status: str = "all") -> Optional[Dict]:
        """Get matches from football-data.org"""
        try:
            if league and league in self.league_mappings:
                url = f"https://api.football-data.org/v4/competitions/{self.league_mappings[league]['football_data']}/matches"
            else:
                url = "https://api.football-data.org/v4/matches"
            
            headers = {"X-Auth-Token": self.football_data_api_key}
            params = {}
            
            if date:
                params["dateFrom"] = date
                params["dateTo"] = date
            
            data = self._make_request(url, headers, params, "football-data")
            if data:
                matches = []
                for match in data.get("matches", []):
                    match_info = {
                        "id": match.get("id"),
                        "date": match.get("utcDate", "")[:10],
                        "time": match.get("utcDate", "")[11:16],
                        "home_team": match.get("homeTeam", {}).get("name", ""),
                        "away_team": match.get("awayTeam", {}).get("name", ""),
                        "home_score": match.get("score", {}).get("fullTime", {}).get("home"),
                        "away_score": match.get("score", {}).get("fullTime", {}).get("away"),
                        "status": match.get("status", ""),
                        "competition": match.get("competition", {}).get("name", ""),
                        "matchday": match.get("matchday")
                    }
                    
                    # Filter by status
                    if status != "all":
                        if status == "finished" and match_info["status"] not in ["FINISHED", "AWARDED"]:
                            continue
                        elif status == "scheduled" and match_info["status"] not in ["SCHEDULED", "TIMED"]:
                            continue
                        elif status == "live" and match_info["status"] not in ["IN_PLAY", "PAUSED"]:
                            continue
                    
                    matches.append(match_info)
                
                return {
                    "matches": matches,
                    "source": "football-data.org",
                    "total": len(matches)
                }
        except Exception as e:
            print(f"Error fetching from football-data.org: {e}")
            return None
    
    def _get_matches_api_football(self, league: str = None, date: str = None, status: str = "all") -> Optional[Dict]:
        """Get matches from api-football.com"""
        if not self.api_football_key:
            return None
        
        try:
            url = "https://v3.football.api-sports.io/fixtures"
            headers = {"X-RapidAPI-Key": self.api_football_key}
            params = {}
            
            if league and league in self.league_mappings:
                params["league"] = self.league_mappings[league]["api_football"]
            
            if date:
                params["date"] = date
            
            if status == "finished":
                params["status"] = "FT"
            elif status == "scheduled":
                params["status"] = "NS"
            elif status == "live":
                params["status"] = "1H-HT-2H"
            
            data = self._make_request(url, headers, params, "api-football")
            if data:
                matches = []
                for fixture in data.get("response", []):
                    match_info = {
                        "id": fixture.get("fixture", {}).get("id"),
                        "date": fixture.get("fixture", {}).get("date", "")[:10],
                        "time": fixture.get("fixture", {}).get("date", "")[11:16],
                        "home_team": fixture.get("teams", {}).get("home", {}).get("name", ""),
                        "away_team": fixture.get("teams", {}).get("away", {}).get("name", ""),
                        "home_score": fixture.get("goals", {}).get("home"),
                        "away_score": fixture.get("goals", {}).get("away"),
                        "status": fixture.get("fixture", {}).get("status", {}).get("long", ""),
                        "competition": fixture.get("league", {}).get("name", ""),
                        "matchday": fixture.get("league", {}).get("round", "")
                    }
                    matches.append(match_info)
                
                return {
                    "matches": matches,
                    "source": "api-football.com",
                    "total": len(matches)
                }
        except Exception as e:
            print(f"Error fetching from api-football.com: {e}")
            return None
    
    def get_standings(self, league: str, season: str = None, force_live: bool = False) -> Dict[str, Any]:
        """
        Get league standings with enhanced error handling and caching
        force_live: If True, bypasses cache and fetches fresh data
        """
        # For live data requirements, adjust cache strategy
        if force_live:
            # Bypass cache for live data
            errors = []
            
            # Try football-data.org first
            try:
                result = self._get_standings_football_data(league, season)
                if result and result.get("standings"):
                    result["fetch_type"] = "live_fetch"
                    return result
                elif result and result.get("error"):
                    errors.append(f"football-data.org: {result['error']}")
            except Exception as e:
                errors.append(f"football-data.org: {str(e)}")
            
            # Fallback to api-football.com
            try:
                result = self._get_standings_api_football(league, season)
                if result and result.get("standings"):
                    result["fetch_type"] = "live_fetch"
                    return result
                elif result and result.get("error"):
                    errors.append(f"api-football.com: {result['error']}")
            except Exception as e:
                errors.append(f"api-football.com: {str(e)}")
            
            return {
                "standings": [], 
                "source": "none", 
                "error": "No live standings data available",
                "detailed_errors": errors,
                "fetch_type": "live_fetch_failed"
            }
        
        # Create cache parameters for non-live requests
        cache_params = {
            'type': 'standings',
            'league': league,
            'season': season or datetime.now().year
        }
        
        def fetch_standings_data(type, league, season):
            errors = []
            
            # Try football-data.org first
            try:
                result = self._get_standings_football_data(league, season)
                if result and result.get("standings"):
                    result["fetch_type"] = "cached"
                    return result
                elif result and result.get("error"):
                    errors.append(f"football-data.org: {result['error']}")
            except Exception as e:
                errors.append(f"football-data.org: {str(e)}")
            
            # Fallback to api-football.com
            try:
                result = self._get_standings_api_football(league, season)
                if result and result.get("standings"):
                    result["fetch_type"] = "cached"
                    return result
                elif result and result.get("error"):
                    errors.append(f"api-football.com: {result['error']}")
            except Exception as e:
                errors.append(f"api-football.com: {str(e)}")
            
            return {
                "standings": [], 
                "source": "none", 
                "error": "No standings data available",
                "detailed_errors": errors,
                "fetch_type": "cached"
            }
        
        # Standings change less frequently - cache for 30 minutes for live accuracy
        return self.cache_manager.get_or_fetch(cache_params, fetch_standings_data, ttl=1800)
    
    def _get_standings_football_data(self, league: str, season: str = None) -> Optional[Dict]:
        """Get standings from football-data.org"""
        if league not in self.league_mappings:
            return None
        
        try:
            url = f"https://api.football-data.org/v4/competitions/{self.league_mappings[league]['football_data']}/standings"
            headers = {"X-Auth-Token": self.football_data_api_key}
            params = {}
            if season:
                params["season"] = season
            
            data = self._make_request(url, headers, params, "football-data")
            if data and data.get("standings"):
                standings = []
                for table in data["standings"]:
                    if table.get("type") == "TOTAL":
                        for team in table.get("table", []):
                            standings.append({
                                "position": team.get("position"),
                                "team": team.get("team", {}).get("name"),
                                "played": team.get("playedGames"),
                                "won": team.get("won"),
                                "drawn": team.get("draw"),
                                "lost": team.get("lost"),
                                "goals_for": team.get("goalsFor"),
                                "goals_against": team.get("goalsAgainst"),
                                "goal_difference": team.get("goalDifference"),
                                "points": team.get("points")
                            })
                
                return {
                    "standings": standings,
                    "source": "football-data.org",
                    "league": self.league_mappings[league]["name"],
                    "season": data.get("season", {}).get("startDate", "")[:4]
                }
        except Exception as e:
            print(f"Error fetching standings from football-data.org: {e}")
            return None
    
    def _get_standings_api_football(self, league: str, season: str = None) -> Optional[Dict]:
        """Get standings from api-football.com"""
        if not self.api_football_key or league not in self.league_mappings:
            return None
        
        try:
            url = "https://v3.football.api-sports.io/standings"
            headers = {"X-RapidAPI-Key": self.api_football_key}
            params = {"league": self.league_mappings[league]["api_football"]}
            if season:
                params["season"] = season
            else:
                params["season"] = datetime.now().year
            
            data = self._make_request(url, headers, params, "api-football")
            if data and data.get("response"):
                standings = []
                for league_data in data["response"]:
                    for team in league_data.get("league", {}).get("standings", [[]])[0]:
                        standings.append({
                            "position": team.get("rank"),
                            "team": team.get("team", {}).get("name"),
                            "played": team.get("all", {}).get("played"),
                            "won": team.get("all", {}).get("win"),
                            "drawn": team.get("all", {}).get("draw"),
                            "lost": team.get("all", {}).get("lose"),
                            "goals_for": team.get("all", {}).get("goals", {}).get("for"),
                            "goals_against": team.get("all", {}).get("goals", {}).get("against"),
                            "goal_difference": team.get("goalsDiff"),
                            "points": team.get("points")
                        })
                
                return {
                    "standings": standings,
                    "source": "api-football.com",
                    "league": self.league_mappings[league]["name"],
                    "season": season or datetime.now().year
                }
        except Exception as e:
            print(f"Error fetching standings from api-football.com: {e}")
            return None


class WikipediaScraper:
    """Scraper for Wikipedia football-related data"""
    
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/wiki/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_player(self, player_name: str) -> Dict[str, Any]:
        """Search for player information on Wikipedia"""
        try:
            search_url = f"https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": f"{player_name} footballer",
                "srlimit": 3
            }
            
            response = self.session.get(search_url, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get("query", {}).get("search", [])
                
                if results:
                    # Get the first result
                    page_title = results[0]["title"]
                    return self._get_player_details(page_title)
            
            return {"error": "Player not found on Wikipedia"}
        except Exception as e:
            return {"error": f"Wikipedia search error: {e}"}
    
    def _get_player_details(self, page_title: str) -> Dict[str, Any]:
        """Get detailed player information from Wikipedia page"""
        try:
            url = f"{self.base_url}{quote(page_title)}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract infobox data
                infobox = soup.find('table', class_='infobox')
                player_info = {"name": page_title, "source": "Wikipedia"}
                
                if infobox:
                    rows = infobox.find_all('tr')
                    for row in rows:
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            key = th.get_text().strip().lower()
                            value = td.get_text().strip()
                            
                            # Map common fields
                            if 'born' in key or 'birth' in key:
                                player_info['birth_date'] = value
                            elif 'position' in key:
                                player_info['position'] = value
                            elif 'current team' in key or 'club' in key:
                                player_info['current_team'] = value
                            elif 'height' in key:
                                player_info['height'] = value
                            elif 'nationality' in key or 'national' in key:
                                player_info['nationality'] = value
                
                # Extract first paragraph for biography
                first_para = soup.find('p')
                if first_para:
                    player_info['biography'] = first_para.get_text().strip()[:500] + "..."
                
                return player_info
            
            return {"error": "Could not access Wikipedia page"}
        except Exception as e:
            return {"error": f"Wikipedia scraping error: {e}"}


class TransfermarktScraper:
    """Scraper for Transfermarkt data"""
    
    def __init__(self):
        self.base_url = "https://www.transfermarkt.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_player(self, player_name: str) -> Dict[str, Any]:
        """Search for player on Transfermarkt"""
        try:
            search_url = f"{self.base_url}/schnellsuche/ergebnis/schnellsuche"
            params = {"query": player_name}
            
            response = self.session.get(search_url, params=params)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find player links in search results
                player_links = soup.find_all('a', href=re.compile(r'/.*?/profil/spieler/\d+'))
                
                if player_links:
                    player_url = self.base_url + player_links[0]['href']
                    return self._get_player_market_value(player_url)
            
            return {"error": "Player not found on Transfermarkt"}
        except Exception as e:
            return {"error": f"Transfermarkt search error: {e}"}
    
    def search_multi_club_careers(self, club1: str, club2: str = None) -> Dict[str, Any]:
        """Search for players who played for multiple clubs"""
        try:
            # Build search queries for multi-club careers
            queries = []
            if club2:
                queries = [
                    f"{club1} {club2} players",
                    f"players {club1} to {club2}",
                    f"{club1} former players {club2}"
                ]
            else:
                queries = [f"{club1} players", f"{club1} squad"]
            
            results = []
            for query in queries[:2]:  # Limit to avoid rate limits
                search_result = self.search_player(query)
                if search_result and not search_result.get("error"):
                    results.append(search_result)
                time.sleep(1)  # Rate limiting
            
            if results:
                return {
                    "multi_club_results": results,
                    "query_clubs": [club1, club2] if club2 else [club1],
                    "source": "Transfermarkt"
                }
            else:
                return {"error": f"No multi-club career data found for {club1}" + (f" and {club2}" if club2 else "")}
                
        except Exception as e:
            return {"error": f"Multi-club search error: {e}"}
    
    def _get_player_market_value(self, player_url: str) -> Dict[str, Any]:
        """Get player market value and transfer data"""
        try:
            response = self.session.get(player_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                player_info = {"source": "Transfermarkt", "url": player_url}
                
                # Extract market value
                market_value_elem = soup.find('a', class_='data-header__market-value-wrapper')
                if market_value_elem:
                    player_info['market_value'] = market_value_elem.get_text().strip()
                
                # Extract basic info
                info_table = soup.find('table', class_='auflistung')
                if info_table:
                    rows = info_table.find_all('tr')
                    for row in rows:
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            key = th.get_text().strip().lower()
                            value = td.get_text().strip()
                            
                            if 'age' in key:
                                player_info['age'] = value
                            elif 'position' in key:
                                player_info['position'] = value
                            elif 'current club' in key:
                                player_info['current_club'] = value
                
                return player_info
            
            return {"error": "Could not access Transfermarkt page"}
        except Exception as e:
            return {"error": f"Transfermarkt scraping error: {e}"}