# AFKRedeemerBot

## Summary
Runs a persistent Telegram bot, which allows users to register for a service that will periodically scan the AFK Arena fandom wiki page for new gift codes. When new codes are found, they will be automatically redeemed for all subscribed users.

## Valid commands
- /register <UID> - this will trigger a verification mail sent to the ingame mailbox
- /login - This will trigger a verification mail for a subscribed user
- /verify <verification code> - this will verify you with AFK Arena's servers and redeem any outstanding codes

## To run locally
* Clone this repo using git clone or download the folder.
* Register for a bot token with t.me/Botfather
* Either place the token in a file called "token" in the main directory
* pip install -r requirements.txt

## To run in docker
* Clone this repo and run docker-compose up
