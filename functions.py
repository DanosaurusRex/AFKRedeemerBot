import logging
import requests
import re
import json
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from config import Config, Messages
from db import Session, Code, User


def scrape_wiki(session) -> int:
    """Scrape fandom wiki for codes and add them to DB."""
    html = requests.get(Config.WIKI_URL)
    soup = BeautifulSoup(html.content, 'html.parser')
    table = soup.find('tbody')

    code_re = re.compile(r'>(\S+?)\s*<')

    records = []
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if cols:
            reward = cols[1].text.strip()
            matches = code_re.findall(str(cols[0]))
            for code in matches:
                code = code.lower()
                record = Code(code=code, reward=reward)
                logging.info(f'Found code: {record}')
                if session.query(Code).filter(Code.code == code).count():
                    logging.info(f'Code {record} already in db.')
                    continue
                logging.info(f'Adding Code {record} to db')
                records.append(record)
    if records:
        logging.info(f'Adding codes to DB: {records}')
        session.add_all(records)
    return len(records)


def generate_payload(endpoint, *args, **kwargs) -> dict:
    """Generate the requested payload for endpoint"""
    if endpoint == 'send-mail':
        return {
            "game": "afk",
            "uid": kwargs['uid'],
            "title": "Verification Code",
            "template": "You are currently logging in to an external payment portal. You verification code is: {{code}}. This verification code will expire in 10 minutes. Please use this code to log in. Do not send this code to anyone else. Sender: AFK Arena Team",
            "sender": "sender"
        }
    elif endpoint == 'verify-code':
        return {
            "uid": kwargs['uid'],
            "game": "afk",
            "code": kwargs['code']
        }
    elif endpoint == 'consume':
        return {
            "type": "cdkey_web",
            "game": "afk",
            "uid": kwargs['uid'],
            "cdkey": kwargs['code']
        }


def send_request(url, *args, **kwargs):
    endpoint = url.split('/')[-1]
    payload = generate_payload(endpoint, **kwargs)
    logging.info(f'Posting {endpoint} payload: {payload}')
    cookies = kwargs.get('cookies')
    return requests.post(url=url, json=payload, cookies=cookies)


def get_cookie_expiry(cookies):
    expiries = []
    for cookie in cookies:
        expiry = datetime.fromtimestamp(cookie.expires)
        expiries.append(expiry)
    return min(expiries)


def post_login(user) -> bool:
    response = send_request(Config.SEND_MAIL_URL, uid=user.uid)
    decoded = json.loads(response.content.decode(encoding='utf-8'))
    logging.info(f'Response received: {decoded["info"]}')
    if decoded.get('ret') == 0:
        user.cookie = response.cookies
        user.cookie_expiry = get_cookie_expiry(user.cookie)
        return True
    return False


def post_verification(user, verification) -> str:
    response = send_request(Config.VERIFY_CODE_URL, uid=user.uid, code=verification, cookies=user.cookie)
    decoded = json.loads(response.content.decode(encoding='utf-8'))
    info = decoded.get('info')
    logging.info(f'Response received: {info}')
    if info == 'ok':
        cookie = user.cookie.copy()  # Dumb workaround as SQLAlchemy does not recognise if an existing PickleType is updated.
        cookie.update(response.cookies)
        user.cookie = cookie
        user.cookie_expiry = get_cookie_expiry(user.cookie)
    return info


def post_consume(user, code) -> str:
    response = send_request(Config.CONSUME_URL, uid=user.uid, code=code.code, cookies=user.cookie)
    decoded = json.loads(response.content.decode(encoding='utf-8'))
    logging.info(f'Response received: {decoded}')
    info = decoded.get('info')
    return info


def redeem_user_codes(session, user):
    successfully_redeemed = []
    codes = session.query(Code).filter(~Code.used_by.contains(user),
                                        Code.expired != True).all()
    for code in codes:
        info = post_consume(user, code)
        if info in ('err_cdkey_expired', 'err_cdkey_record_not_found'):
            logging.info(f'Code: {code}, Error: {info}')
            code.expired = True
            session.add(code)
            continue

        user.redeem_code(code)
        session.add(user)

        if info == 'ok':
            logging.info(f'Code: {code} successfully redeemed.')
            successfully_redeemed.append(code.code)
    return successfully_redeemed


def scan_n_redeem(updater):
    session = Session()

    scrape_wiki(session)
    session.commit()

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

    session.commit()
    session.close()


def scheduled_scan(updater):
    while True:
        logging.info('Starting scheduled scan')
        scan_n_redeem(updater)
        next_run = datetime.now() + timedelta(hours=1)
        logging.info(f'Next scan at {next_run.strftime("%Y-%m-%dT%H:%M:%S")}')
        time.sleep(3600)