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
from django_bitcoin.models import Wallet, BitcoinAddress, WalletTransaction, DepositTransaction
from django_bitcoin.utils import bitcoind
from django.db.models import Avg, Max, Min, Sum
from decimal import Decimal

class Command(NoArgsCommand):
    help = 'This checks that alles is in ordnung in django_bitcoin.'

    def handle_noargs(self, **options):
        # BitcoinAddress.objects.filter(active=True)
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
        # 	print x.amount, x.created_at
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
            raise Exception("wrong total receive amount! "+str(ba.address))
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


