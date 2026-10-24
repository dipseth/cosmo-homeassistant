"""Constants for the COSMO (myFilip) kids-watch integration."""

from __future__ import annotations

DOMAIN = "cosmo"
MANUFACTURER = "COSMO"

# COSMO is a white-label of the myFilip platform.
API_BASE = "https://api.myfilip.com/"
WHITE_LABEL_ID = 18
APP_BUILD = "3.4.1.732"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_POLL_INTERVAL = 60  # seconds between v2/map polls
MIN_POLL_INTERVAL = 15
MAX_POLL_INTERVAL = 900

# sourceType -> human label (from the map payload)
SOURCE_TYPES = {1: "GPS", 2: "LBS", 3: "WiFi", 4: "WiFi"}
