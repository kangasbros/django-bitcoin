from django.core.management.base import NoArgsCommand
from django.conf import settings
import os
import sys
import re
import codecs
import commands
import urllib2
import urllib
import json
import random
from time import sleep
import math
import datetime
from django_bitcoin.models import DepositTransaction, BitcoinAddress, WalletTransaction, Wallet
from django.db.models import Avg, Max, Min, Sum
from decimal import Decimal

from distributedlock import distributedlock, MemcachedLock, LockNotAcquiredError
from django.core.cache import cache

def CacheLock(key, lock=None, blocking=True, timeout=10):
    if lock is None:
        lock = MemcachedLock(key=key, client=cache, timeout=timeout)

    return distributedlock(key, lock, blocking)

import pytz  # 3rd party

class Command(NoArgsCommand):
    help = 'Create a profile object for users which do not have one.'

    def handle_noargs(self, **options):

        dt_now = datetime.datetime.now()

        for w in Wallet.objects.all():
            for ba in BitcoinAddress.objects.filter(wallet=w).exclude(migrated_to_transactions=True):
                with CacheLock('query_bitcoind_'+str(ba.id)):
                    dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
                    for dp in dts:
                        wt = WalletTransaction.objects.create(amount=dp.amount, to_wallet=ba.wallet, created_at=ba.created_at,
                        description=ba.address)
                        DepositTransaction.objects.filter(id=dp.id).update(transaction=wt)
                    s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                    if s < ba.least_received_confirmed and ba.least_received_confirmed > 0:
                        wt = WalletTransaction.objects.create(amount=ba.least_received_confirmed - s, to_wallet=ba.wallet, created_at=ba.created_at,
                            description=u"Deposits "+ba.address+u" "+ ba.created_at.strftime("%x")  + u" - "+ dt_now.strftime("%x") )
                        dt = DepositTransaction.objects.create(address=ba, amount=ba.least_received_confirmed - s, wallet=ba.wallet,
                            created_at=ba.created_at, transaction=wt, confirmations=settings.BITCOIN_MINIMUM_CONFIRMATIONS,
                            description=u"Deposits "+ba.address+u" "+ ba.created_at.strftime("%x")  + u" - "+ dt_now.strftime("%x"))
                        print dt.description, dt.amount
                    elif s > ba.least_received_confirmed:
                        print "TOO MUCH!!!", ba.address
                    elif s < ba.least_received_confirmed:
                        print "too little, address", ba.address, ba.least_received_confirmed, s
                    BitcoinAddress.objects.filter(id=ba.id).update(migrated_to_transactions=True)

for ba in BitcoinAddress.objects.filter(migrated_to_transactions=True):
    dts = ba.deposittransaction_set.filter(address=ba)
    deposit_sum = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    wt_sum = Decimal(0)
    for dp in dts:
        if dp.transaction:
            wt_sum += dp.transaction.amount
    if wt_sum != deposit_sum or ba.least_received_confirmed != deposit_sum:
        print "Bitcoinaddress integrity error!", ba.address, deposit_sum, wt_sum, ba.least_received_confirmed
