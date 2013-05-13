from __future__ import with_statement

import datetime
import random
import hashlib
import base64
from decimal import Decimal

from django.db import models
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from django_bitcoin.utils import *
from django_bitcoin.utils import bitcoind
from django_bitcoin import settings

from django.utils.translation import ugettext as _

import django.dispatch

import jsonrpc

from BCAddressField import is_valid_btc_address

from django.db import transaction as db_transaction


balance_changed = django.dispatch.Signal(providing_args=["changed", "transaction", "bitcoinaddress"])
balance_changed_confirmed = django.dispatch.Signal(providing_args=["changed", "transaction", "bitcoinaddress"])


currencies = (
    (1, "USD"),
    (2, "EUR"),
    (3, "BTC")
)

# XXX There *is* a risk when dealing with less then 6 confirmations. Check:
# http://eprint.iacr.org/2012/248.pdf
# http://blockchain.info/double-spends
# for an informed decision.
confirmation_choices = (
    (0, "0, (quick, recommended)"),
    (1, "1, (safer, slower for the buyer)"),
    (5, "5, (for the paranoid, not recommended)")
)

class Transaction(models.Model):
    created_at = models.DateTimeField(default=datetime.datetime.now)
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    address = models.CharField(max_length=50)


class BitcoinAddress(models.Model):
    address = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    active = models.BooleanField(default=False)
    least_received = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal(0))
    least_received_confirmed = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal(0))
    label = models.CharField(max_length=50, blank=True, null=True, default=None)

    wallet = models.ForeignKey("Wallet", null=True, related_name="addresses")

    class Meta:
        verbose_name_plural = 'Bitcoin addresses'

    def query_bitcoind(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        r = bitcoind.total_received(self.address, minconf=minconf)
        if r > self.least_received:
            if settings.BITCOIN_TRANSACTION_SIGNALING:
                if self.wallet:
                    balance_changed.send(sender=self.wallet, changed=(r - self.least_received), bitcoinaddress=self)
            # self.least_received = r
            # self.save()
            BitcoinAddress.objects.filter(id=self.id).update(least_received=r)
        if r > self.least_received_confirmed and \
            minconf >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
            if settings.BITCOIN_TRANSACTION_SIGNALING:
                if self.wallet:
                    balance_changed_confirmed.send(sender=self.wallet,
                        changed=(r - self.least_received_confirmed), bitcoinaddress=self)
            # self.least_received_confirmed = r
            # self.save()
            BitcoinAddress.objects.filter(id=self.id).update(least_received_confirmed=r)
        return r

    def received(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        if settings.BITCOIN_TRANSACTION_SIGNALING:
            if minconf >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                return self.least_received_confirmed
            else:
                return self.least_received
        return self.query_bitcoind(minconf)

    def __unicode__(self):
        if self.label:
            return u'%s (%s)' % (self.label, self.address)
        return self.address


def new_bitcoin_address():
    while True:
        with db_transaction.autocommit():
            db_transaction.enter_transaction_management()
            db_transaction.commit()
            bp = BitcoinAddress.objects.filter(Q(active=False) & Q(wallet__isnull=True) & \
                    Q(least_received__lte=0))
            if len(bp) < 1:
                refill_payment_queue()
                db_transaction.commit()
                print "refilling queue...", bp
            else:
                bp = bp[0]
                updated = BitcoinAddress.objects.select_for_update().filter(Q(id=bp.id) & Q(active=False) & Q(wallet__isnull=True) & \
                    Q(least_received__lte=0)).update(active=True)
                db_transaction.commit()
                if updated:
                    return bp
                else:
                    print "wallet transaction concurrency:", bp.address


class Payment(models.Model):
    description = models.CharField(
        max_length=255,
        blank=True)
    address = models.CharField(
        max_length=50)
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    amount_paid = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    active = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=datetime.datetime.now)
    updated_at = models.DateTimeField()

    paid_at = models.DateTimeField(null=True, default=None)

    withdrawn_total = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))

    transactions = models.ManyToManyField(Transaction)

    def calculate_amount(self, proportion):
        return quantitize_bitcoin(
            Decimal((proportion/Decimal("100.0"))*self.amount))

    def add_transaction(self, amount, address):
        self.withdrawn_total += amount
        bctrans = self.transactions.create(
            amount=amount,
            address=address)
        self.save()

        return bctrans

    def withdraw_proportion(self, address, proportion):
        if proportion<=Decimal("0") or proportion>Decimal("100"):
            raise Exception("Illegal proportion.")

        amount = self.calculate_amount(proportion)

        if self.amount-self.withdrawn_total > amount:
            raise Exception("Trying to withdraw too much.")

        self.add_transaction(amount, address)
        bitcoind.send(address, amount)

    @classmethod
    def withdraw_proportion_all(cls, address, bitcoin_payments_proportions):
        """hash BitcoinPayment -> Proportion"""
        final_amount=Decimal("0.0")
        print bitcoin_payments_proportions
        for bp, proportion in bitcoin_payments_proportions.iteritems():
            am=bp.calculate_amount(proportion)
            final_amount+=am
            bp.add_transaction(am, address)
        bitcoind.send(address, final_amount)
        return True

    def withdraw_amounts(self, addresses_shares):
        """hash address -> percentage (string -> Decimal)"""
        if self.amount_paid<self.amount:
            raise Exception("Not paid.")
        if self.withdrawn_at:
            raise Exception("Trying to withdraw again.")
        if sum(addresses_shares.values())>100:
            raise Exception("Sum of proportions must be <=100.")
        #self.withdraw_addresses=",".join(addresses)
        #self.withdraw_proportions=",".join([str(x) for x in proportions])
        amounts=[]
        for p in addresses_shares.values():
            if p<=0:
                raise Exception()
            am=quantitize_bitcoin(Decimal((p/Decimal("100.0"))*self.amount))
            amounts.append(am)
        #self.withdraw_proportions=",".join([str(x) for x in ])
        if sum(amounts)>self.amount:
            raise Exception("Sum of calculated amounts exceeds funds.")
        return amounts

    @classmethod
    def calculate_amounts(cls, bitcoinpayments, addresses_shares):
        amounts_all=[Decimal("0.0") for _i in addresses_shares]
        for amount, payment in zip(amounts_all, bitcoinpayments):
            withdrawn=payment.withdraw_amounts(addresses_shares)
            amounts_all=[(w+total) for w, total in zip(withdrawn, amounts_all)]
        return amounts_all

    @classmethod
    def withdraw_all(cls, bitcoinpayments, addresses_shares):
        #if len(bitcoinpayments)!=len(addresses_shares):
        #    raise Exception("")
        amounts_all=Payment.calculate_amounts(bitcoinpayments, addresses_shares)
        for bp in bitcoinpayments:
            am=bp.withdraw_amounts(addresses_shares)
            bp.withdraw_addresses=",".join(addresses_shares.keys())
            bp.withdraw_proportions=",".join(
                [str(x) for x in addresses_shares.values()])
            bp.withdraw_amounts=",".join(
                [str(x) for x in am])
            bp.withdrawn_at=datetime.datetime.now()
            bp.withdrawn_total=sum(am)
            bp.save()
        for i, share in enumerate(addresses_shares.keys()):
            bitcoind.send(share, amounts_all[i])
        return True

    def is_paid(self, minconf=1):
        if self.paid_at:
            return True
        self.update_payment(minconf=minconf)
        return self.amount_paid>=self.amount

    def getbalance(self, minconf=1):
        return bitcoind.total_received(self.address, minconf=minconf)

    def update_payment(self, minconf=1):
        new_amount=Decimal(bitcoin_getbalance(self.address, minconf=minconf))
        print "blaa", new_amount, self.address
        if new_amount>=self.amount:
            self.amount_paid=new_amount
            self.paid_at=datetime.datetime.now()
            self.save()
        #elif (datetime.datetime.now()-self.updated_at)>datetime.timedelta(hours=PAYMENT_VALID_HOURS):
        #    self.deactivate()

    def deactivate(self):
        return False
        if self.amount_paid > Decimal("0"):
            return False
        self.active=False
        self.description=""
        self.save()
        return True

    def save(self, **kwargs):
        self.updated_at = datetime.datetime.now()
        return super(Payment, self).save(**kwargs)

    def __unicode__(self):
        return unicode(self.amount_paid)

    @models.permalink
    def get_absolute_url(self):
        return ('view_or_url_name',)

