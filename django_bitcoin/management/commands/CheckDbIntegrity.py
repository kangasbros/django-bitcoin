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
        bitcoinaddress_sum = sum([x.received() for x in BitcoinAddress.objects.filter(active=True)])
        print "Total received, sum", bitcoinaddress_sum
        transaction_wallets_sum = sum([x.amount for x in WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__id__gt=0)])
        print "Total transactions, sum", transaction_wallets_sum
        transaction_out_sum = sum([x.amount for x in WalletTransaction.objects.filter(from_wallet__id__gt=0)\
        	.exclude(to_bitcoinaddress="").exclude(to_bitcoinaddress="")])
        print "Total outgoing, sum", transaction_out_sum
        # for x in WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress=""):
        # 	print x.amount, x.created_at
        fee_sum = sum([x.amount for x in WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress="")])
        print "Fees, sum", fee_sum
        print "DB balance", (bitcoinaddress_sum - transaction_out_sum - fee_sum)
        print "----"
        bitcoind_balance = bitcoind.bitcoind_api.getbalance()
        print "Bitcoind balance", bitcoind_balance
        print "----"
        print "Wallet check"
        for w in Wallet.objects.filter(last_balance__gt=0):
            lb = w.last_balance
            tb_sql = w.total_balance_sql()
            tb = w.total_balance()
            if lb != tb or w.last_balance != tb or tb != tb_sql:
                print "Wallet balance error!", w.id, lb, tb_sql, tb
                print w.created_at, w.sent_transactions.all(), w.received_transactions.all()
            # if random.random() < 0.001:
            #     sleep(1)
        print "Address check"
        for ba in BitcoinAddress.objects.filter(least_received_confirmed__gt=0):
            dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
            s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
            if s != ba.least_received_confirmed:
                print "DepositTransaction error", ba.address
            # if random.random() < 0.001:
            #     sleep(1)


