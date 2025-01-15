from datetime import datetime, date

import requests
from flask import request

import settings
from funding.factory import cache


def json_encoder(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


class Summary:
    @staticmethod
    @cache.cached(timeout=600, key_prefix="fetch_prices")
    def fetch_prices():
        _rates = coin_btc_usd_value()
        return {
            'coin-btc': _rates['beam']['btc'],
            'coin-usd': _rates['beam']['usd'],
        }

    @staticmethod
    @cache.cached(timeout=600, key_prefix="funding_stats")
    def fetch_stats():
        from funding.factory import db
        from funding.orm import Proposal, User

        data = {}
        categories = settings.FUNDING_CATEGORIES
        statuses = settings.FUNDING_STATUSES.keys()

        for cat in categories:
            q = db.session.query(Proposal)
            q = q.filter(Proposal.category == cat)
            res = q.count()
            data.setdefault('cats', {})
            data['cats'][cat] = res

        for status in statuses:
            q = db.session.query(Proposal)
            q = q.filter(Proposal.status == status)
            res = q.count()
            data.setdefault('statuses', {})
            data['statuses'][status] = res

        data.setdefault('users', {})
        data['users']['count'] = db.session.query(User.id).count()
        return data


def price_cmc_btc_usd():
    headers = {'User-Agent': 'Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0'}
    try:
        r = requests.get('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd', headers=headers)
        r.raise_for_status()
        data = r.json()
        btc = next(c for c in data if c['symbol'] == 'btc')
        return btc['current_price']
    except:
        return

def coin_btc_usd_value():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0',
        'accept': 'application/json',
        # 'x-cg-pro-api-key': settings.CG_API_KEY
   }
    try:
        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=beam&vs_currencies=usd,btc', headers=headers)
        r.raise_for_status()
        return r.json()
    except:
        return

def coin_to_usd(amt: float, coin_usd: float):
    try:
        return round((amt * coin_usd), 2)
    except:
        pass

def get_ip():
    return request.headers.get('X-Forwarded-For') or request.remote_addr
