import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import time
from telegram.ext import Updater

from config import Config, Messages
from db import Session, User, Code
from functions import scrape_wiki, redeem_user_codes

logging.basicConfig(
    handlers=[RotatingFileHandler('./logs/scheduled.log', maxBytes=10000, backupCount=10)],
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt='%Y-%m-%dT%H:%M:%S'
)

def scheduled_scan(updater):
    session = Session()

    new = scrape_wiki(session)

    if not new:
        logging.info('No new codes to redeem in this run.')
        return

    users = session.query(User).all()
    for user in users:
        logging.info(f'Checking for unredeemed codes for {user}')
        unredeemed = session.query(Code).filter(~Code.used_by.contains(user),
                                                Code.expired != True).all()
        if not unredeemed:
            logging.info(f'No unredeemed codes for {user}')
            continue

        if user.cookie_expiry < datetime.utcnow():
            logging.info(f'Unredeemed codes found, but login has expired for {user}')
            message = Messages.LOGIN_EXPIRED
            updater.bot.send_message(chat_id=user.chat_id, text=message)
            continue

        redeemed = redeem_user_codes(session, user)
        if redeemed:
            message = Messages.CODES_REDEEMED.format('\n'.join(redeemed))
            updater.bot.send_message(chat_id=user.chat_id, text=message)

    if session.dirty:
        session.commit()
    session.close()


def main():
    with open(Config.TOKEN_URI) as f:
        token = f.read()
    updater = Updater(token, use_context=True)

    while True:
        scheduled_scan(updater)
        next_run = datetime.now() + timedelta(hours=1)
        logging.info(f'Next scan at {next_run.strftime("%Y-%m-%dT%H:%M:%S")}')
        time.sleep(3600)


if __name__ == '__main__':
    main()