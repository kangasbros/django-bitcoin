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
    if cache.get('bitcoinprice'):
        return cache.get('bitcoinprice')
    # try first bitcoincharts
    try:
        f = urllib2.urlopen(u"http://bitcoincharts.com/t/weighted_prices.json")
        result=f.read()
        j=json.loads(result)
        cache.set('bitcoinprice', j['USD'], 60*60)
    except:
        print "Unexpected error:", sys.exc_info()[0]
        #raise

    if not cache.get('bitcoinprice'):
        if not cache.get('bitcoinprice_old'):
            return {'24h': Decimal("13.4")}
        cache.set('bitcoinprice', cache.get('bitcoinprice_old'), 60*60)

    cache.set('bitcoinprice_old', cache.get('bitcoinprice'), 60*60*24*7)
    return cache.get('bitcoinprice')

def bitcoinprice_eur():
    """return bitcoin price from any service we can get it"""
    if cache.get('bitcoinprice_eur'):
        return cache.get('bitcoinprice_eur')
    # try first bitcoincharts
    try:
        f = urllib2.urlopen(u"http://bitcoincharts.com/t/weighted_prices.json")
        result=f.read()
        j=json.loads(result)
        cache.set('bitcoinprice_eur', j['EUR'], 60*60)
    except:
        print "Unexpected error:", sys.exc_info()[0]
        #raise

    if not cache.get('bitcoinprice_eur'):
        if not cache.get('bitcoinprice_eur_old'):
            return {'24h': Decimal("10.0")}
            #raise NameError('Not any currency data')
        cache.set('bitcoinprice_eur', cache.get('bitcoinprice_eur_old'), 60*60)
        cache.set('bitcoinprice_eur_old', cache.get('bitcoinprice_eur'), 60*60*24*7)

    return cache.get('bitcoinprice')

def bitcoinprice(currency):
    if currency=="USD" or currency==1:
        return Decimal(bitcoinprice_usd()['24h'])
    elif currency=="EUR" or currency==2:
        return Decimal(bitcoinprice_eur()['24h'])

    raise NotImplementedError('This currency is not implemented')


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