class WalletTransaction(models.Model):
    created_at = models.DateTimeField(default=datetime.datetime.now)
    from_wallet = models.ForeignKey(
        'Wallet',
        related_name="sent_transactions")
    to_wallet = models.ForeignKey(
        'Wallet',
        null=True,
        related_name="received_transactions")
    to_bitcoinaddress = models.CharField(
        max_length=50,
        blank=True)
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    description = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        if self.from_wallet and self.to_wallet:
            return u"Wallet transaction "+unicode(self.amount)
        elif self.from_wallet and self.to_bitcoinaddress:
            return u"Outgoing bitcoin transaction "+unicode(self.amount)
        return u"Fee "+unicode(self.amount)

    def confirmation_status(self,
                            minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS,
                            transactions=None):
        """
        Returns the confirmed and unconfirmed parts of this transfer.
        Also accepts and returns a list of transactions that are being
        currently used.

        The sum of the two amounts is the total transaction amount.
        """

        if not transactions: transactions = {}

        if minconf == 0 or self.to_bitcoinaddress:
            return (0, self.amount, transactions)

        _, confirmed, txs = self.from_wallet.balance(minconf=minconf,
                                             timeframe=self.created_at,
                                             transactions=transactions)
        transactions.update(txs)

        if confirmed > self.amount: confirmed = self.amount
        unconfirmed = self.amount - confirmed

        return (unconfirmed, confirmed, transactions)

