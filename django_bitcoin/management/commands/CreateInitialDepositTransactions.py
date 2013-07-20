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
from django_bitcoin.models import DepositTransaction, BitcoinAddress
from django.db.models import Avg, Max, Min, Sum
from decimal import Decimal

import pytz  # 3rd party

class Command(NoArgsCommand):
    help = 'Create a profile object for users which do not have one.'

    def handle_noargs(self, **options):
        dt_now = datetime.datetime.now()

        for ba in BitcoinAddress.objects.exclude(wallet=None):
            dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
            s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
            if s < ba.least_received_confirmed and ba.least_received_confirmed > 0:
                dt = DepositTransaction.objects.create(address=ba, amount=ba.least_received_confirmed, wallet=ba.wallet,
                    created_at=ba.created_at,
                    description=u"Deposits "+ba.address+u" "+unicode(ba.created_at) + u" - "+unicode(dt_now))
                print dt.description, dt.amount
            elif s > ba.least_received_confirmed:
                print "TOO MUCH!!!", ba.address
            elif s < ba.least_received_confirmed:
                print "too little, address", ba.address, ba.least_received_confirmed, s
