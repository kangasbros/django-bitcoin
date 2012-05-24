from django.core.management.base import NoArgsCommand
from time import sleep, time
from django_bitcoin.utils import bitcoind
from django_bitcoin.models import BitcoinAddress
from django.conf import settings
from decimal import Decimal

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
        while time() - start_time < float(RUN_TIME_SECONDS):
            if settings.DEBUG:
                print "starting..."
            if not last_check_time:
                addresses_json = bitcoind.bitcoind_api.listreceivedbyaddress(0)
                addresses = {}
                for t in addresses_json:
                    addresses[t['address']] = Decimal(t['amount'])
                for ba in BitcoinAddress.objects.filter(active=True):
                    if ba.address in addresses.keys() and\
                        ba.least_received < addresses[ba.address]:
                        ba.query_bitcoind()
                        ba.query_bitcoind(0)
            transactions = bitcoind.bitcoind_api.listtransactions()
            for t in transactions:
                if not last_check_time or (int(t['time'])) >= last_check_time:
                    try:
                        ba = BitcoinAddress.objects.get(address=t['address'])
                        if ba:
                            ba.query_bitcoind(0)
                        last_check_time = int(t['time'])
                    except BitcoinAddress.DoesNotExist:
                        pass
                elif not last_check_time:
                    last_check_time = int(t['time'])
            for ba in BitcoinAddress.objects.filter(active=True).extra(where=["least_received>least_received_confirmed"]):
                ba.query_bitcoind()
            if settings.DEBUG:
                print "done, sleeping..."
            sleep(1)
