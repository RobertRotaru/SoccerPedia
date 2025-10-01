# agent/tools.py
import json
from datetime import datetime, timedelta
from langchain.tools import tool
from .data_sources import DataSourceManager, WikipediaScraper, TransfermarktScraper

# Initialize data source managers
data_manager = DataSourceManager()
wiki_scraper = WikipediaScraper()
transfermarkt_scraper = TransfermarktScraper()


@tool
def get_current_date() -> str:
    """
    Returns the current date in YYYY-MM-DD format.
    """
    return datetime.now().strftime("%Y-%m-%d")


@tool
def get_matches(league: str = None, date: str = None, status: str = "all") -> str:
    """
    Get football matches for any league and date.
    
    Args:
        league: League code (PL, BL1, SA, PD, FL1, CL, WC) or None for all leagues
        date: Date in YYYY-MM-DD format or None for recent matches
        status: 'finished', 'scheduled', 'live', or 'all'
    
    Examples:
        - get_matches() -> Get recent matches from all leagues
        - get_matches(league="PL") -> Get Premier League matches
        - get_matches(date="2024-10-01") -> Get matches for specific date
        - get_matches(league="PL", date="2024-10-01", status="finished") -> Get finished PL matches for date
    """
    try:
        # If no date specified, get matches from the last 7 days to ensure we get recent results
        if date is None and status in ["all", "finished"]:
            # Get matches from the past week to capture the most recent results
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            # Try to get recent finished matches
            result = data_manager.get_matches(league=league, date=end_date, status="finished")
            
            # If no matches on today, expand search to past week
            if not result.get("matches"):
                result = data_manager.get_matches(league=league, status="finished")
        else:
            result = data_manager.get_matches(league=league, date=date, status=status)
        
        if not result.get("matches"):
            return f"No matches found for league={league}, date={date}, status={status}"
        
        matches = result["matches"]
        source = result["source"]
        
        # Format the response
        response = f"**Found {len(matches)} matches** (Source: {source})\n\n"
        
        for match in matches[:10]:  # Limit to 10 matches for readability
            if match["home_score"] is not None and match["away_score"] is not None:
                score = f"{match['home_score']}-{match['away_score']}"
            else:
                score = "vs"
            
            response += f"🏆 **{match['competition']}** (Matchday {match.get('matchday', 'N/A')})\n"
            response += f"📅 {match['date']} {match['time']}\n"
            response += f"⚽ {match['home_team']} {score} {match['away_team']}\n"
            response += f"📊 Status: {match['status']}\n\n"
        
        if len(matches) > 10:
            response += f"... and {len(matches) - 10} more matches\n"
        
        return response
    
    except Exception as e:
        return f"Error fetching matches: {str(e)}"


@tool
def get_latest_matches(league: str = None, limit: int = 10) -> str:
    """
    Get the most recent finished matches from any league.
    This tool specifically focuses on getting the latest completed matches,
    not matches from matchweek 1.
    
    Args:
        league: League code (PL, BL1, SA, PD, FL1, CL, WC) or None for all leagues
        limit: Maximum number of matches to return (default: 10)
    
    Examples:
        - get_latest_matches() -> Get latest matches from all leagues
        - get_latest_matches("PL") -> Get latest Premier League matches
        - get_latest_matches("PL", 5) -> Get latest 5 Premier League matches
    """
    try:
        # Get matches from the past 14 days to ensure we capture recent results
        recent_matches = []
        
        for days_back in range(0, 15):  # Check last 14 days
            check_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            result = data_manager.get_matches(league=league, date=check_date, status="finished")
            
            if result.get("matches"):
                for match in result["matches"]:
                    # Parse match date to ensure proper ordering
                    try:
                        match_datetime = datetime.strptime(f"{match['date']} {match.get('time', '00:00')}", "%Y-%m-%d %H:%M")
                        match["datetime"] = match_datetime
                        recent_matches.append(match)
                    except:
                        recent_matches.append(match)
        
        if not recent_matches:
            return f"No recent finished matches found for {league if league else 'any league'}"
        
        # Sort by date (most recent first) and take the requested limit
        recent_matches.sort(key=lambda x: x.get("datetime", datetime.min), reverse=True)
        recent_matches = recent_matches[:limit]
        
        source = "Multiple API calls"
        league_name = data_manager.league_mappings.get(league, {}).get('name', league) if league else "All Leagues"
        
        response = f"**🏆 LATEST MATCHES - {league_name}** (Most Recent {len(recent_matches)} matches)\n\n"
        
        current_date = None
        for match in recent_matches:
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
        
        response += f"\n*Showing the most recent completed matches, not chronological matchweeks*"
        return response
    
    except Exception as e:
        return f"Error fetching latest matches: {str(e)}"


