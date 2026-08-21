"""Constants for the Somtoday integration."""

from datetime import timedelta

DOMAIN = "somtoday"
PLATFORMS = ["calendar", "sensor"]

CONF_SCHOOL = "school"
CONF_TENANT_ID = "tenant_id"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

CLIENT_ID = "somtoday-leerling-native"
AUTHORIZE_URL = "https://inloggen.somtoday.nl/oauth2/authorize"
TOKEN_URL = "https://inloggen.somtoday.nl/oauth2/token"
REDIRECT_URI = "somtoday://nl.topicus.somtoday.leerling/oauth/callback"
UPDATE_INTERVAL = timedelta(minutes=15)
DEFAULT_LOOKAHEAD_DAYS = 60
