"""Constants for the Somtoday integration."""

from datetime import timedelta

DOMAIN = "somtoday"
PLATFORMS = ["calendar", "sensor"]

CONF_SCHOOL = "school"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

CLIENT_ID = "D50E0C06-32D1-4B41-A137-A9A850C892C2"
TOKEN_URL = "https://somtoday.nl/oauth2/token"
ORGANISATIONS_URL = "https://servers.somtoday.nl/organisaties.json"
UPDATE_INTERVAL = timedelta(minutes=15)
DEFAULT_LOOKAHEAD_DAYS = 60
