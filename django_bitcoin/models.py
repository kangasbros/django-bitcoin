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

currencies=(
    (1, "USD"), 
    (2, "EUR"), 
    (3, "BTC")
)

confirmation_choices=(
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
    label = models.CharField(max_length=50, blank=True, null=True, default=None)

    class Meta:
        verbose_name_plural = 'Bitcoin addresses'

    def received(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        r=bitcoind.total_received(self.address, minconf=minconf)
        if r>self.least_received:
            self.least_received=r
            self.save()
        return r

    def __unicode__(self):
        if self.label:
            return u'%s (%s)' % (self.label, self.address)
        return self.address

@transaction.commit_on_success
def new_bitcoin_address():
    bp=BitcoinAddress.objects.filter(active=False)
    if len(bp)<1:
        refill_payment_queue()
        bp=BitcoinAddress.objects.filter(active=False)
    bp=bp[0]
    bp.active=True
    bp.save()
    return bp

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

class Wallet(models.Model):
    created_at = models.DateTimeField(default=datetime.datetime.now)
    updated_at = models.DateTimeField()

    label = models.CharField(max_length=50, blank=True)
    addresses = models.ManyToManyField(BitcoinAddress)
    transactions_with = models.ManyToManyField(
        'self',
        through=WalletTransaction,
        symmetrical=False)

    def __unicode__(self):
        return u"%s: %s" % (self.label,
                            self.created_at.strftime('%Y-%m-%d %H:%M'))

    def save(self):
        '''Assings a wallet label if the wallet doesn't have one.'''
        super(Wallet, self).save(*args, **kwargs)
        if not self.label:
            self.label = 'Wallet #%d' % self.id
            super(Wallet, self).save(*args, **kwargs) 

    def receiving_address(self, fresh_addr=True):
        usable_addresses = self.addresses.filter(active=True).order_by("id")
        if fresh_addr:
            usable_addresses = usable_addresses.filter(least_received=Decimal(0))
        if usable_addresses.count():
            return usable_addresses[0].address
        addr=new_bitcoin_address()
        self.addresses.add(addr)
        return addr.address

    def static_receiving_address(self):
        '''
        Returns a static receiving address for this Wallet object.
        '''
        return self.receiving_address(fresh_addr=False)

    def send_to_wallet(self, otherWallet, amount, description=''):
        if amount>self.total_balance():
            raise Exception(_("Trying to send too much"))
        if self==otherWallet:
            raise Exception(_("Can't send to self-wallet"))
        if not otherWallet.id or not self.id:
            raise Exception(_("Some of the wallets not saved"))
        return WalletTransaction.objects.create(
            amount=amount,
            from_wallet=self,
            to_wallet=otherWallet,
            description=description)
    
    def send_to_address(self, address, amount, description=''):
        if Decimal(amount)<Decimal(0):
            raise Exception(_("Trying to send too much"))
        if Decimal(amount)>self.total_balance():
            raise Exception(_("Trying to send too much"))
        bwt = WalletTransaction.objects.create(
            amount=amount,
            from_wallet=self,
            to_bitcoinaddress=address,
            description=description)
        try:
            result=bitcoind.send(address, amount)
        except JSONRPCException:
            bwt.delete()
            raise
        # check if a transaction fee exists, and deduct it from the wallet
        # TODO: because fee can't be known beforehand, can result in negative wallet balance.
        # currently isn't much of a issue, but might be in the future, depending of the application
        transaction=bitcoind.gettransaction(result)
        fee_transaction=None
        if Decimal(transaction['fee'])<Decimal(0):
            fee_transaction = WalletTransaction.objects.create(
                amount=Decimal(transaction['fee'])*Decimal(-1),
                from_wallet=self)
        return (bwt, fee_transaction)

    def total_received(self):
        """docstring for getreceived"""
        s=sum([a.received() for a in self.addresses.all()])
        rt=self.received_transactions.aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)
        return (s+rt)

    def total_sent(self):
        return self.sent_transactions.aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)

    def total_balance(self):
        return self.total_received() - self.total_sent()

    def total_received_unconfirmed(self):
        """docstring for getreceived"""
        s=sum([a.received(minconf=0) for a in self.addresses.all()])
        rt=self.received_transactions.aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)
        return (s+rt)

    def total_balance_unconfirmed(self):
        return self.total_received_unconfirmed() - self.total_sent()

    def save(self, **kwargs):
        self.updated_at = datetime.datetime.now()
        super(Wallet, self).save(**kwargs)

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
    c=Payment.objects.filter(active=False).count()
    if settings.BITCOIN_PAYMENT_BUFFER_SIZE>c:
        for i in range(0,settings.BITCOIN_PAYMENT_BUFFER_SIZE-c):
            bp=Payment()
            bp.address=bitcoind.create_address()
            bp.save()
    c=BitcoinAddress.objects.filter(active=False).count()
    if settings.BITCOIN_ADDRESS_BUFFER_SIZE>c:
        for i in range(0,settings.BITCOIN_ADDRESS_BUFFER_SIZE-c):
            ba=BitcoinAddress()
            ba.address=bitcoind.create_address()
            ba.save()

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

# EOF


