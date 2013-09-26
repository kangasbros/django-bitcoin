
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
            print "d", d.address, d.amount, d.created_at, d.transaction
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

python manage.py shell_plus
import datetime
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
