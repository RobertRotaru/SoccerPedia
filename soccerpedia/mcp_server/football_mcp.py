from fastapi import FastAPI
import httpx, os, datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

app = FastAPI()

headers = {"x-apisports-key": API_KEY}

# Cache league name -> id
LEAGUE_CACHE = {}

async def get_league_id(name: str):
    """Resolve league name to ID via API-Football."""
    name_lower = name.lower()
    if name_lower in LEAGUE_CACHE:
        return LEAGUE_CACHE[name_lower]

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/leagues", headers=headers)
        data = resp.json()

    for item in data.get("response", []):
        league = item["league"]
        if league["name"].lower() == name_lower:
            league_id = league["id"]
            LEAGUE_CACHE[name_lower] = league_id
            return league_id
    return None


@app.get("/matches")
async def get_matches(date: str = None, league: str = None):
    """
    Get matches for a given date (default: yesterday).
    Accepts either league name (e.g. "Premier League") or league ID.
    """
    if not date:
        date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    league_id = None
    if league:
        if league.isdigit():
            league_id = int(league)
        else:
            league_id = await get_league_id(league)
            if not league_id:
                return {"error": f"League '{league}' not found."}

    params = {"date": date}
    if league_id:
        params["league"] = league_id

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/fixtures", params=params, headers=headers)
        data = resp.json()

    matches = []
    for f in data.get("response", []):
        matches.append({
            "date": f["fixture"]["date"],
            "league": f["league"]["name"],
            "home": f["teams"]["home"]["name"],
            "away": f["teams"]["away"]["name"],
            "score": f["score"]["fulltime"]
        })

    return {"matches": matches}
