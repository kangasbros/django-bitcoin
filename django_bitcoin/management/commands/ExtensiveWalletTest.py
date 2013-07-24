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
from django_bitcoin import Wallet
from django_bitcoin.utils import bitcoind
from decimal import Decimal
import warnings
import twitter

class Command(NoArgsCommand):
    help = 'Tweet with LocalBitcoins.com account.'

    def handle_noargs(self, **options):
        final_wallets = []
        process_num = random.randint(0, 1000)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",category=RuntimeWarning)
            for i in range(0, 3):
                w = Wallet.objects.create()
                # print "starting w.id", w.id
                addr = w.receiving_address()
                # print "taddr", w.id, addr
                final_wallets.append(w)
        for w in final_wallets:
            if w.total_balance_sql() > 0:
                print str(process_num) + " error", w.id
                raise Exception("damn!")
            # print "final", w.id, w.static_receiving_address(), w.receiving_address()
        print str(process_num) + " loading 0.001 to wallet #1", w1.static_receiving_address()
        w1 = final_wallets[0]
        w2 = final_wallets[1]
        w3 = final_wallets[2]
        bitcoind.send(w1.static_receiving_address(), Decimal("0.001"))
        while w1.total_balance_sql() <= 0:
            sleep(1)
            w1 = Wallet.objects.get(id=w1.id)
            # print w1.last_balance
        print str(process_num) + " w1.last_balance " + str(w1.last_balance)
        print str(process_num) + "loading"
        w1.send_to_wallet(w2, Decimal("0.0002"))
        w1.send_to_wallet(w3, Decimal("0.0005"))
        w3.send_to_address(w1, Decimal("0.0004"))
        print str(process_num) + " w1.last_balance " + str(w1.last_balance)
        print str(process_num) + " w2.last_balance " + str(w2.last_balance)
        print str(process_num) + " w3.last_balance " + str(w3.last_balance)
        while w1.total_balance_sql() <= 0:
            sleep(1)
            w1 = Wallet.objects.get(id=w1.id)
        print str(process_num) + "catching"
        print str(process_num) + " w1.last_balance " + str(w1.last_balance)
        print str(process_num) + " w2.last_balance " + str(w2.last_balance)
        print str(process_num) + " w3.last_balance " + str(w3.last_balance)


