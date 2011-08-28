# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

import json
import jsonrpc
import sys
import urllib
import urllib2
import random
import hashlib
import base64
from decimal import Decimal
import decimal
import warnings

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from django_bitcoin import settings
from django_bitcoin import currency

# BITCOIND COMMANDS

def quantitize_bitcoin(d):
    return d.quantize(Decimal("0.00000001"))

class BitcoindConnection(object):
    def __init__(self, connection_string, main_account_name):
        self.bitcoind_api = jsonrpc.ServiceProxy(connection_string)
        self.account_name = main_account_name

    def total_received(self, address, *args, **kwargs):
        return decimal.Decimal(
            self.bitcoind_api.getreceivedbyaddress(address, *args, **kwargs))
    
    def send(self, address, amount, *args, **kwargs):
        self.bitcoind_api.sendtoaddress(address, float(amount), *args, **kwargs)

    def create_address(self, for_account=None, *args, **kwargs):
        return self.bitcoind_api.getnewaddress(
            for_account or self.account_name, *args, **kwargs)

bitcoind = BitcoindConnection(settings.CONNECTION_STRING,
                              settings.MAIN_ACCOUNT)

def bitcoin_getnewaddress(account_name=None):
    warnings.warn("Use bitcoind.create_address(...) instead",    
                  DeprecationWarning)
    return bitcoind.create_address(account_name=account_name)

def bitcoin_getbalance(address, minconf=1):
    warnings.warn("Use bitcoind.total_received(...) instead",
                  DeprecationWarning)
    return bitcoind.total_received(address, minconf)

def bitcoin_getreceived(address, minconf=1):
    warnings.warn("Use bitcoind.total_received(...) instead",
                  DeprecationWarning)
    return bitcoind.total_received(address, minconf)

def bitcoin_sendtoaddress(address, amount):
    warnings.warn("Use bitcoind.send(...) instead",
                  DeprecationWarning)
    return bitcoind.send(address, amount)

# --------

def bitcoinprice_usd():
    """return bitcoin price from any service we can get it"""
    warnings.warn("Use django_bitcoin.currency.exchange.get_rate('USD')",
                  DeprecationWarning)
    return {"24h": currency.exchange.get_rate("USD")}

def bitcoinprice_eur():
    warnings.warn("Use django_bitcoin.currency.exchange.get_rate('EUR')",
                  DeprecationWarning)
    return {"24h": currency.exchange.get_rate("EUR")}

def bitcoinprice(currency):
    warnings.warn("Use django_bitcoin.currency.exchange.get_rate(currency)",
                  DeprecationWarning)
    return currency.exchange.get_rate(currency)

# ------

# generate a hash
def generateuniquehash(length=43, extradata=''):
    r=str(random.random())
    m = hashlib.sha256()
    m.update(r+str(extradata))
    key=m.digest()
    key=base64.urlsafe_b64encode(key)
    return key[:min(length, 43)]

import string

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + \
           string.digits + '_-'
ALPHABET_REVERSE = dict((c, i) for (i, c) in enumerate(ALPHABET))
BASE = len(ALPHABET)
SIGN_CHARACTER = '%'

def int2base64(n):
    if n < 0:
        return SIGN_CHARACTER + num_encode(-n)
    s = []
    while True:
        n, r = divmod(n, BASE)
        s.append(ALPHABET[r])
        if n == 0: break
    return ''.join(reversed(s))

def base642int(s):
    if s[0] == SIGN_CHARACTER:
        return -num_decode(s[1:])
    n = 0
    for c in s:
        n = n * BASE + ALPHABET_REVERSE[c]
    return n
