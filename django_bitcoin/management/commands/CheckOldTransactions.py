from django.core.management.base import NoArgsCommand
from time import sleep, time
from django_bitcoin.utils import bitcoind
from django_bitcoin.models import BitcoinAddress
from django.conf import settings
from decimal import Decimal
import datetime

RUN_TIME_SECONDS = 60


class Command(NoArgsCommand):
    help = """This needs transactions signaling enabled. Polls\
     incoming transactions via listtransactions -bitcoind call, and checks\
      the balances accordingly.
      To enable, add this command to your cron, and set
      BITCOIN_TRANSACTION_SIGNALING = True
      After that, you will get signals from the transactions you do.
      balance_changed = django.dispatch.Signal(providing_args=["balance", "changed"])
"""

    def handle_noargs(self, **options):
        start_time = time()
        last_check_time = None
        print "starting overall1", time() - start_time, datetime.datetime.now()
        print "starting round", time() - start_time
        if not last_check_time:
            addresses_json = bitcoind.bitcoind_api.listreceivedbyaddress(0, True)
            addresses = {}
            for t in addresses_json:
                addresses[t['address']] = Decimal(t['amount'])
            for ba in BitcoinAddress.objects.filter(active=True, wallet__isnull=False):
                if ba.address in addresses.keys() and\
                    ba.least_received < addresses[ba.address]:
                    ba.query_bitcoind()
                    ba.query_bitcoind(0)
            print "finished initial scan", time() - start_time
            print "starting overall2", time() - start_time
