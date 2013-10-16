
python manage.py shell_plus
from django_bitcoin.tasks import query_transactions
query_transactions()
for d in DepositTransaction.objects.all().order_by("-id")[:10]:
    print d.created_at, d.amount, d.transaction, d.under_execution

quit()



python manage.py shell_plus
from django_bitcoin.tasks import check_integrity
check_integrity()
quit()

python manage.py shell_plus
from django_bitcoin.models import update_wallet_balance
for w in Wallet.objects.filter(last_balance__gt=0):
    lb = w.last_balance
    tb_sql = w.total_balance_sql()
    tb = w.total_balance()
    if lb != tb_sql:
        print "error", w.id, lb, tb_sql
        update_wallet_balance.delay(w.id)

python manage.py shell_plus
from django_bitcoin.tasks import process_outgoing_group
process_outgoing_group()
quit()


for ot in OutgoingTransaction.objects.filter(under_execution=True):
    print ot.to_bitcoinaddress, ot.amount, ot.txid

for ot in OutgoingTransaction.objects.filter(txid=None).exclude(executed_at=None):
    print ot.executed_at, ot.to_bitcoinaddress, ot.amount, ot.txid


from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
for ba in BitcoinAddress.objects.filter(least_received_confirmed__gt=0, migrated_to_transactions=True):
    dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
    s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    if s != ba.least_received:
        print "DepositTransaction error", ba.address, ba.least_received, s
        print "BitcoinAddress check"
        for d in dts:
            print "d", d.address, d.amount, d.created_at, d.transaction, d.txid
            if not d.transaction and s > ba.least_received:
                print "DELETED"
                d.delete()
        for wt in ba.wallettransaction_set.all():
            print "wt", wt.deposit_address, wt.amount, wt.created_at, wt.deposittransaction_set.all()
        if s < ba.least_received:
            # deposit_tx = DepositTransaction.objects.create(wallet=ba.wallet,
            #         address=ba,
            #         amount=ba.least_received - s,
            #         txid="fix_manual",
            #         confirmations=9999)
            print "ADDED"

quit()

from django_bitcoin.models import process_outgoing_transactions

ots = OutgoingTransaction.objects.filter(txid=None).exclude(executed_at=None).order_by("id")[:3]
for ot in ots:
    print ot.executed_at, ot.to_bitcoinaddress, ot.amount, ot.txid
    print OutgoingTransaction.objects.filter(id=ot.id).update(executed_at=None)

process_outgoing_transactions()

from decimal import Decimal
kb = UserProfile.objects.get(user__username="kangasbros")
kb.wallet.send_to_address("16aoubHNmaC1p5VdJNfinx36Gbky4M8BqH", Decimal('0.0001'), expires_seconds=100)
kb.wallet.send_to_address("16aoubHNmaC1p5VdJNfinx36Gbky4M8BqH", Decimal('0.000102'), expires_seconds=100)
kb.wallet.send_to_address("16cHYRnZGBco5JNtkipBUQryExvZtNeNrS", Decimal('0.000101'), expires_seconds=0)

import datetime
import pytz
next_run_at = OutgoingTransaction.objects.all().aggregate(Min('expires_at'))['expires_at__min']
countdown=max(((next_run_at - datetime.datetime.now(pytz.utc)) + datetime.timedelta(seconds=5)).total_seconds(), 5)
if next_run_at:
    process_outgoing_transactions.retry(
        countdown=min(((next_run_at - datetime.datetime.now()) + datetime.timedelta(seconds=5)).total_seconds(), 0) )

python manage.py shell_plus
import datetime
from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
BitcoinAddress.objects.aggregate(Sum('least_received'))['least_received__sum'] or Decimal(0)
BitcoinAddress.objects.aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
bas = BitcoinAddress.objects.extra(where=["least_received>least_received_confirmed",])
for ba in bas:
    print ba.address, ba.least_received, ba.least_received_confirmed, ba.wallet.total_balance_sql(), ba.wallet.total_balance_sql(confirmed=False)
    print ba.wallet.total_balance(), ba.wallet.total_balance_unconfirmed()


python manage.py shell_plus
from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
for w in Wallet.objects.all():
    if w.total_balance()>0 or w.total_balance(0)>0 or w.total_balance_sql(confirmed=False)>0:
        print w.id, w.total_balance(), w.total_balance_sql()
        print w.id, w.total_balance(0), w.total_balance_sql(confirmed=False), w.total_balance_sql(confirmed=False)

from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
for ba in BitcoinAddress.objects.filter(migrated_to_transactions=True):
        dts = ba.deposittransaction_set.filter(address=ba, confirmations__gte=settings.BITCOIN_MINIMUM_CONFIRMATIONS)
        deposit_sum = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        if wt_sum != deposit_sum or ba.least_received_confirmed != deposit_sum:
            print "Bitcoinaddress integrity error!", ba.address, deposit_sum, wt_sum, ba.least_received_confirmed
