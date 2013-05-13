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
from django_bitcoin.models import get_historical_price

class Command(NoArgsCommand):
    help = 'Create a profile object for users which do not have one.'

    def handle_noargs(self, **options):
        print datetime.datetime.now(), get_historical_price()
