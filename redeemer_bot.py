import logging
from logging.handlers import RotatingFileHandler
import threading
import os
from datetime import datetime
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler

from config import Config, Messages

if not os.path.exists(Config.DATA_DIR):
    os.mkdir(Config.DATA_DIR)
    if not os.path.exists(os.path.dirname(Config.LOG_URI)):
        os.mkdir(os.path.dirname(Config.LOG_URI))

from functions import get_wiki_codes, store_codes, get_cookie_expiry, post_login, redeem_user_codes, scheduled_scan
from db import Session, User, Code

logging.basicConfig(
    handlers=[RotatingFileHandler(Config.LOG_URI, maxBytes=10000, backupCount=10)],
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt='%Y-%m-%dT%H:%M:%S'
)

def start(update, context):
    update.message.reply_text(Messages.INSTRUCTIONS)


def scan(update, context):
    chat_id = update.effective_chat.id

    with Session() as session:
        user = session.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            update.message.reply_text(Messages.NOT_REGISTERED)
            return
        uid = user.uid

    codes = get_wiki_codes()
    new_codes = store_codes(codes)
    if not new_codes:
        return

    update.message.reply_text(f'{len(new_codes)} codes found.')

    if user.cookie_expiry < datetime.utcnow():
        logging.info(f'Unredeemed codes found, but login has expired')
        update.message.reply_text(Messages.LOGIN_EXPIRED)
        return

    redeem_user_codes(uid)

def register(update, context):
    """Respond to /register command and prompt to /verify."""
    chat_id = update.effective_chat.id
    with Session() as session:
        if session.query(User).filter(User.chat_id == chat_id).count() > 0:
            update.message.reply_text(Messages.ALREADY_REGISTERED)
            return

    try:
        uid = int(context.args[0])
    except IndexError:
        update.message.reply_text('Use /register <UID> to begin.')
        return
    except ValueError:
        update.message.reply_text('UID must be numeric.')
        return

    context.user_data['uid'] = uid
    logging.info(f'Registration started for UID: {uid}')
    update.message.reply_text(Messages.WELCOME.format(uid))



def login(update, context):
    chat_id = update.effective_chat.id
    uid = context.user_data.get('uid')

    with Session() as session:
        user = session.query(User).filter(User.chat_id == chat_id).first()
        if user:
            uid = user.uid

    if not uid:
        update.message.reply_text(Messages.NOT_REGISTERED)
        return

    try:
        int(context.args[0])
    except IndexError:
        update.message.reply_text('Use /login <verification code> to log in.')
        return
    except ValueError:
        update.message.reply_text('Verification code must be numeric.')
        return

    code = context.args[0]
    cookies = post_login(uid, code)
    if not cookies:
        update.message.reply_text('Login unsuccessful, please try again.')
        return

    if context.user_data.get('uid'):
        del context.user_data['uid']

    with Session() as session:
        user = session.query(User).filter(User.uid == uid).first()
        if not user:
            user = User(uid=uid, chat_id=chat_id)
        user.cookie = cookies
        user.cookie_expiry = get_cookie_expiry(cookies)
        session.add(user)
        session.commit()

    redeemed = redeem_user_codes(uid)

    if redeemed:
        message = Messages.CODES_REDEEMED.format('\n'.join(redeemed))
    else:
        message = 'No new codes to redeem.'
    update.message.reply_text(message)


def main():
    with open(Config.TOKEN_URI) as f:
        token = f.read()
    updater = Updater(token, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler('register', register))
    dispatcher.add_handler(CommandHandler('scan', scan))
    dispatcher.add_handler(CommandHandler('login', login))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, start))

    # Start the Bot
    updater.start_polling()

    # Start the scheduled scan thread
    scan_schedule = threading.Thread(target=scheduled_scan, args=(updater,), daemon=True)
    scan_schedule.start()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
