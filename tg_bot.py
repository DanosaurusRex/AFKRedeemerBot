import logging
from datetime import datetime
from telegram.ext import Updater, CommandHandler

from config import Config, Messages
from functions import scrape_wiki, post_login, post_verification, redeem_user_codes
from db import Session, User, Code

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


def start(update, context):
    update.message.reply_text(Messages.INSTRUCTIONS)


def scan(update, context):
    session = Session()
    chat_id = update.effective_chat.id
    user = session.query(User).filter(User.chat_id == chat_id).first()
    if not user:
        update.message.reply_text(Messages.NOT_REGISTERED)
        session.close()
        return

    new = scrape_wiki(session)
    if session.dirty:
        session.commit()
    update.message.reply_text(f'{new} codes found.')

    codes = session.query(Code).filter(~Code.used_by.contains(user),
                                        Code.expired != True).all()
    if codes:
        if user.cookie_expiry < datetime.utcnow():
            logging.debug(f'Unredeemed codes found, but login has expired for {user}')
            update.message.reply_text(Messages.LOGIN_EXPIRED)
            session.close()
            return
        redeem_user_codes(session, user)

    if session.dirty:
        session.commit()
    session.close()


def register(update, context):
    """Respond to /register command and prompt to /verify."""
    try:
        uid = int(context.args[0])
    except IndexError:
        update.message.reply_text('Use /register <UID> to begin.')
        return
    except ValueError:
        update.message.reply_text('UID must be a number.')
        return

    chat_id = update.effective_chat.id
    session = Session()
    if session.query(User).filter(User.chat_id == chat_id).count() > 0:
        update.message.reply_text(Messages.ALREADY_REGISTERED)
        session.close()
        return

    user = User(uid=uid, chat_id=chat_id)
    valid = post_login(user)
    if valid:
        context.user_data['user'] = user
        context.user_data['mail_sent'] = True
        logging.debug(f'Registration started for UID: {uid}')
        update.message.reply_text(Messages.WELCOME.format(uid))
    else:
        update.message.reply_text(f'UID {uid} not found. Please try again.')


def login(update, context):
    chat_id = update.effective_chat.id
    session = Session()
    user = session.query(User).filter(User.chat_id == chat_id).first()

    if not user:
        update.message.reply_text(Messages.NOT_REGISTERED)
        session.close()
        return

    post_login(user)
    session.add(user)
    session.commit()
    session.close()
    context.user_data['mail_sent'] = True
    logging.debug(f'Login started for UID: {user.uid}')
    update.message.reply_text(Messages.WELCOME.format(user.uid))


def verify(update, context):
    """Respond to /verify command and redeem codes."""
    try:
        verification = context.args[0]
        int(verification)
    except IndexError:
        update.message.reply_text('Use /verify <verification code> to verify.')
        return
    except ValueError:
        update.message.reply_text('Verification code must be a number. Please try again.')
        return
    if not context.user_data.get('mail_sent'):
        update.message.reply_text('No verification mail has been sent.')
        return

    session = Session()
    chat_id = update.effective_chat.id

    user = context.user_data.get('user')
    if not user:
        user = session.query(User).filter(User.chat_id == chat_id).first()

    info = post_verification(user, verification)
    update.message.reply_text(Messages.VERIFY_RESPONSES[info])
    if info != 'ok':
        session.close()
        return

    session.add(user)
    if context.user_data.get('user'):
        del context.user_data['user']
    if context.user_data.get('mail_sent'):
        del context.user_data['mail_sent']

    redeemed = redeem_user_codes(session, user)
    session.commit()
    session.close()

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
    dispatcher.add_handler(CommandHandler('verify', verify))
    dispatcher.add_handler(CommandHandler('scan', scan))
    dispatcher.add_handler(CommandHandler('login', login))
    dispatcher.add_handler(CommandHandler('start', start))

   # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
