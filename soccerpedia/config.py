# Configuration for Soccerpedia
import os

# API Configuration
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "98792b7d8bd64cc5a2c32ea06c7f0de9")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")

# Rate Limiting Configuration
RATE_LIMIT_DELAY = 1.0  # seconds between requests
MAX_REQUESTS_PER_MINUTE = 50  # conservative limit
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

# GUI Configuration
ANIMATION_SPEED = 0.1  # seconds between animation frames
ERROR_DISPLAY_DURATION = 5  # seconds to show error messages

# League configurations
LEAGUE_MAPPINGS = {
    "PL": {"football_data": "PL", "api_football": 39, "name": "Premier League"},
    "BL1": {"football_data": "BL1", "api_football": 78, "name": "Bundesliga"},
    "SA": {"football_data": "SA", "api_football": 135, "name": "Serie A"},
    "PD": {"football_data": "PD", "api_football": 140, "name": "La Liga"},
    "FL1": {"football_data": "FL1", "api_football": 61, "name": "Ligue 1"},
    "CL": {"football_data": "CL", "api_football": 2, "name": "Champions League"},
    "EL": {"football_data": "EL", "api_football": 3, "name": "Europa League"},
    "WC": {"football_data": "WC", "api_football": 1, "name": "World Cup"}
}