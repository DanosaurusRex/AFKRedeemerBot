import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config():
    DATA_DIR = os.environ.get('DATA_DIR') or \
        os.path.join(basedir, 'data')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(DATA_DIR, 'redeemer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TOKEN_URI = os.environ.get('TOKEN_URI') or \
        os.path.join(basedir, 'token')

    LOG_URI = os.environ.get('LOG_URI') or \
        os.path.join(basedir, 'logs', 'debug.log')

    WIKI_URL = 'https://afk-arena.fandom.com/wiki/Redemption_Code'
    LOGIN_URL = 'https://cdkey.lilith.com/api/verify-afk-code'
    CONSUME_URL = 'https://cdkey.lilith.com/api/cd-key/consume'


class Messages():
    WELCOME = (
        'Hello, user {}.\n' +
        'Please respond with /login <verification code> to complete login.'
    )

    ALREADY_REGISTERED = (
        'You have already registered for this service.\n' +
        'Please use /login <verification code> if you wish to login.'
    )

    INSTRUCTIONS = (
        'I will automatically redeem gift codes I find for AFK Arena.\n' +
        'The following commands are available:\n' +
        '/register <UID> - Register for the service\n' +
        '/login <verification code> - Prompt a new verification code when needed'
    )

    LOGIN_EXPIRED = (
        'There are new codes to redeem but your login has expired.\n' +
        'Please use /login <verification code> to login and redeem them'
    )

    NOT_REGISTERED = (
        'You are not registered for this service.\n' +
        'Please use /register <UID> to begin.'
    )

    CODES_REDEEMED = (
        'The following code(s) were successfully redeemed:\n' +
        '{}'
    )