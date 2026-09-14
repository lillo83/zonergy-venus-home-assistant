"""Constants for the Zonergy Venus integration."""

from typing import Final

DOMAIN: Final = "zonergy_venus"
DEFAULT_PORT: Final = 6053
CONF_ENCRYPTION_KEY: Final = "encryption_key"
CONF_CONNECTION_TYPE: Final = "connection_type"
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_SN: Final = "device_sn"
CONF_INVERTER_MODEL: Final = "inverter_model"
CONF_PLANT_ID: Final = "plant_id"
CONF_PLANT_NAME: Final = "plant_name"

CONNECTION_ESPHOME: Final = "esphome"
CONNECTION_CLOUD: Final = "cloud"

CLOUD_BASE_URL: Final = "https://zonergy.vidagrid.com"
CLOUD_SCAN_INTERVAL: Final = 15

PLATFORMS: Final = ["sensor", "binary_sensor", "switch", "number"]

# These entities identify the companion ESPHome firmware without depending on
# the node name or its IP address.
REQUIRED_ENTITY_NAMES: Final = {
    "Potenza Totale PV",
    "Potenza Carico",
    "SOC Medio Batteria",
}
