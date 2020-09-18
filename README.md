![CI status badge](https://github.com/Gowee/traceroute-map-panel/workflows/CI/badge.svg)

# telegram-user-tracker
A telegram bot built with MTProto (telethon) to track user accounts persistently even through account deletion and recreation.

## How?
The bot keeps tracking the changes of the list of blocked contacts, waiting for new user accounts, which corresponds with some certain blocked contacts, automatically added by the Telegram server.

## Run
`env API_ID={ID} API_HASH={HASH} REPORT_CHANNEL={CHANNEL_OR_CHAT_ID} ROOT_ADMIN={USER_ID} python -m telegram-user-tracker`
, where:
* `API_ID` and `API_HASH` is available from Telegram following [the instructions of Telethon](https://docs.telethon.dev/en/latest/basic/signing-in.html). They can also be specified in files named `.api_id` and `.api_hash` in the current working directory, respectively.
* `REPORT_CHANNEL` is the ID of a chat, group or channel for the bot to report the account changes.
* `ROOT_ADMIN` is the user ID of an additional account from where the bot accepts instructions such as adding/removing tracked accounts or elevating/lifting privileges for non-root admins.
Other configurable options are listed in [.config](https://github.com/Gowee/telegram-user-tracker/blob/master/telegram_user_tracker/config.py).
