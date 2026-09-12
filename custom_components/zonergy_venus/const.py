"""Constants for the Zonergy Venus integration."""

from typing import Final

DOMAIN: Final = "zonergy_venus"
DEFAULT_PORT: Final = 6053
CONF_ENCRYPTION_KEY: Final = "encryption_key"

PLATFORMS: Final = ["sensor", "binary_sensor", "switch", "number"]

# These entities identify the companion ESPHome firmware without depending on
# the node name or its IP address.
REQUIRED_ENTITY_NAMES: Final = {
    "Potenza Totale PV",
    "Potenza Carico",
    "SOC Medio Batteria",
}
