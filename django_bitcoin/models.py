from __future__ import with_statement
from django.db import models
import random
import hashlib
import base64
from decimal import *
from django.contrib.sites.models import Site
from django.conf import settings
import datetime
#from django

from django.contrib.auth.models import User

from django_bitcoin.utils import *

PAYMENT_VALID_HOURS = getattr(settings, "BITCOIND_PAYMENT_VALID_HOURS", 128)

REUSE_ADDRESSES = getattr(settings, "BITCOIND_REUSE_ADDRESSES", True)

ESCROW_PAYMENT_TIME_HOURS = getattr(settings, "BITCOIND_ESCROW_PAYMENT_TIME_HOURS", 4)
ESCROW_RELEASE_TIME_DAYS = getattr(settings, "BITCOIND_ESCROW_RELEASE_TIME_DAYS", 14)


currencies=((1, "USD"), (2, "EUR"), (3, "BTC"))
confirmation_choices=((0, "0, (quick, recommended)"), (1, "1, (safer, slower for the buyer)"), 
        (5, "5, (for the paranoid, not recommended)"))


class BitcoinTransaction(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal("0.0"))
    address = models.CharField(max_length=50)

class BitcoinPayment(models.Model):
    """docstring"""
    description = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal("0.0"))
    amount_paid = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal("0.0"))
    active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    paid_at = models.DateTimeField(null=True, default=None)

    withdrawn_total = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal("0.0"))

    transactions = models.ManyToManyField(BitcoinTransaction)
    
    def calculate_amount(self, proportion):
        return quantitize_bitcoin(Decimal((proportion/Decimal("100.0"))*self.amount))

    def add_transaction(self, amount, address):
        self.withdrawn_total+=am
        bctrans=BitcoinTransaction()
        bctrans.amount=am
        bctrans.address=address
        bctrans.save()
        self.transactions.add(bctrans)
        self.save()
    
    def withdraw_proportion(self, address, proportion):
        if proportion<=Decimal("0") or proportion>Decimal("100"):
            raise Exception("Illegal proportion.")
        if self.amount-self.withdrawn_total>am:
            raise Exception("Trying to withdraw too much.")
        am=self.calculate_amount(proportion)
        self.add_transaction(am, address)
        bitcoin_sendtoaddress(address, amount)
        return True
    
    @classmethod
    def withdraw_proportion_all(address, bitcoin_payments_proportions):
        """hash BitcoinPayment -> Proportion"""
        final_amount=Decimal("0.0")
        for bp, proportion in bitcoin_payments_proportions:
            am=bp.calculate_amount(proportion)
            final_amount+=am
            bp.add_transaction(am, address)
        bitcoin_sendtoaddress(address, final_amount)
        return True
        

    def withdraw_amounts(self, addresses_shares):
        """hash address -> percentage (string -> Decimal)"""
        if self.amount_paid<self.amount:
            raise Exception("Not paid.")
        if withdrawn_at:
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
    def calculate_amounts(bitcoinpayments, addresses_shares):
        amounts_all=[Decimal("0.0") for i in range(0, len(addresses_shares.keys()))]
        for i in range(0, len(bitcoinpayments)):
            bp=bitcoinpayments[i]
            am=bp.withdraw_amounts(addresses_shares)
            amounts_all=[(am[i]+amounts_all[i]) for i in range(0, len(addresses_shares.keys()))]
        return amounts_all

    @classmethod
    def withdraw_all(bitcoinpayments, addresses_shares):
        #if len(bitcoinpayments)!=len(addresses_shares):
        #    raise Exception("")
        amounts_all=BitcoinPayment.calculate_amounts(bitcoinpayments, addresses_shares)
        for i in range(0, len(bitcoinpayments)):
            bp=bitcoinpayments[i]
            am=bp.withdraw_amounts(addresses_shares)
            bp.withdraw_addresses=",".join(addresses_shares.keys())
            bp.withdraw_proportions=",".join([str(x) for x in addresses_shares.values()])
            bp.withdraw_amounts=",".join([str(x) for x in am])
            bp.withdrawn_at=datetime.datetime.now()
            bp.withdrawn_total=sum(am)
            bp.save()
        for i in range(0, len(addresses_shares.keys())):
            bitcoin_sendtoaddress(addresses_shares.keys()[i], amounts_all[i])
        return True

    def is_paid(self, minconf=1):
        if self.paid_at:
            return True
        self.update_payment(minconf=minconf)
        return self.amount_paid>=self.amount

    def getbalance(self, minconf=1):
        return Decimal(bitcoin_getbalance(self.address, minconf=minconf))

    def update_payment(self, minconf=1):
        new_amount=Decimal(bitcoin_getbalance(self.address, minconf=minconf))
        if new_amount>=self.amount_paid:
            self.amount_paid=new_amount
            self.paid_at=datetime.datetime.now()
            self.save()
        #elif (datetime.datetime.now()-self.updated_at)>datetime.timedelta(hours=PAYMENT_VALID_HOURS):
        #    self.deactivate()

    def deactivate(self):
        return False
        if self.amount_paid>Decimal(0):
            return False
        self.active=False
        self.description=""
        self.save()
        return True
    
    #def save(self, force_insert=False, force_update=False):
    #

    @models.permalink
    def get_absolute_url(self):
        return ('view_or_url_name')

class BitcoinEscrow(models.Model):
    """Bitcoin escrow payment"""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    seller = models.ForeignKey(User)
    
    bitcoin_payment = models.ForeignKey(BitcoinPayment)

    confirm_hash = models.CharField(max_length=50, blank=True)
    
    buyer_address = models.TextField()
    buyer_phone = models.CharField(max_length=20, blank=True)
    buyer_email = models.EmailField(max_length=75)
    
    def save(self, force_insert=False, force_update=False):
        super(BitcoinEscrow, self).save(force_insert=force_insert, force_update=force_update)
        if not self.confirm_hash:
            self.confirm_hash=generateuniquehash(length=32, extradata=str(self.id))
            super(BitcoinEscrow, self).save(force_insert=force_insert, force_update=force_update)
    
    @models.permalink
    def get_absolute_url(self):
        return ('view_or_url_name' )

