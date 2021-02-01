import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config():
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'redeemer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TOKEN_URI = os.environ.get('TOKEN_URI') or \
        os.path.join(basedir, 'token')

    WIKI_URL = 'https://afk-arena.fandom.com/wiki/Redemption_Code'
    SEND_MAIL_URL = 'https://cdkey.lilith.com/api/send-mail'
    VERIFY_CODE_URL = 'https://cdkey.lilith.com/api/verify-code'
    CONSUME_URL = 'https://cdkey.lilith.com/api/cd-key/consume'


class Messages():
    WELCOME = (
    """Hello, user {}.\n
    A verification code has been sent to your ingame mailbox.
    Please respond with /verify <verification code> to complete login."""
    )

    ALREADY_REGISTERED = (
    """You have already registered for this service.
    Please use /login if you wish to login."""
    )

    VERIFY_RESPONSES = {
        'err_wrong_code': 'Incorrect verification code. Use /verify <verification code> to try again.',
        'err_code_out_of_date': 'Verification code is out of date. Use /login for a new one.',
        'ok': 'Successfully logged in. Looking for codes to redeem...'
    }

    INSTRUCTIONS = (
    """I will automatically redeem gift codes I find for AFK Arena.\n
    The following commands are available:
    /register <UID> - Register for the service
    /verify <verification code> - Provide verification for login when prompted
    /login - Prompt a new verification code when needed"""
    )

    LOGIN_EXPIRED = (
        """There are new codes to redeem but your login has expired.
        Please use /login to login and redeem them."""
    )

    NOT_REGISTERED = (
        """You are not registered for this service.
        Please use /register <UID> to begin."""
    )

    CODES_REDEEMED = (
        """The following code(s) were successfully redeemed:
        {}"""
    )