import logging
import requests
import re
import json
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from config import Config, Messages
from db import Session, Code, User


def get_wiki_codes() -> list:
    """Scrapes wiki for current redemption codes

    Returns:
     - list: Current redemption codes
    """
    html = requests.get(Config.WIKI_URL)
    soup = BeautifulSoup(html.content, 'html.parser')
    div = soup.find('div', {'class': 'mw-parser-output'})
    ul = div.find('ul', recursive=False)

    codes = []
    for li in ul.find_all('li'):
        split = li.text.split('-')
        code = split[0].strip().lower()
        codes.append(code)
    return codes


def store_codes(codes) -> list:
    """Store new codes to the database

    Args:
     - codes (list): Current redemption codes

    Returns:
     - list: Newly added codes
    """
    new_codes = []
    with Session() as session:
        for code in codes:
            if session.query(Code).filter(Code.code == code).count():
                continue
            new_code = Code(code=code)
            session.add(new_code)
            new_codes.append(code)
        session.commit()
    return new_codes



def generate_payload(endpoint, uid, code, **kwargs) -> dict:
    """Generate the requested payload for endpoint"""
    if endpoint == 'verify-afk-code':
        return {
            "uid": uid,
            "game": "afk",
            "code": code
        }
    elif endpoint == 'consume':
        return {
            "type": "cdkey_web",
            "game": "afk",
            "uid": uid,
            "cdkey": code
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


def post_login(uid, code) -> bool:
    response = send_request(Config.LOGIN_URL, uid=uid, code=code)
    decoded = json.loads(response.content.decode(encoding='utf-8'))
    logging.info(f'Response received: {decoded["info"]}')
    if decoded.get('ret') == 0:
        return response.cookies


def post_consume(uid, code, cookie) -> str:
    response = send_request(Config.CONSUME_URL, uid=uid, code=code, cookies=cookie)
    decoded = json.loads(response.content.decode(encoding='utf-8'))
    logging.info(f'Response received: {decoded}')
    info = decoded.get('info')
    return info


def redeem_user_codes(uid):
    successfully_redeemed = []

    with Session() as session:
        user = session.query(User).filter(User.uid == uid).first()
        codes = session.query(Code).filter(~Code.used_by.contains(user),
                                            Code.expired != True).all()
        for code in codes:
            info = post_consume(user.uid, code.code, user.cookie)
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

        session.commit()

    return successfully_redeemed


def scan_n_redeem(updater):
    codes = get_wiki_codes()
    store_codes(codes)

    uids = []
    with Session() as session:
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

            uids.append(user.uid)

    for uid in uids:
        redeemed = redeem_user_codes(uid)
        if redeemed:
            message = Messages.CODES_REDEEMED.format('\n'.join(redeemed))
            updater.bot.send_message(chat_id=user.chat_id, text=message)



def scheduled_scan(updater):
    while True:
        logging.info('Starting scheduled scan')
        scan_n_redeem(updater)
        next_run = datetime.now() + timedelta(hours=1)
        logging.info(f'Next scan at {next_run.strftime("%Y-%m-%dT%H:%M:%S")}')
        time.sleep(3600)