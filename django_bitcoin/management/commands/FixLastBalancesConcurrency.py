from django.core.management.base import NoArgsCommand
from time import sleep, time
from django_bitcoin.utils import bitcoind
from django_bitcoin.models import BitcoinAddress
from django_bitcoin.models import Wallet
from django.conf import settings
from decimal import Decimal


class Command(NoArgsCommand):
    help = """fix balances
"""

    def handle_noargs(self, **options):
        print "starting..."
        for w in Wallet.objects.all():
            w.last_balance = w.total_balance()
            w.save()



