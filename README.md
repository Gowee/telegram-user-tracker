![CI status badge](https://github.com/Gowee/traceroute-map-panel/workflows/CI/badge.svg)

# telegram-user-tracker
A telegram bot built with MTProto (telethon) to track user accounts persistently even through account deletion and recreation.

## How?
Telegram automatically adds newly created accounts, which shares the same phone number with the ones already blocked and deleted, to the list of blocked contacts, of which the bot keeps tracking the changes.

**Note:** In general, if a new corresponding account is not created immediately after the old account is deleted, it is barely possible to relate those accounts when there are lots of tracked accounts. The reason is that the mechanism provided by Telegram does not reveal such relations. 

## Run
`env API_ID={ID} API_HASH={HASH} REPORT_CHANNEL={CHANNEL_OR_CHAT_ID} ROOT_ADMIN={USER_ID} python -m telegram-user-tracker`
, where:
* `API_ID` and `API_HASH` is available from Telegram following [the instructions of Telethon](https://docs.telethon.dev/en/latest/basic/signing-in.html). They can also be specified in files named `.api_id` and `.api_hash` in the current working directory, respectively.
* `REPORT_CHANNEL` is the ID of a chat, group or channel for the bot to report the account changes.
* `ROOT_ADMIN` is the user ID of an additional account from where the bot accepts instructions such as adding/removing tracked accounts or elevating/lifting privileges for non-root admins.
Other configurable options are listed in [.config](https://github.com/Gowee/telegram-user-tracker/blob/master/telegram_user_tracker/config.py).

## Commands
* `/track {TARGET_USER}`: Request to start tracking a user account.
* `/ignore {TARGET_USER}`: Request to stop tracking a user account.
* `/list_tracked`: Request to display a list of all users under tracking.
* `/list_admins`: Request to display a list of admins.
* `/elevate {TARGET_USER}`: Elevate an admin.
* `/lift {TARGET_USER}`: Lift the privileges of a existing admin.

Where `TARGET_USER` can be:
* a username with or without @;
* a https://t.me url to a message the target user sent, *which works only if the message is linked in a public group or the bot is also in the private group where the message originates*;
* an id, *which won't work under many cases due to the limitation of [Telegram's abuse-prevention mechanism](https://docs.telethon.dev/en/latest/concepts/entities.html)*.

Commands in any chats or groups where the bot is in will be accepted as long as the requester has been granted proper admin privileges. The bot reports only on successful command requests in the specified `REPORT_CHANNEL` (instead of the chat or group where the request is raised) and won't report any error.

Only root admins, which can be the bot account itself or an additional one specified as mentioned above, can elevate or lift admin (privileges).
