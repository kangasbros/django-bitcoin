from django.core.management.base import NoArgsCommand, BaseCommand
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

from django.db import transaction

from optparse import make_option
from django.contrib.auth.models import User


@transaction.commit_manually
def flush_transaction():
    transaction.commit()


def CacheLock(key, lock=None, blocking=True, timeout=10):
    if lock is None:
        lock = MemcachedLock(key=key, client=cache, timeout=timeout)

    return distributedlock(key, lock, blocking)

import pytz  # 3rd party

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-u", "--users",
            action='store', type="str", dest="users"),
        )
    help = 'This creates the revenue report for a specific month.'

    def handle(self, *args, **options):

        dt_now = datetime.datetime.now()

        wallet_query = Wallet.objects.all()

        if options['users']:
            w_ids = []
            for u in options['users'].split(","):
                w_ids.append(User.objects.get(username=u).get_profile().wallet.id)
            wallet_query = wallet_query.filter(id__in=w_ids)

        for w in wallet_query:
            for ba in BitcoinAddress.objects.filter(wallet=w).exclude(migrated_to_transactions=True):
                original_balance = ba.wallet.last_balance
                with CacheLock('query_bitcoind_'+str(ba.id)):
                    dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
                    for dp in dts:
                        wt = WalletTransaction.objects.create(amount=dp.amount, to_wallet=ba.wallet, created_at=ba.created_at,
                        description=ba.address, deposit_address=ba)
                        DepositTransaction.objects.filter(id=dp.id).update(transaction=wt)
                    s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                    if s < ba.least_received_confirmed and ba.least_received_confirmed > 0:
                        wt = WalletTransaction.objects.create(amount=ba.least_received_confirmed - s, to_wallet=ba.wallet, created_at=ba.created_at,
                            description=u"Deposits "+ba.address+u" "+ ba.created_at.strftime("%x")  + u" - "+ dt_now.strftime("%x"),
                            deposit_address=ba)
                        dt = DepositTransaction.objects.create(address=ba, amount=wt.amount, wallet=ba.wallet,
                            created_at=ba.created_at, transaction=wt, confirmations=settings.BITCOIN_MINIMUM_CONFIRMATIONS,
                            description=u"Deposits "+ba.address+u" "+ ba.created_at.strftime("%x")  + u" - "+ dt_now.strftime("%x"))
                        print dt.description, dt.amount
                    elif s > ba.least_received_confirmed:
                        print "TOO MUCH!!!", ba.address
                    elif s < ba.least_received_confirmed:
                        print "too little, address", ba.address, ba.least_received_confirmed, s
                    BitcoinAddress.objects.filter(id=ba.id).update(migrated_to_transactions=True)
                flush_transaction()
                wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                if wt_sum != ba.least_received_confirmed:
                    raise Exception("wrong amount! "+str(ba.address))
                w = Wallet.objects.get(id=ba.wallet.id)
                if original_balance != w.total_balance_sql():
                    raise Exception("wrong wallet amount! "+str(ba.address))
                tot_received = WalletTransaction.objects.filter(from_wallet=None).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                tot_received_bitcoinaddress = BitcoinAddress.objects.filter(migrated_to_transactions=True)\
                    .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
                if tot_received != tot_received_bitcoinaddress:
                    raise Exception("wrong total receive amount! "+str(ba.address))

        for ba in BitcoinAddress.objects.filter(migrated_to_transactions=True):
            dts = ba.deposittransaction_set.filter(address=ba)
            deposit_sum = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
            wt_sum = Decimal(0)
            for dp in dts:
                if dp.transaction:
                    wt_sum += dp.transaction.amount
            if wt_sum != deposit_sum or ba.least_received_confirmed != deposit_sum:
                print "Bitcoinaddress integrity error!", ba.address, deposit_sum, wt_sum, ba.least_received_confirmed
