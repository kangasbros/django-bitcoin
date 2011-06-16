from __future__ import with_statement
from django.db import models
import random
import hashlib
import base64
import jsonrpc
import json
from django.core.cache import cache
import urllib
import urllib2
from decimal import *
from django.contrib.sites.models import Site
import settings
import datetime
from django

from django.contrib.auth.models import User

from django.db import transaction

PAYMENT_BUFFER_SIZE = getattr(settings, "DBITCOIN_PAYMENT_BUFFER_SIZE", 5)
CONNECTION_STRING = getattr(settings, "BITCOIND_CONNECTION_STRING", "http://jeremias:kakkanaama@kangasbros.fi:8332")
MAIN_ACCOUNT = getattr(settings, "BITCOIND_MAIN_ACCOUNT", "somerandomstring14aqqwd")
PAYMENT_VALID_HOURS = getattr(settings, "BITCOIND_PAYMENT_VALID_HOURS", 128)

ESCROW_PAYMENT_TIME_HOURS = getattr(settings, "BITCOIND_ESCROW_PAYMENT_TIME_HOURS", 4)
ESCROW_RELEASE_TIME_DAYS = getattr(settings, "BITCOIND_ESCROW_RELEASE_TIME_DAYS", 14)

bitcoind_access = jsonrpc.ServiceProxy(CONNECTION_STRING)

def bitcoin_getnewaddress(account_name=MAIN_ACCOUNT):
    s=bitcoind_access.getnewaddress(account_name)
    #print s
    return s

def bitcoin_getbalance(address):
    s=bitcoind_access.getreceivedbyaddress(address)
    #print Decimal(s)
    return Decimal(s)

def generateuniquehash(length=43, extradata=''):
    r=str(random.random())
    m = hashlib.sha256()
    m.update(r+str(extradata))
    key=m.digest()
    key=base64.urlsafe_b64encode(key)
    return key[:min(length, 43)]

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

class BitcoinPayment(models.Model):
    """docstring"""
    description = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal("0.0"))
    amount_paid = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal("0.0"))
    active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    paid_at = models.DateTimeField(null=True, default=None)
    
    def is_paid(self):
        self.update_payment()
        return self.amount_paid>=self.amount

    def update_payment(self):
        new_amount=Decimal(bitcoin_getbalance(self.address))
        if new_amount>=self.amount_paid:
            self.amount_paid=new_amount
            self.save()
        if (datetime.datetime.now()-self.updated_at)>datetime.timedelta(hours=PAYMENT_VALID_HOURS):
            self.deactivate()

    def deactivate(self):
        if self.amount_paid>Decimal(0):
            return False
        self.active=False
        self.description=""
        self.save()
        return True
    
    #def save(self, force_insert=False, force_update=False):
    #

    @models.permalink
    def get_absolute_url(self):
        return ('view_or_url_name')

class BitcoinEscrow(models.Model):
    """Bitcoin escrow payment"""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    seller = models.ForeignKey(User)
    
    bitcoin_payment = models.ForeignKey(BitcoinPayment)

    confirm_hash = models.CharField(max_length=50, blank=True)
    
    buyer_address = models.TextField()
    buyer_phone = models.CharField(max_length=20, blank=True)
    buyer_email = models.EmailField(max_length=75)
    
    def save(self, force_insert=False, force_update=False):
        super(BitcoinEscrow, self).save(force_insert=force_insert, force_update=force_update)
        if not self.confirm_hash:
            self.confirm_hash=generateuniquehash(length=32, extradata=str(self.id))
            super(BitcoinEscrow, self).save(force_insert=force_insert, force_update=force_update)
    
    @models.permalink
    def get_absolute_url(self):
        return ('view_or_url_name' )


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