@tool
def get_league_standings(league: str, season: str = None) -> str:
    """
    Get current league standings/table.
    
    Args:
        league: League code (PL, BL1, SA, PD, FL1, CL, WC)
        season: Season year (e.g., "2024") or None for current season
    
    Examples:
        - get_league_standings("PL") -> Get current Premier League table
        - get_league_standings("BL1", "2023") -> Get 2023 Bundesliga table
    """
    try:
        result = data_manager.get_standings(league=league, season=season)
        
        if not result.get("standings"):
            return f"No standings found for league {league}, season {season}"
        
        standings = result["standings"]
        source = result["source"]
        league_name = result.get("league", league)
        season_info = result.get("season", "current")
        
        response = f"**{league_name} Standings - Season {season_info}** (Source: {source})\n\n"
        response += "Pos | Team | P | W | D | L | GF | GA | GD | Pts\n"
        response += "-" * 50 + "\n"
        
        for team in standings[:20]:  # Show top 20 teams
            response += f"{team['position']:2d} | "
            response += f"{team['team'][:15]:15s} | "
            response += f"{team['played']:2d} | "
            response += f"{team['won']:2d} | "
            response += f"{team['drawn']:2d} | "
            response += f"{team['lost']:2d} | "
            response += f"{team['goals_for']:2d} | "
            response += f"{team['goals_against']:2d} | "
            response += f"{team['goal_difference']:+3d} | "
            response += f"{team['points']:2d}\n"
        
        return response
    
    except Exception as e:
        return f"Error fetching standings: {str(e)}"


@tool
def get_player_info(player_name: str, include_market_value: bool = True) -> str:
    """
    Get comprehensive player information from multiple sources.
    
    Args:
        player_name: Full or partial player name
        include_market_value: Whether to include market value from Transfermarkt
    
    Examples:
        - get_player_info("Lionel Messi") -> Get full info about Messi
        - get_player_info("Haaland", False) -> Get info without market value
    """
    try:
        response = f"**Player Information: {player_name}**\n\n"
        sources_used = []
        
        # Get Wikipedia data
        wiki_data = wiki_scraper.search_player(player_name)
        if not wiki_data.get("error"):
            sources_used.append("Wikipedia")
            response += "📖 **Wikipedia Information:**\n"
            for key, value in wiki_data.items():
                if key not in ["source", "name"] and value:
                    formatted_key = key.replace("_", " ").title()
                    response += f"• {formatted_key}: {value}\n"
            response += "\n"
        
        # Get Transfermarkt data if requested
        if include_market_value:
            tm_data = transfermarkt_scraper.search_player(player_name)
            if not tm_data.get("error"):
                sources_used.append("Transfermarkt")
                response += "💰 **Transfermarkt Information:**\n"
                for key, value in tm_data.items():
                    if key not in ["source", "url"] and value:
                        formatted_key = key.replace("_", " ").title()
                        response += f"• {formatted_key}: {value}\n"
                response += "\n"
        
        if not sources_used:
            return f"No information found for player '{player_name}' from any source."
        
        response += f"*Sources: {', '.join(sources_used)}*"
        return response
    
    except Exception as e:
        return f"Error fetching player information: {str(e)}"


