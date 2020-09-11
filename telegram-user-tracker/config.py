import os

# import logging

from .utils import read_file

# logging.basicConfig(
#     format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
# )

API_ID = read_file("./.api_id") or os.environ.get("API_ID")
API_HASH = read_file("./.api_hash") or os.environ.get("API_HASH")
SESSION_NAME = os.environ.get("SESSION_NAME", "anon")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "warning").upper()
print(repr(API_ID), repr(API_HASH))
assert API_ID
assert API_HASH

__all__ = ("API_ID", "API_HASH", "SESSION_NAME", "LOG_LEVEL")
