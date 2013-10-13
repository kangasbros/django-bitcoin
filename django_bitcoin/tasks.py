from __future__ import with_statement

import datetime
import random
import hashlib
import base64
from decimal import Decimal

from django.db import models

from django_bitcoin.utils import bitcoind
from django_bitcoin import settings

from django.utils.translation import ugettext as _
from django_bitcoin.models import DepositTransaction, BitcoinAddress

import django.dispatch

import jsonrpc

from BCAddressField import is_valid_btc_address

from django.db import transaction as db_transaction
from celery import task
from distributedlock import distributedlock, MemcachedLock, LockNotAcquiredError
from django.core.cache import cache

from django.core.mail import mail_admins

def NonBlockingCacheLock(key, lock=None, blocking=False, timeout=10000):
    if lock is None:
        lock = MemcachedLock(key=key, client=cache, timeout=timeout)

    return distributedlock(key, lock, blocking)

@task()
def query_transactions():
    with NonBlockingCacheLock("query_transactions_ongoing"):
        blockcount = bitcoind.bitcoind_api.getblockcount()
        max_query_block = blockcount - settings.BITCOIN_MINIMUM_CONFIRMATIONS - 1
        if cache.get("queried_block_index"):
            query_block = min(int(cache.get("queried_block_index")), max_query_block)
        else:
            query_block = blockcount - 100
        blockhash = bitcoind.bitcoind_api.getblockhash(query_block)
        # print query_block, blockhash
        transactions = bitcoind.bitcoind_api.listsinceblock(blockhash)
        # print transactions
        transactions = [tx for tx in transactions["transactions"] if tx["category"]=="receive"]
        print transactions
        for tx in transactions:
            ba = BitcoinAddress.objects.filter(address=tx[u'address'])
            if ba.count() > 1:
                raise Exception(u"Too many addresses!")
            if ba.count() == 0:
                print "no address found, address", tx[u'address']
                continue
            ba = ba[0]
            dps = DepositTransaction.objects.filter(txid=tx[u'txid'], amount=tx['amount'], address=ba)
            if dps.count() > 1:
                raise Exception(u"Too many deposittransactions for the same ID!")
            elif dps.count() == 0:
                deposit_tx = DepositTransaction.objects.create(wallet=ba.wallet,
                    address=ba,
                    amount=tx['amount'],
                    txid=tx[u'txid'],
                    confirmations=int(tx['confirmations']))
                if deposit_tx.confirmations >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                    ba.query_bitcoin_deposit(deposit_tx)
                else:
                    ba.query_unconfirmed_deposits()
            elif dps.count() == 1 and not dps[0].under_execution:
                deposit_tx = dps[0]
                if int(tx['confirmations']) >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                    ba.query_bitcoin_deposit(deposit_tx)
                if int(tx['confirmations']) > deposit_tx.confirmations:
                    DepositTransaction.objects.filter(id=deposit_tx.id).update(confirmations=int(tx['confirmations']))
            elif dps.count() == 1:
                print "already processed", dps[0].txid, dps[0].transaction
            else:
                print "FUFFUFUU"

        cache.set("queried_block_index", max_query_block)

import sys
from cStringIO import StringIO

@task()
def check_integrity():
    from django_bitcoin.models import Wallet, BitcoinAddress, WalletTransaction, DepositTransaction
    from django_bitcoin.utils import bitcoind
    from django.db.models import Avg, Max, Min, Sum
    from decimal import Decimal

    import sys
    from cStringIO import StringIO
    backup = sys.stdout
    sys.stdout = StringIO()

    bitcoinaddress_sum = BitcoinAddress.objects.filter(active=True)\
        .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
    print "Total received, sum", bitcoinaddress_sum
    transaction_wallets_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__id__gt=0)\
        .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    print "Total transactions, sum", transaction_wallets_sum
    transaction_out_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0)\
        .exclude(to_bitcoinaddress="").exclude(to_bitcoinaddress="")\
        .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    print "Total outgoing, sum", transaction_out_sum
    # for x in WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress=""):
    #   print x.amount, x.created_at
    fee_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress="")\
        .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    print "Fees, sum", fee_sum
    print "DB balance", (bitcoinaddress_sum - transaction_out_sum - fee_sum)
    print "----"
    bitcoind_balance = bitcoind.bitcoind_api.getbalance()
    print "Bitcoind balance", bitcoind_balance
    print "----"
    print "Wallet quick check"
    total_sum = Decimal(0)
    for w in Wallet.objects.filter(last_balance__lt=0):
        if w.total_balance()<0:
            bal = w.total_balance()
            # print w.id, bal
            total_sum += bal
    print "Negatives:", Wallet.objects.filter(last_balance__lt=0).count(), "Amount:", total_sum
    print "Migration check"
    tot_received = WalletTransaction.objects.filter(from_wallet=None).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    tot_received_bitcoinaddress = BitcoinAddress.objects.filter(migrated_to_transactions=True)\
        .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
    tot_received_unmigrated = BitcoinAddress.objects.filter(migrated_to_transactions=False)\
        .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
    if tot_received != tot_received_bitcoinaddress:
        print "wrong total receive amount! "+str(tot_received)+", "+str(tot_received_bitcoinaddress)
    print "Total " + str(tot_received) + " BTC deposits migrated, unmigrated " + str(tot_received_unmigrated) + " BTC"
    print "Migration check #2"
    dts = DepositTransaction.objects.filter(address__migrated_to_transactions=False).exclude(transaction=None)
    if dts.count() > 0:
        print "Illegal transaction!", dts
    if WalletTransaction.objects.filter(from_wallet=None, deposit_address=None).count() > 0:
        print "Illegal deposit transactions!"
    print "Wallet check"
    for w in Wallet.objects.filter(last_balance__gt=0):
        lb = w.last_balance
        tb_sql = w.total_balance_sql()
        tb = w.total_balance()
        if lb != tb or w.last_balance != tb or tb != tb_sql:
            print "Wallet balance error!", w.id, lb, tb_sql, tb
            print w.sent_transactions.all().count()
            print w.received_transactions.all().count()
            print w.sent_transactions.all().aggregate(Max('created_at'))['created_at__max']
            print w.received_transactions.all().aggregate(Max('created_at'))['created_at__max']
            # Wallet.objects.filter(id=w.id).update(last_balance=w.total_balance_sql())
    # print w.created_at, w.sent_transactions.all(), w.received_transactions.all()
        # if random.random() < 0.001:
        #     sleep(1)
    print "Address check"
    for ba in BitcoinAddress.objects.filter(least_received_confirmed__gt=0, migrated_to_transactions=True):
        dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
        s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        if s != ba.least_received:
            print "DepositTransaction error", ba.address, ba.least_received, s
            print "BitcoinAddress check"
    for ba in BitcoinAddress.objects.filter(migrated_to_transactions=True):
        dts = ba.deposittransaction_set.filter(address=ba, confirmations__gte=settings.BITCOIN_MINIMUM_CONFIRMATIONS)
        deposit_sum = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        if wt_sum != deposit_sum or ba.least_received_confirmed != deposit_sum:
            print "Bitcoinaddress integrity error!", ba.address, deposit_sum, wt_sum, ba.least_received_confirmed
        # if random.random() < 0.001:
        #     sleep(1)

    integrity_test_output = sys.stdout.getvalue() # release output
    # ####

    sys.stdout.close()  # close the stream
    sys.stdout = backup # restore original stdout
    mail_admins("Integrity check", integrity_test_output)
