"""Constants for the Smart Pool Connect integration."""

from __future__ import annotations

DOMAIN = "smartpoolcontrol"

# Base URL of the Smart Pool Connect REST API (api.smartpoolconnect.eu).
# The legacy owner.smartpoolcontrol.eu portal has been decommissioned; the
# vendor migrated to a modern OAuth2 + JSON API backend.
DEFAULT_BASE_URL = "https://api.smartpoolconnect.eu"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_POOL_ID = "pool_id"  # the API's pool UUID ("pid")
CONF_POOL_NAME = "pool_name"
CONF_POOL_MAC = "pool_mac"

# How often the coordinator polls the API (seconds). The device reports every
# couple of minutes, so polling much faster is pointless.
DEFAULT_SCAN_INTERVAL = 120

MANUFACTURER = "Europe Pool Supplies B.V. (Smart Pool Connect)"

# Module sub-resources under /pool/{pid}/ that expose GET + PATCH.
MODULE_PH = "ph"
MODULE_CL = "cl"
MODULE_FILTER = "filter"
MODULE_LIGHTING = "lighting"
MODULE_COVER = "cover"
MODULE_TEMPERATURE = "temperature"

# Pump speed values accepted by the filter config (config.pump_speed is a
# string). Extend if the controller exposes more steps.
PUMP_SPEEDS: tuple[str, ...] = ("off", "low", "medium", "high")
