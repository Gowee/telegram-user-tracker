import os
from dateutil import tz as timezone

# import logging

from .utils import read_file

# logging.basicConfig(
#     format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
# )

API_ID = read_file("./.api_id") or os.environ.get("API_ID")
API_HASH = read_file("./.api_hash") or os.environ.get("API_HASH")
SESSION_NAME = os.environ.get("SESSION_NAME", "anon")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "warning").upper()
CHECK_INTERVAL = os.environ.get("CHECK_INTERVAL", 15 * 60)  # in seconds
REPORT_CHANNEL = read_file("./.report_channel") or os.environ.get(
    "report_channel", "me"
)
TIME_ZONE = timezone.gettz(os.environ.get("TIMEZONE", "Asia/Shanghai"))

try:
    REPORT_CHANNEL = int(REPORT_CHANNEL)
except ValueError:
    pass

assert API_ID
assert API_HASH
assert TIME_ZONE

__all__ = (
    "API_ID",
    "API_HASH",
    "SESSION_NAME",
    "LOG_LEVEL",
    "REPORT_CHANNEL",
    "TIME_ZONE",
)