from django.db.models import Q

class Wallet(models.Model):
    created_at = models.DateTimeField(default=datetime.datetime.now)
    updated_at = models.DateTimeField()

    label = models.CharField(max_length=50, blank=True)
    # DEPRECATED: changed to foreign key
    # addresses = models.ManyToManyField(BitcoinAddress, through="WalletBitcoinAddress")
    transactions_with = models.ManyToManyField(
        'self',
        through=WalletTransaction,
        symmetrical=False)

    transaction_counter = models.IntegerField(default=1)
    last_balance = models.DecimalField(default=Decimal(0), max_digits=16, decimal_places=8)

    def __unicode__(self):
        return u"%s: %s" % (self.label,
                            self.created_at.strftime('%Y-%m-%d %H:%M'))

    def save(self, *args, **kwargs):
        '''No need for labels.'''
        self.updated_at = datetime.datetime.now()
        super(Wallet, self).save(*args, **kwargs)
        #super(Wallet, self).save(*args, **kwargs)

    def receiving_address(self, fresh_addr=True):
        while True:
            usable_addresses = self.addresses.filter(active=True).order_by("id")
            if fresh_addr:
                usable_addresses = usable_addresses.filter(least_received=Decimal(0))
            if usable_addresses.count():
                return usable_addresses[0].address
            addr = new_bitcoin_address()
            updated = BitcoinAddress.objects.select_for_update().filter(Q(id=addr.id) & Q(active=True) & Q(least_received__lte=0) & Q(wallet__isnull=True))\
                          .update(active=True, wallet=self)
            print "addr_id", addr.id, updated
            # db_transaction.commit()
            if updated:
                return addr.address
            else:
                raise Exception("Concurrency error!")

    def static_receiving_address(self):
        ''' Returns a static receiving address for this Wallet object.'''
        return self.receiving_address(fresh_addr=False)

    def send_to_wallet(self, otherWallet, amount, description=''):

        if type(amount) != Decimal:
            amount = Decimal(amount)
        amount = amount.quantize(Decimal('0.00000001'))

        with db_transaction.autocommit():
            db_transaction.enter_transaction_management()
            db_transaction.commit()
            if settings.BITCOIN_UNCONFIRMED_TRANSFERS:
                avail = self.total_balance_unconfirmed()
            else:
                avail = self.total_balance()
            updated = Wallet.objects.filter(Q(id=self.id)).update(last_balance=avail)

            if self == otherWallet:
                raise Exception(_("Can't send to self-wallet"))
            if not otherWallet.id or not self.id:
                raise Exception(_("Some of the wallets not saved"))
            if amount <= 0:
                raise Exception(_("Can't send zero or negative amounts"))
            if amount > avail:
                raise Exception(_("Trying to send too much"))
            # concurrency check
            new_balance = avail - amount
            updated = Wallet.objects.filter(Q(id=self.id) & Q(transaction_counter=self.transaction_counter) &
                Q(last_balance=avail))\
              .update(last_balance=new_balance, transaction_counter=self.transaction_counter+1)
            if not updated:
                print "wallet transaction concurrency:", new_balance, avail, self.transaction_counter, self.last_balance, self.total_balance()
                raise Exception(_("Concurrency error with transactions. Please try again."))
            # db_transaction.commit()
            # concurrency check end
            transaction = WalletTransaction.objects.create(
                amount=amount,
                from_wallet=self,
                to_wallet=otherWallet,
                description=description)
            # db_transaction.commit()
            self.transaction_counter = self.transaction_counter+1
            self.last_balance = new_balance
            # updated = Wallet.objects.filter(Q(id=otherWallet.id))\
            #   .update(last_balance=otherWallet.total_balance())

            if settings.BITCOIN_TRANSACTION_SIGNALING:
                balance_changed.send(sender=self,
                    changed=(Decimal(-1) * amount), transaction=transaction)
                balance_changed.send(sender=otherWallet,
                    changed=(amount), transaction=transaction)
                balance_changed_confirmed.send(sender=self,
                    changed=(Decimal(-1) * amount), transaction=transaction)
                balance_changed_confirmed.send(sender=otherWallet,
                    changed=(amount), transaction=transaction)
            return transaction

    def send_to_address(self, address, amount, description=''):
        if settings.BITCOIN_DISABLE_OUTGOING:
            raise Exception("Outgoing transactions disabled! contact support.")
        address = address.strip()

        if type(amount) != Decimal:
            amount = Decimal(amount)
        amount = amount.quantize(Decimal('0.00000001'))

        if not is_valid_btc_address(str(address)):
            raise Exception(_("Not a valid bitcoin address") + ":" + address)
        if amount <= 0:
            raise Exception(_("Can't send zero or negative amounts"))
        # concurrency check
        with db_transaction.autocommit():
            db_transaction.enter_transaction_management()
            db_transaction.commit()
            avail = self.total_balance()
            updated = Wallet.objects.filter(Q(id=self.id)).update(last_balance=avail)
            if amount > avail:
                raise Exception(_("Trying to send too much"))
            new_balance = avail - amount
            updated = Wallet.objects.filter(Q(id=self.id) & Q(transaction_counter=self.transaction_counter) &
                Q(last_balance=avail) )\
              .update(last_balance=new_balance, transaction_counter=self.transaction_counter+1)
            if not updated:
                print "address transaction concurrency:", new_balance, avail, self.transaction_counter, self.last_balance, self.total_balance()
                raise Exception(_("Concurrency error with transactions. Please try again."))
            # concurrency check end
            bwt = WalletTransaction.objects.create(
                amount=amount,
                from_wallet=self,
                to_bitcoinaddress=address,
                description=description)
            try:
                result = bitcoind.send(address, amount)
            except jsonrpc.JSONRPCException:
                bwt.delete()
                raise
            self.transaction_counter = self.transaction_counter+1
            self.last_balance = new_balance

            # check if a transaction fee exists, and deduct it from the wallet
            # TODO: because fee can't be known beforehand, can result in negative wallet balance.
            # currently isn't much of a issue, but might be in the future, depending of the application
            transaction = bitcoind.gettransaction(result)
            fee_transaction = None
            total_amount = amount
            if Decimal(transaction['fee']) < Decimal(0):
                fee_transaction = WalletTransaction.objects.create(
                    amount=Decimal(transaction['fee']) * Decimal(-1),
                    from_wallet=self)
                total_amount += fee_transaction.amount
            if settings.BITCOIN_TRANSACTION_SIGNALING:
                balance_changed.send(sender=self,
                    changed=(Decimal(-1) * total_amount), transaction=bwt)
                balance_changed_confirmed.send(sender=self,
                    changed=(Decimal(-1) * total_amount), transaction=bwt)
            return (bwt, fee_transaction)

    def update_transaction_cache(self,
                                 mincf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        """
        Finds the timestamp from the oldest transaction found with wasn't yet
        confirmed. If none, returns the current timestamp.
        """
        if mincf == 0: return datetime.datetime.now()

        transactions_checked = "bitcoin_transactions_checked_%d" % mincf
        oldest_unconfirmed = "bitcoin_oldest_unconfirmed_%d" % mincf

        if cache.get(transactions_checked):
            return cache.get(oldest_unconfirmed)
        else:
            cache.set(transactions_checked, True, 60*15)
            current_timestamp = datetime.datetime.now()
            transactions = WalletTransaction.objects.all()
            oldest = cache.get(oldest_unconfirmed)
            if oldest:
                transactions = transactions.filter(created_at__gte=oldest)

            transactions_cache = {}
            for t in transactions.order_by('created_at'):
                unc, _, txs =  t.confirmation_status(minconf=mincf, transactions=transactions_cache)
                transactions_cache.update(txs)
                if unc:
                    cache.set(oldest_unconfirmed, t.created_at)
                    return t.created_at
            cache.set(oldest_unconfirmed, current_timestamp)
            return current_timestamp

    def balance(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS,
                timeframe=None, transactions=None):
        """
        Returns a "greater or equal than minimum"  total ammount received at
        this wallet with the given confirmations at the given timeframe.
        """
        if minconf == 0: return (0, self.total_received(0) - self.total_sent())

        if not transactions: transactions = {}

        if not timeframe:
            oldest_unconfirmed = self.update_transaction_cache(minconf)
        else:
            oldest_unconfirmed = None

        csum = sum([a.received(minconf=minconf) for a in self.addresses.all()])
        usum = sum([a.received(minconf=0) for a in self.addresses.all()]) -csum

        received = self.received_transactions.all()
        sent = self.sent_transactions.all()
        if timeframe:
            received = received.filter(created_at__lt=timeframe)
            sent = sent.filter(created_at__lt=timeframe)

        def get_t(x):
            if not (x.id,minconf) in transactions:
                unc, conf, txs = x.confirmation_status(minconf,transactions)
                transactions.update(txs)
                transactions[(x.id, minconf)]= (unc, conf)
            return transactions[(x.id,minconf)]

        for t in received.order_by('created_at'):
            if oldest_unconfirmed and t.created_at < oldest_unconfirmed:
                csum += t.amount
            else:
                u,c = get_t(t)
                usum += u
                csum += c

        for t in sent.order_by('created_at'):
            if oldest_unconfirmed and t.created_at < oldest_unconfirmed:
                csum -= t.amount
            else:
                u,c = get_t(t)
                usum -= u
                csum -= c

        if not timeframe:
            return (usum, csum)  # return of a non recursive call
        else:
            return (usum, csum, transactions)  # return of a recursive call

    def total_balance_sql(self, confirmed=True):
        from django.db import connection
        cursor = connection.cursor()
        sql="""
         SELECT IFNULL((SELECT SUM(%(confirmed)s) FROM django_bitcoin_bitcoinaddress ba WHERE ba.wallet_id=%(id)s), 0)
        + IFNULL((SELECT SUM(amount) FROM django_bitcoin_wallettransaction wt WHERE wt.to_wallet_id=%(id)s), 0)
        - IFNULL((SELECT SUM(amount) FROM django_bitcoin_wallettransaction wt WHERE wt.from_wallet_id=%(id)s), 0) as total_balance;
        """ % {'confirmed': ("least_received", "least_received_confirmed")[confirmed], 'id': self.id}
        cursor.execute(sql)
        return cursor.fetchone()[0]

    def total_balance(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        """
        Returns the total confirmed balance from the Wallet.
        """
        if not settings.BITCOIN_UNCONFIRMED_TRANSFERS:
            # if settings.BITCOIN_TRANSACTION_SIGNALING:
            #     if minconf == settings.BITCOIN_MINIMUM_CONFIRMATIONS:
            #         return self.total_balance_sql()
            #     elif mincof == 0:
            #         self.total_balance_sql(False)
            return self.total_received(minconf) - self.total_sent()
        else:
            return self.balance(minconf)[1]

    def total_balance_unconfirmed(self):
        if not settings.BITCOIN_UNCONFIRMED_TRANSFERS:
            return self.total_received(0) - self.total_sent()
        else:
            x = self.balance()
            return x[0] + x[1]

    def unconfirmed_balance(self):
        if not settings.BITCOIN_UNCONFIRMED_TRANSFERS:
            return self.total_received(0) - self.total_sent()
        else:
            return self.balance()[0]

    def total_received(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        """Returns the raw ammount ever received by this wallet."""
        if settings.BITCOIN_TRANSACTION_SIGNALING:
            if minconf == settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                s = self.addresses.aggregate(models.Sum("least_received_confirmed"))['least_received_confirmed__sum'] or Decimal(0)
            elif minconf == 0:
                s = self.addresses.aggregate(models.Sum("least_received"))['least_received__sum'] or Decimal(0)
            else:
                s = sum([a.received(minconf=minconf) for a in self.addresses.all()])
        else:
            s = sum([a.received(minconf=minconf) for a in self.addresses.all()])
        rt = self.received_transactions.aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)
        return (s + rt)

    def total_sent(self):
        """Returns the raw ammount ever sent by this wallet."""
        return self.sent_transactions.aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)

    def has_history(self):
        """Returns True if this wallet was any transacion history."""
        if self.received_transactions.all().count():
            return True
        if self.sent_transactions.all().count():
            return True
        if filter(lambda x: x.received(), self.addresses.all()):
            return True
        return False

    def merge_wallet(self, other_wallet):
        if self.id>0 and other_wallet.id>0:
            from django.db import connection, transaction
            cursor = connection.cursor()
            cursor.execute("UPDATE django_bitcoin_bitcoinaddress SET wallet_id="+str(other_wallet.id)+\
                " WHERE wallet_id="+str(self.id))
            cursor.execute("UPDATE django_bitcoin_wallettransaction SET from_wallet_id="+str(other_wallet.id)+\
                " WHERE from_wallet_id="+str(self.id))
            cursor.execute("UPDATE django_bitcoin_wallettransaction SET to_wallet_id="+str(other_wallet.id)+\
                " WHERE to_wallet_id="+str(self.id))
            cursor.execute("DELETE FROM django_bitcoin_wallettransaction WHERE to_wallet_id=from_wallet_id")
            transaction.commit_unless_managed()

    # def save(self, **kwargs):
    #     self.updated_at = datetime.datetime.now()
    #     super(Wallet, self).save(**kwargs)

### Maybe in the future

# class FiatWalletTransaction(models.Model):
#     """Transaction for storing fiat currencies"""
#     pass

# class FiatWallet(models.Model):
#     """Wallet for storing fiat currencies"""
#     pass

# class BitcoinEscrow(models.Model):
#     """Bitcoin escrow payment"""

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     seller = models.ForeignKey(User)

#     bitcoin_payment = models.ForeignKey(Payment)

#     confirm_hash = models.CharField(max_length=50, blank=True)

#     buyer_address = models.TextField()
#     buyer_phone = models.CharField(max_length=20, blank=True)
#     buyer_email = models.EmailField(max_length=75)

#     def save(self, **kwargs):
#         super(BitcoinEscrow, self).save(**kwargs)
#         if not self.confirm_hash:
#             self.confirm_hash=generateuniquehash(
#                 length=32,
#                 extradata=str(self.id))
#             super(BitcoinEscrow, self).save(**kwargs)

#     @models.permalink
#     def get_absolute_url(self):
#         return ('view_or_url_name',)


def refill_payment_queue():
    c=BitcoinAddress.objects.filter(active=False, wallet=None).count()
    # print "count", c
    if settings.BITCOIN_ADDRESS_BUFFER_SIZE>c:
        for i in range(0,settings.BITCOIN_ADDRESS_BUFFER_SIZE-c):
            BitcoinAddress.objects.create(address = bitcoind.create_address(), active=False)


def update_payments():
    if not cache.get('last_full_check'):
        cache.set('bitcoinprice', cache.get('bitcoinprice_old'))
    bps=BitcoinPayment.objects.filter(active=True)
    for bp in bps:
        bp.amount_paid=Decimal(bitcoin_getbalance(bp.address))
        bp.save()
        print bp.amount
        print bp.amount_paid

@transaction.commit_on_success
def new_bitcoin_payment(amount):
    bp=BitcoinPayment.objects.filter(active=False)
    if len(bp)<1:
        refill_payment_queue()
        bp=BitcoinPayment.objects.filter(active=False)
    bp=bp[0]
    bp.active=True
    bp.amount=amount
    bp.save()
    return bp

def getNewBitcoinPayment(amount):
    warnings.warn("Use new_bitcoin_payment(amount) instead",
                  DeprecationWarning)
    return new_bitcoin_payment(amount)

@transaction.commit_on_success
def new_bitcoin_payment_eur(amount):
    print bitcoinprice_eur()
    return new_bitcoin_payment(Decimal(amount)/Decimal(bitcoinprice_eur()['24h']))

def getNewBitcoinPayment_eur(amount):
    return new_bitcoin_payment_eur(amount)

# initialize the conversion module

from django_bitcoin import currency

from django.core import urlresolvers
from django.utils import importlib

for dottedpath in settings.BITCOIN_CURRENCIES:
    mod, func = urlresolvers.get_mod_func(dottedpath)
    klass = getattr(importlib.import_module(mod), func)
    currency.exchange.register_currency(klass())

# Historical prie storage

class HistoricalPrice(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=16, decimal_places=2)
    params = models.CharField(max_length=50)
    currency = models.CharField(max_length=10)

    class Meta:
        verbose_name = _('HistoricalPrice')
        verbose_name_plural = _('HistoricalPrices')

    def __unicode__(self):
        return str(self.created_at) + " - " + str(self.price) + " - " + str(self.params)

def set_historical_price(curr="EUR"):
    markets = currency.markets_chart()
    # print markets
    markets_currency = sorted(filter(lambda m: m['currency']==curr and m['volume']>1, markets.values()), key=lambda m: -m['volume'])[:3]
    # print markets_currency
    price = sum([m['close'] for m in markets_currency]) / len(markets_currency)
    hp = HistoricalPrice.objects.create(price=Decimal(str(price)), params=",".join([m['symbol'] for m in markets_currency]), currency=curr)
    return hp.price

def get_historical_price(curr="EUR", dt=None):
    query = HistoricalPrice.objects.filter(currency=curr)
    if dt:
        try:
            query = HistoricalPrice.objects.filter(created_at__lte=dt).order_by("-created_at")[0].price
        except IndexError:
            return None
    try:
        return HistoricalPrice.objects.filter(currency=curr,
            created_at__gte=datetime.datetime.now() - datetime.timedelta(hours=settings.HISTORICALPRICES_FETCH_TIMESPAN_MINUTES)).\
            order_by("-created_at")[0].price
    except IndexError:
        return set_historical_price()




# EOF
