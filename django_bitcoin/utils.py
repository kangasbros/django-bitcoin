# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

from django.conf import settings

from django.core.cache import cache

from django_bitcoin.models import BitcoinPayment

from django.db import transaction

from decimal import *

import json

import jsonrpc

import sys

import urllib

import urllib2

MAIN_ACCOUNT = getattr(settings, "BITCOIND_MAIN_ACCOUNT", "somerandomstring14aqqwd")
CONNECTION_STRING = getattr(settings, "BITCOIND_CONNECTION_STRING", "http://jeremias:kakkanaama@kangasbros.fi:8332")
PAYMENT_BUFFER_SIZE = getattr(settings, "DBITCOIN_PAYMENT_BUFFER_SIZE", 5)

bitcoind_access = jsonrpc.ServiceProxy(CONNECTION_STRING)

# BITCOIND COMMANDS

def quantitize_bitcoin(d):
    return d.quantize(Decimal("0.00000001"))

def bitcoin_getnewaddress(account_name=MAIN_ACCOUNT):
    s=bitcoind_access.getnewaddress(account_name)
    #print s
    return s

def bitcoin_getbalance(address, minconf=1):
    s=bitcoind_access.getreceivedbyaddress(address, minconf)
    #print Decimal(s)
    return Decimal(s)

def bitcoin_sendtoaddress(address, amount):
    r=bitcoind_access.sendtoaddress(address, amount)
    return True

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
             raise NameError('Not any currency data')
        cache.set('bitcoinprice_eur', cache.get('bitcoinprice_eur_old'), 60*60)
        cache.set('bitcoinprice_eur_old', cache.get('bitcoinprice_eur'), 60*60*24*7)

    return cache.get('bitcoinprice')

def bitcoinprice(currency):
    if currency=="USD" or currency==1:
        return Decimal(bitcoinprice_usd()['24h'])
    elif currency=="EUR" or currency==2:
        return Decimal(bitcoinprice_eur()['24h'])

    raise NotImplementedError('This currency is not implemented')

def RefillPaymentQueue():
    c=BitcoinPayment.objects.filter(active=False).count()
    if PAYMENT_BUFFER_SIZE>c:
        for i in range(0,PAYMENT_BUFFER_SIZE-c):
            bp=BitcoinPayment()
            bp.address=bitcoin_getnewaddress()
            bp.save()

def UpdatePayments():
    if not cache.get('last_full_check'):
        cache.set('bitcoinprice', cache.get('bitcoinprice_old'))
    bps=BitcoinPayment.objects.filter(active=True)
    for bp in bps:
        bp.amount_paid=Decimal(bitcoin_getbalance(bp.address))
        bp.save()
        print bp.amount
        print bp.amount_paid
    
    
@transaction.commit_on_success
def getNewBitcoinPayment(amount):
    bp=BitcoinPayment.objects.filter(active=False)
    if len(bp)<1:
        RefillPaymentQueue()
        bp=BitcoinPayment.objects.filter(active=False)
    bp=bp[0]
    bp.active=True
    bp.amount=amount
    bp.save()
    return bp

def getNewBitcoinPayment_eur(amount):
    print bitcoinprice_eur()
    return getNewBitcoinPayment(Decimal(amount)/Decimal(bitcoinprice_eur()['24h']))

# EOF

