"""Constants for HT HomeService integration."""

from datetime import timedelta

DOMAIN = "hiot"
API_BASE_URL = "https://www2.hthomeservice.com"
AES_PASSPHRASE = "hTsEcret"

# API Paths
PATH_LOGIN = "login"
PATH_HOUSEHOLD = "proxy/bearer/api/v1/user/danji/household"
PATH_HOMEPAGE = "proxy/bearer/api/v1/user/homepage"
PATH_CTOC_TOKEN = "getctoctoken"
PATH_DEVICES = "proxy/ctoc/devices"
PATH_DEVICES_WITH_STATUS = "proxy/ctoc/devices?includeStatus=true"
PATH_EMS_USAGE = "proxy/ctoc/ems/usage"
PATH_EMS_FEE = "proxy/ctoc/ems/fee"
PATH_EMS_USAGE_GOAL = "proxy/ctoc/ems/usage/goal"
PATH_EMS_USAGE_HISTORY = "proxy/ctoc/ems/usage/history"

# Device category paths (used in /proxy/ctoc/{category}/{id})
CATEGORY_LIGHT = "lights"
CATEGORY_HEATER = "heaters"
CATEGORY_FAN = "fans"
CATEGORY_GAS = "gases"
CATEGORY_AIRCON = "aircons"
CATEGORY_WALLSOCKET = "wall-sockets"

DEVICE_CATEGORY_MAP = {
    "light": CATEGORY_LIGHT,
    "heating": CATEGORY_HEATER,
    "fan": CATEGORY_FAN,
    "gas": CATEGORY_GAS,
    "aircon": CATEGORY_AIRCON,
    "wallsocket": CATEGORY_WALLSOCKET,
}

# Config keys
CONF_SITE_ID = "site_id"
CONF_SITE_NAME = "site_name"
CONF_DONG = "dong"
CONF_HO = "ho"
CONF_HOMEPAGE_DOMAIN = "homepage_domain"

PLATFORMS = [
    "light",
    "climate",
    "fan",
    "switch",
    "sensor",
]
DEFAULT_SCAN_INTERVAL = timedelta(seconds=20)
DEFAULT_ENERGY_SCAN_INTERVAL = timedelta(minutes=30)
ENERGY_TYPES = ["ELEC", "WATER", "GAS"]

CONF_DEVICE_SCAN_INTERVAL = "device_scan_interval"
CONF_ENERGY_SCAN_INTERVAL = "energy_scan_interval"

# Options for scan interval selector (seconds)
DEVICE_SCAN_INTERVAL_OPTIONS = [5, 10, 15, 20, 30, 40, 50, 60, 180, 300, 600]
ENERGY_SCAN_INTERVAL_OPTIONS = [300, 600, 900, 1800, 3600, 7200, 21600, 43200, 86400]


MANUFACTURER = "Hyundai T&S"
