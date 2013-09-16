from django.core.management.base import NoArgsCommand
from time import sleep, time
from django_bitcoin.utils import bitcoind
from django_bitcoin.models import BitcoinAddress, DepositTransaction
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
        while time() - start_time < float(RUN_TIME_SECONDS):
            print "starting round", time() - start_time
            # print "starting standard", time() - start_time
            transactions = bitcoind.bitcoind_api.listtransactions("*", 50, 0)
            for t in transactions:
                if t[u'category'] != u'immature' and (not last_check_time or (int(t['time'])) >= last_check_time) and t[u'amount']>0:
                    dps = DepositTransaction.objects.filter(txid=t[u'txid'])
                    if dps.count() == 0:
                        try:
                            ba = BitcoinAddress.objects.get(address=t['address'], active=True, wallet__isnull=False)
                            if ba:
                                ba.query_bitcoind(0, triggered_tx=t[u'txid'])
                            last_check_time = int(t['time'])
                        except BitcoinAddress.DoesNotExist:
                            pass
                    elif Decimal(str(t[u'amount'])) == dps[0].amount and int(t[u'confirmations'])>dps[0].confirmations and dps.count()==1:
                        dp = dps[0]
                        DepositTransaction.objects.filter(id=dp.id).update(confirmations=int(t[u'confirmations']))
                        if int(t[u'confirmations']) >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                            dp.address.query_bitcoind(triggered_tx=t[u'txid'])
                elif not last_check_time:
                    last_check_time = int(t['time'])
            print "done listtransactions checking, starting checking least_received>least_received_confirmed", time() - start_time
            for ba in BitcoinAddress.objects.filter(active=True,
                wallet__isnull=False).extra(where=["least_received>least_received_confirmed"]).order_by("?")[:5]:
                ba.query_bitcoind()
            print "done, sleeping...", time() - start_time
            sleep(1)
        print "finished all", datetime.datetime.now()
