import logging
from datetime import datetime
from telegram.ext import Updater

from config import Config, Messages
from db import Session, User, Code
from functions import scrape_wiki, redeem_user_codes

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


def main():
    with open(Config.TOKEN_URI) as f:
        token = f.read()
    updater = Updater(token, use_context=True)

    session = Session()

    scrape_wiki(session)

    users = session.query(User).all()
    for user in users:
        logging.debug(f'Checking for unredeemed codes for {user}')
        unredeemed = session.query(Code).filter(~Code.used_by.contains(user),
                                                Code.expired != True).all()
        if not unredeemed:
            logging.debug(f'No unredeemed codes for {user}')
            continue

        if user.cookie_expiry < datetime.utcnow():
            logging.debug(f'Unredeemed codes found, but login has expired for {user}')
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



if __name__ == '__main__':
    main()