@tool
def get_team_info(team_name: str, league: str = None) -> str:
    """
    Get team information including recent matches and league position.
    
    Args:
        team_name: Team name (e.g., "Manchester United", "Bayern Munich")
        league: League code if known (helps with search accuracy)
    
    Examples:
        - get_team_info("Manchester United") -> Get Man United info
        - get_team_info("Bayern", "BL1") -> Get Bayern Munich info from Bundesliga
    """
    try:
        response = f"**Team Information: {team_name}**\n\n"
        
        # Get recent matches involving this team
        recent_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        matches_result = data_manager.get_matches(league=league, date=recent_date)
        
        team_matches = []
        if matches_result.get("matches"):
            for match in matches_result["matches"]:
                if (team_name.lower() in match["home_team"].lower() or 
                    team_name.lower() in match["away_team"].lower()):
                    team_matches.append(match)
        
        if team_matches:
            response += "⚽ **Recent Matches:**\n"
            for match in team_matches[:5]:
                if match["home_score"] is not None:
                    score = f"{match['home_score']}-{match['away_score']}"
                else:
                    score = "vs"
                response += f"• {match['date']}: {match['home_team']} {score} {match['away_team']}\n"
            response += "\n"
        
        # Try to get league position if league is specified
        if league:
            standings_result = data_manager.get_standings(league)
            if standings_result.get("standings"):
                for team in standings_result["standings"]:
                    if team_name.lower() in team["team"].lower():
                        response += "📊 **League Position:**\n"
                        response += f"• Position: {team['position']}\n"
                        response += f"• Points: {team['points']}\n"
                        response += f"• Played: {team['played']}\n"
                        response += f"• Record: {team['won']}W-{team['drawn']}D-{team['lost']}L\n"
                        break
        
        if len(response.split('\n')) <= 3:  # Only header present
            return f"No recent information found for team '{team_name}'"
        
        return response
    
    except Exception as e:
        return f"Error fetching team information: {str(e)}"


@tool
def get_live_matches() -> str:
    """
    Get currently live/ongoing football matches.
    """
    try:
        result = data_manager.get_matches(status="live")
        
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
def get_upcoming_matches(league: str = None, days_ahead: int = 7) -> str:
    """
    Get upcoming matches in the next few days.
    
    Args:
        league: League code (PL, BL1, SA, PD, FL1, CL, WC) or None for all leagues
        days_ahead: Number of days to look ahead (default: 7)
    
    Examples:
        - get_upcoming_matches() -> Next 7 days, all leagues
        - get_upcoming_matches("PL", 3) -> Next 3 days, Premier League only
    """
    try:
        end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        result = data_manager.get_matches(league=league, status="scheduled")
        
        if not result.get("matches"):
            return f"No upcoming matches found for the next {days_ahead} days"
        
        # Filter matches for the specified time period
        upcoming_matches = []
        today = datetime.now().date()
        cutoff_date = today + timedelta(days=days_ahead)
        
        for match in result["matches"]:
            try:
                match_date = datetime.strptime(match["date"], "%Y-%m-%d").date()
                if today <= match_date <= cutoff_date:
                    upcoming_matches.append(match)
            except:
                continue
        
        if not upcoming_matches:
            return f"No upcoming matches found for the next {days_ahead} days"
        
        response = f"**📅 UPCOMING MATCHES** (Next {days_ahead} days)\n"
        if league:
            response += f"League: {data_manager.league_mappings.get(league, {}).get('name', league)}\n"
        response += f"Source: {result['source']}\n\n"
        
        # Group by date
        matches_by_date = {}
        for match in upcoming_matches:
            date = match["date"]
            if date not in matches_by_date:
                matches_by_date[date] = []
            matches_by_date[date].append(match)
        
        for date in sorted(matches_by_date.keys())[:7]:  # Show max 7 days
            response += f"**{date}:**\n"
            for match in matches_by_date[date][:5]:  # Max 5 matches per day
                response += f"• {match['time']} - {match['home_team']} vs {match['away_team']}"
                if match.get('competition'):
                    response += f" ({match['competition']})"
                response += "\n"
            response += "\n"
        
        return response
    
    except Exception as e:
        return f"Error fetching upcoming matches: {str(e)}"


@tool
def search_football_info(query: str) -> str:
    """
    General search for football information using Wikipedia.
    Use this for historical data, club information, tournaments, or any football-related query
    that doesn't fit other specific tools.
    
    Args:
        query: Search query (e.g., "2018 World Cup", "Manchester United history", "Champions League")
    
    Examples:
        - search_football_info("2018 World Cup final") -> Info about the 2018 WC final
        - search_football_info("Arsenal FC history") -> Historical info about Arsenal
    """
    try:
        # Use Wikipedia search for general football information
        wiki_data = wiki_scraper.search_player(query)  # Reusing the search functionality
        
        if wiki_data.get("error"):
            return f"No information found for '{query}' on Wikipedia"
        
        response = f"**Search Results for: {query}**\n\n"
        
        for key, value in wiki_data.items():
            if key not in ["source"] and value:
                formatted_key = key.replace("_", " ").title()
                response += f"**{formatted_key}:** {value}\n\n"
        
        response += "*Source: Wikipedia*"
        return response
    
    except Exception as e:
        return f"Error searching for football information: {str(e)}"
