"""Constants for the Smart Pool Control integration."""

from __future__ import annotations

DOMAIN = "smartpoolcontrol"

# Default base URL of the owner web portal.
DEFAULT_BASE_URL = "https://owner.smartpoolcontrol.eu"

CONF_BASE_URL = "base_url"
CONF_POOL_ID = "pool_id"
CONF_POOL_NAME = "pool_name"
CONF_POOL_MAC = "pool_mac"

# How often the coordinator polls the portal (seconds). The portal itself
# refreshes roughly every 2 minutes, so polling much faster is pointless.
DEFAULT_SCAN_INTERVAL = 120

MANUFACTURER = "Europe Pool Supplies B.V. (Smart Pool Control)"

# Pump speed values used by the filter schedule forms.
PUMP_SPEEDS: dict[int, str] = {
    0: "off",
    1: "low",
    2: "medium",
    3: "high",
    4: "maximum",
}
PUMP_SPEEDS_REVERSE = {v: k for k, v in PUMP_SPEEDS.items()}

# Lighting program configurations exposed by the lighting settings form.
LIGHTING_MODES: dict[int, str] = {
    0: "Single Colour",
    1: "Rotating RGB",
    2: "STL-RGB",
    3: "Adagio",
    4: "Adagio tw",
    5: "Allegro",
    6: "Spectra",
    7: "Spectra tw",
    8: "plp rem",
}
LIGHTING_MODES_REVERSE = {v: k for k, v in LIGHTING_MODES.items()}
