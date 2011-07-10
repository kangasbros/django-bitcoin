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
import numpy
import random
from time import sleep
import math
from django_bitcoin.models import RefillPaymentQueue, UpdatePayments

class Command(NoArgsCommand):
    help = 'Create a profile object for users which do not have one.'

    def handle_noargs(self, **options):
        RefillPaymentQueue()
        UpdatePayments()
