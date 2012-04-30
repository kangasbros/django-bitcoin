# coding=utf-8
# vim: ai ts=4 sts=4 et sw=4

from django.db import models
from django import forms
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.utils.translation import get_language_from_request, ugettext_lazy as _
from djangoextras.forms import CurrencyField
from django_bitcoin.models import BitcoinEscrow

class BitcoinEscrowBuyForm(ModelForm):
    class Meta:
        model=BitcoinEscrow
        fields = ('buyer_address', 'buyer_phone', 'buyer_email')
        
