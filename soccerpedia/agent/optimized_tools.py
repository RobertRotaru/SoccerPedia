# agent/optimized_tools.py
import json
from datetime import datetime, timedelta
from langchain.tools import tool
from .data_sources import DataSourceManager, WikipediaScraper, TransfermarktScraper
from .cache_manager import CacheManager, BatchDataFetcher

# Initialize optimized data source managers
data_manager = DataSourceManager()
cache_manager = CacheManager()
batch_fetcher = BatchDataFetcher(data_manager, cache_manager)
wiki_scraper = WikipediaScraper()
transfermarkt_scraper = TransfermarktScraper()


@tool
def get_current_date() -> str:
    """
    Returns the current date in YYYY-MM-DD format.
    """
    return datetime.now().strftime("%Y-%m-%d")


@tool
def get_latest_premier_league_results(limit: int = 10) -> str:
    """
    Get the most recent Premier League results using cached data to avoid rate limits.
    This tool specifically focuses on getting the latest completed matches.
    
    Args:
        limit: Maximum number of matches to return (default: 10)
    """
    try:
        # Use batch fetcher to get comprehensive PL data efficiently
        comprehensive_data = batch_fetcher.get_comprehensive_league_data("PL")
        
        if not comprehensive_data.get('success'):
            return f"Error fetching Premier League data: {comprehensive_data.get('error', 'Unknown error')}"
        
        recent_matches = comprehensive_data['data'].get('recent_matches', [])
        
        if not recent_matches:
            return "No recent Premier League matches found"
        
        # Take the most recent matches
        latest_matches = recent_matches[:limit]
        
        response = f"**🏆 LATEST PREMIER LEAGUE RESULTS** (Most Recent {len(latest_matches)} matches)\n\n"
        
        current_date = None
        for match in latest_matches:
            # Group by date for better readability
            if match['date'] != current_date:
                current_date = match['date']
                response += f"**📅 {current_date}:**\n"
            
            if match["home_score"] is not None and match["away_score"] is not None:
                score = f"{match['home_score']}-{match['away_score']}"
            else:
                score = "vs"
            
            response += f"⚽ {match['home_team']} {score} {match['away_team']}"
            if match.get('matchday'):
                response += f" - MD{match['matchday']}"
            response += "\n"
        
        response += f"\n*Data from cache - {comprehensive_data['fetched_at'][:16]}*"
        return response
    
    except Exception as e:
        return f"Error fetching latest Premier League results: {str(e)}"


