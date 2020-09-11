import logging

from .config import LOG_LEVEL

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=LOG_LEVEL
)

from .core import client

with client:
    print("bobmb")
    client.run_until_disconnected()

    # client.loop.run_until_complete()
