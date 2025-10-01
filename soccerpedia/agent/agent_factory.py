# agent/agent_factory.py
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .optimized_tools import (
    get_current_date,
    get_latest_premier_league_results,
    get_latest_matches_any_league,
    compare_players,
    get_league_overview,
    get_player_info_optimized,
    get_live_matches_optimized,
    search_football_info_optimized,
    clear_cache
)


def build_agent():
    """Build a comprehensive football assistant agent with ReAct capabilities"""
    
    # Choose your LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Register optimized tools that use caching and batch processing to avoid rate limits
    tools = [
        get_current_date,
        get_latest_premier_league_results,
        get_latest_matches_any_league,
        compare_players,
        get_league_overview,
        get_player_info_optimized,
        get_live_matches_optimized,
        search_football_info_optimized,
        clear_cache
    ]

    # Enhanced ReAct-style prompt with better reasoning guidance
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are Soccerpedia, an expert AI football (soccer) assistant with access to comprehensive CACHED data sources to avoid rate limits.

**IMPORTANT - Rate Limit Optimization:**
- Your tools use intelligent caching to minimize API calls
- Recent data is cached for 5-30 minutes, historical data for hours
- Batch processing fetches related data in single operations
- Use these optimized tools to avoid hitting API rate limits

**Your optimized capabilities:**
- Latest Premier League results (get_latest_premier_league_results)
- Latest matches from any league (get_latest_matches_any_league) 
- Comprehensive league overviews (get_league_overview)
- Player comparisons with cached data (compare_players)
- Player information with market values (get_player_info_optimized)
- Live matches with minimal API calls (get_live_matches_optimized)
- Football info search with caching (search_football_info_optimized)
- Cache management (clear_cache)

**Available leagues:** Premier League (PL), Bundesliga (BL1), Serie A (SA), La Liga (PD), Ligue 1 (FL1), Champions League (CL), World Cup (WC)

**Data sources:** football-data.org, api-football.com, Wikipedia, and Transfermarkt (all cached)

**ReAct Instructions:**
1. **Think** about what the user wants - latest results, player comparison, league overview?
2. **Choose** the most efficient tool that uses cached data
3. **Act** by calling the appropriate optimized tool
4. **Observe** the cached results
5. **Respond** with well-formatted information

**For common queries:**
- "Latest PL results" → use get_latest_premier_league_results()
- "Messi vs Ronaldo" → use compare_players("Messi", "Ronaldo") 
- "Premier League overview" → use get_league_overview("PL")
- "Player info" → use get_player_info_optimized(player_name)

**Guidelines:**
- Prefer cached/optimized tools to avoid rate limits
- Use clear_cache() if experiencing persistent issues
- Format responses with emojis and structure
- Always mention data is cached when relevant
- Be specific about dates and competitions"""),
        
        ("human", "{input}"),
        
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Create agent with enhanced reasoning
    agent = create_openai_functions_agent(llm, tools, prompt)

    # Wrap in executor with optimized settings for rate-limited APIs
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=False,  # Set to False to reduce overhead
        max_iterations=6,  # Reduced to prevent excessive API calls
        max_execution_time=25,  # 25 second timeout
        early_stopping_method="generate",
        handle_parsing_errors=True,
        return_intermediate_steps=False
    )

    return agent_executor