@tool
def get_latest_matches_any_league(league: str = None, limit: int = 10) -> str:
    """
    Get the most recent finished matches from any league using efficient caching.
    
    Args:
        league: League code (PL, BL1, SA, PD, FL1, CL, WC) or None for all leagues
        limit: Maximum number of matches to return (default: 10)
    """
    try:
        if league:
            # Use batch fetcher for specific league
            comprehensive_data = batch_fetcher.get_comprehensive_league_data(league)
            
            if not comprehensive_data.get('success'):
                return f"Error fetching {league} data: {comprehensive_data.get('error', 'Unknown error')}"
            
            recent_matches = comprehensive_data['data'].get('recent_matches', [])
            league_name = data_manager.league_mappings.get(league, {}).get('name', league)
        else:
            # For all leagues, use regular cached call
            cache_params = {
                'type': 'latest_all_leagues',
                'limit': limit,
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
            def fetch_all_leagues_matches(type, limit, date):
                all_matches = []
                for days_back in range(0, 7):  # Check last 7 days
                    check_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                    result = data_manager.get_matches(date=check_date, status="finished")
                    if result.get("matches"):
                        all_matches.extend(result["matches"])
                
                # Sort by date and take latest
                all_matches.sort(key=lambda x: x.get("date", ""), reverse=True)
                return {'matches': all_matches[:limit], 'success': True}
            
            cached_result = cache_manager.get_or_fetch(cache_params, fetch_all_leagues_matches, ttl=600)  # 10 min cache
            recent_matches = cached_result.get('matches', [])
            league_name = "All Leagues"
        
        if not recent_matches:
            return f"No recent finished matches found for {league_name}"
        
        latest_matches = recent_matches[:limit]
        
        response = f"**🏆 LATEST MATCHES - {league_name}** (Most Recent {len(latest_matches)} matches)\n\n"
        
        current_date = None
        for match in latest_matches:
            # Group by date for better readability
            if match['date'] != current_date:
                current_date = match['date']
                response += f"**📅 {current_date}:**\n"
            
            if match["home_score"] is not None and match["away_score"] is not None:
                score = f"{match['home_score']}-{match['away_score']}"
            else:
                score = "vs"
            
            response += f"⚽ {match['home_team']} {score} {match['away_team']}"
            if match.get('competition'):
                response += f" ({match['competition']})"
            if match.get('matchday'):
                response += f" - MD{match['matchday']}"
            response += "\n"
        
        response += f"\n*Showing the most recent completed matches from cached data*"
        return response
    
    except Exception as e:
        return f"Error fetching latest matches: {str(e)}"


@tool
def compare_players(player1: str, player2: str) -> str:
    """
    Compare two football players using cached data from multiple sources to avoid rate limits.
    
    Args:
        player1: Name of first player (e.g., "Lionel Messi")
        player2: Name of second player (e.g., "Cristiano Ronaldo")
    
    Examples:
        - compare_players("Messi", "Ronaldo") -> Compare Messi and Ronaldo
        - compare_players("Haaland", "Mbappe") -> Compare Haaland and Mbappe
    """
    try:
        # Use batch fetcher to get both players' data efficiently
        comparison_data = batch_fetcher.get_player_comparison_data(player1, player2)
        
        if not comparison_data.get('success'):
            return f"Error fetching player comparison data: {comparison_data.get('error', 'Unknown error')}"
        
        data = comparison_data['data']
        
        response = f"**⚽ PLAYER COMPARISON: {player1.title()} vs {player2.title()}**\n\n"
        
        # Format comparison data
        for i, player_name in enumerate([player1, player2], 1):
            player_data = data.get(f'player{i}', {})
            
            response += f"**📊 {player_name.title()}:**\n"
            
            # Wikipedia data
            wiki_data = player_data.get('wikipedia', {})
            if wiki_data and not wiki_data.get('error'):
                response += "📖 *Wikipedia:*\n"
                if wiki_data.get('birth_date'):
                    response += f"• Birth Date: {wiki_data['birth_date']}\n"
                if wiki_data.get('nationality'):
                    response += f"• Nationality: {wiki_data['nationality']}\n"
                if wiki_data.get('position'):
                    response += f"• Position: {wiki_data['position']}\n"
                if wiki_data.get('current_team'):
                    response += f"• Current Team: {wiki_data['current_team']}\n"
                if wiki_data.get('height'):
                    response += f"• Height: {wiki_data['height']}\n"
                response += "\n"
            
            # Transfermarkt data
            tm_data = player_data.get('transfermarkt', {})
            if tm_data and not tm_data.get('error'):
                response += "💰 *Transfermarkt:*\n"
                if tm_data.get('market_value'):
                    response += f"• Market Value: {tm_data['market_value']}\n"
                if tm_data.get('age'):
                    response += f"• Age: {tm_data['age']}\n"
                if tm_data.get('current_club'):
                    response += f"• Current Club: {tm_data['current_club']}\n"
                response += "\n"
            
            if not wiki_data.get('error') and not tm_data.get('error'):
                response += "---\n\n"
        
        if not data.get('player1') and not data.get('player2'):
            return f"No comparison data found for {player1} and {player2}"
        
        response += f"*Data fetched: {comparison_data['fetched_at'][:16]} (cached to avoid rate limits)*"
        return response
    
    except Exception as e:
        return f"Error comparing players: {str(e)}"


@tool
def get_league_overview(league: str) -> str:
    """
    Get a comprehensive overview of a league including recent matches, standings, and upcoming fixtures.
    This uses efficient batch fetching to minimize API calls.
    
    Args:
        league: League code (PL, BL1, SA, PD, FL1, CL, WC)
    
    Examples:
        - get_league_overview("PL") -> Premier League overview
        - get_league_overview("BL1") -> Bundesliga overview
    """
    try:
        # Use batch fetcher to get comprehensive league data efficiently
        comprehensive_data = batch_fetcher.get_comprehensive_league_data(league)
        
        if not comprehensive_data.get('success'):
            return f"Error fetching {league} overview: {comprehensive_data.get('error', 'Unknown error')}"
        
        data = comprehensive_data['data']
        league_name = data_manager.league_mappings.get(league, {}).get('name', league)
        
        response = f"**🏆 {league_name} OVERVIEW**\n\n"
        
        # Recent matches
        recent_matches = data.get('recent_matches', [])
        if recent_matches:
            response += "**📅 RECENT RESULTS:**\n"
            for match in recent_matches[:5]:  # Show last 5 matches
                if match["home_score"] is not None and match["away_score"] is not None:
                    score = f"{match['home_score']}-{match['away_score']}"
                    response += f"• {match['date']}: {match['home_team']} {score} {match['away_team']}\n"
            response += "\n"
        
        # Standings (top 6)
        standings = data.get('standings', [])
        if standings:
            response += "**📊 CURRENT STANDINGS (Top 6):**\n"
            response += "Pos | Team | P | Pts | GD\n"
            response += "-" * 30 + "\n"
            for team in standings[:6]:
                response += f"{team['position']:2d} | {team['team'][:12]:12s} | {team['played']:2d} | {team['points']:2d} | {team['goal_difference']:+3d}\n"
            response += "\n"
        
        # Upcoming matches
        upcoming_matches = data.get('upcoming_matches', [])
        if upcoming_matches:
            response += "**📅 UPCOMING FIXTURES:**\n"
            for match in upcoming_matches[:5]:  # Show next 5 matches
                response += f"• {match['date']} {match.get('time', '')}: {match['home_team']} vs {match['away_team']}\n"
            response += "\n"
        
        # Live matches
        live_matches = data.get('live_matches', [])
        if live_matches:
            response += "**🔴 LIVE MATCHES:**\n"
            for match in live_matches:
                if match["home_score"] is not None and match["away_score"] is not None:
                    score = f"{match['home_score']}-{match['away_score']}"
                else:
                    score = "0-0"
                response += f"• {match['home_team']} {score} {match['away_team']} ({match['status']})\n"
            response += "\n"
        
        response += f"*Data from cache - {comprehensive_data['fetched_at'][:16]}*"
        return response
    
    except Exception as e:
        return f"Error fetching league overview: {str(e)}"


@tool
def get_player_info_optimized(player_name: str, include_market_value: bool = True) -> str:
    """
    Get comprehensive player information using cached data to avoid rate limits.
    
    Args:
        player_name: Full or partial player name
        include_market_value: Whether to include market value from Transfermarkt
    """
    try:
        cache_params = {
            'type': 'player_info',
            'player': player_name.lower(),
            'include_market_value': include_market_value,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        def fetch_player_data(type, player, include_market_value, date):
            player_data = {'success': True, 'data': {}}
            
            # Get Wikipedia data
            wiki_data = wiki_scraper.search_player(player)
            if not wiki_data.get("error"):
                player_data['data']['wikipedia'] = wiki_data
            
            # Get Transfermarkt data if requested
            if include_market_value:
                tm_data = transfermarkt_scraper.search_player(player)
                if not tm_data.get("error"):
                    player_data['data']['transfermarkt'] = tm_data
            
            return player_data
        
        # Cache player data for 6 hours (changes less frequently)
        cached_result = cache_manager.get_or_fetch(cache_params, fetch_player_data, ttl=21600)
        
        if not cached_result.get('success'):
            return f"Error fetching player data: {cached_result.get('error', 'Unknown error')}"
        
        data = cached_result['data']
        response = f"**⚽ Player Information: {player_name.title()}**\n\n"
        sources_used = []
        
        # Wikipedia information
        wiki_data = data.get('wikipedia', {})
        if wiki_data and not wiki_data.get("error"):
            sources_used.append("Wikipedia")
            response += "📖 **Wikipedia Information:**\n"
            for key, value in wiki_data.items():
                if key not in ["source", "name"] and value:
                    formatted_key = key.replace("_", " ").title()
                    response += f"• {formatted_key}: {value}\n"
            response += "\n"
        
        # Transfermarkt information
        tm_data = data.get('transfermarkt', {})
        if tm_data and not tm_data.get("error"):
            sources_used.append("Transfermarkt")
            response += "💰 **Transfermarkt Information:**\n"
            for key, value in tm_data.items():
                if key not in ["source", "url"] and value:
                    formatted_key = key.replace("_", " ").title()
                    response += f"• {formatted_key}: {value}\n"
            response += "\n"
        
        if not sources_used:
            return f"No information found for player '{player_name}' from any source."
        
        response += f"*Sources: {', '.join(sources_used)} (cached data)*"
        return response
    
    except Exception as e:
        return f"Error fetching player information: {str(e)}"


@tool
def get_live_matches_optimized() -> str:
    """
    Get currently live/ongoing football matches using cached data (1 minute cache).
    """
    try:
        cache_params = {
            'type': 'live_matches',
            'timestamp': int(datetime.now().timestamp() // 60)  # Group by minute
        }
        
        def fetch_live_data(type, timestamp):
            result = data_manager.get_matches(status="live")
            return result
        
        # Very short cache for live matches (1 minute)
        result = cache_manager.get_or_fetch(cache_params, fetch_live_data, ttl=60)
        
        if not result.get("matches"):
            return "No live matches currently in progress."
        
        matches = result["matches"]
        source = result["source"]
        
        response = f"**🔴 LIVE MATCHES** ({len(matches)} ongoing) - Source: {source}\n\n"
        
        for match in matches:
            if match["home_score"] is not None and match["away_score"] is not None:
                score = f"{match['home_score']}-{match['away_score']}"
            else:
                score = "0-0"
            
            response += f"🏆 {match['competition']}\n"
            response += f"⚽ {match['home_team']} {score} {match['away_team']}\n"
            response += f"⏱️ {match['status']}\n\n"
        
        return response
    
    except Exception as e:
        return f"Error fetching live matches: {str(e)}"


@tool
def search_football_info_optimized(query: str) -> str:
    """
    General search for football information using cached Wikipedia data.
    
    Args:
        query: Search query (e.g., "2018 World Cup", "Manchester United history")
    """
    try:
        cache_params = {
            'type': 'football_search',
            'query': query.lower(),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        def fetch_search_data(type, query, date):
            # Use Wikipedia search for general football information
            wiki_data = wiki_scraper.search_player(query)
            return {'data': wiki_data, 'success': not wiki_data.get("error")}
        
        # Cache search results for 24 hours
        cached_result = cache_manager.get_or_fetch(cache_params, fetch_search_data, ttl=86400)
        
        wiki_data = cached_result.get('data', {})
        
        if wiki_data.get("error") or not cached_result.get('success'):
            return f"No information found for '{query}' on Wikipedia"
        
        response = f"**🔍 Search Results for: {query}**\n\n"
        
        for key, value in wiki_data.items():
            if key not in ["source"] and value:
                formatted_key = key.replace("_", " ").title()
                response += f"**{formatted_key}:** {value}\n\n"
        
        response += "*Source: Wikipedia (cached data)*"
        return response
    
    except Exception as e:
        return f"Error searching for football information: {str(e)}"


@tool
def clear_cache() -> str:
    """
    Clear expired cache entries to free up space and reset rate limiting issues.
    Use this if you're experiencing persistent rate limiting problems.
    """
    try:
        cleared_count = cache_manager.clear_expired()
        stats = cache_manager.get_cache_stats()
        
        return f"✅ Cache maintenance completed!\n" \
               f"• Cleared {cleared_count} expired entries\n" \
               f"• Memory cache: {stats['memory_entries']} entries\n" \
               f"• File cache: {stats['file_entries']} entries\n" \
               f"• Cache directory: {stats['cache_dir']}"
    
    except Exception as e:
        return f"Error clearing cache: {str(e)}"