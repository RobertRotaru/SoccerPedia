# Configuration and Setup Instructions

## API Keys Setup

### Required APIs:
1. **OpenAI API** (Required)
   - Get your key from: https://platform.openai.com/api-keys
   - Add to .env: `OPENAI_API_KEY=your_key_here`

2. **Football Data API** (Required for matches/standings)
   - Get free key from: https://www.football-data.org/client/register
   - Add to .env: `FOOTBALL_DATA_API_KEY=your_key_here`

### Optional APIs:
3. **API Football** (Optional - additional data)
   - Get key from: https://www.api-football.com/
   - Add to .env: `API_FOOTBALL_KEY=your_key_here`

## League Codes Supported:
- PL: Premier League
- BL1: Bundesliga
- SA: Serie A
- PD: La Liga
- FL1: Ligue 1
- CL: Champions League
- WC: World Cup

## Features:
- ✅ Live matches and scores
- ✅ League standings/tables
- ✅ Player information (Wikipedia + Transfermarkt)
- ✅ Team information and recent performance
- ✅ Upcoming fixtures
- ✅ Historical data search
- ✅ Multiple data source fallbacks
- ✅ ReAct reasoning mechanism

## Usage Examples:
- "Show me today's Premier League matches"
- "What's the current Bundesliga table?"
- "Tell me about Lionel Messi"
- "Manchester United recent matches"
- "Upcoming Champions League fixtures"
- "2018 World Cup final information"

## Installation:
1. Install requirements: `pip install -r requirements.txt`
2. Set up .env file with your API keys
3. Run: `streamlit run gui/app.py`