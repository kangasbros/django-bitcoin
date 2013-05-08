# -*- coding: utf-8 -*-
"""Usage:

>>> currency.exchange(
...     currency.Money("10.0", "BTC"),
...     "BTC")
Money("10.0", "BTC")

Default valid currencies are BTC, EUR and USD. Change exchange rate
sources and add new ones by the setting BITCOIN_CURRENCIES, which
should be a list of dotted paths to Currency subclasses (or other
classes) which implement both to_btc(decimal amount) -> decimal and
from_btc(decimal amount) -> decimal.

You can subclass or instance the `Exchange` class to e.g. maintain
multiple different exchange rates from different sources in your own
code. Default `exchange` uses Bitcoincharts.
"""

import decimal

from django.core.cache import cache

import json
import jsonrpc
import sys
import urllib
import urllib2
import random
import hashlib
import base64
from decimal import Decimal
import decimal
import warnings


from django_bitcoin import settings

class ConversionError(Exception):
    pass

class TemporaryConversionError(ConversionError):
    pass

class Exchange(object):
    def __init__(self):
        self.currencies = {}

    def register_currency(self, klass):
        self.currencies[klass.identifier] = klass

    def get_rate(self, currency, target="BTC"):
        """Rate is inferred from a dummy exchange"""
        start = Money(currency, "1.0")
        end = self(start, target)
        return end.amount

    def __call__(self, money, target="BTC"):
        """Gets the current equivalent amount of the given Money in
        the target currency
        """
        if not hasattr(money, "identifier"):
            raise ConversionError(
                "Use annotated currency (e.g. Money) as "
                "the unit argument")

        if money.identifier not in self.currencies:
            raise ConversionError(
                "Unknown source currency %(identifier)s. "
                "Available currencies: %(currency_list)s" % {
                    "identifier": money.identifier,
                    "currency_list": u", ".join(self.currencies.keys())})

        if target not in self.currencies:
            raise ConversionError(
                "Unknown target currency %(identifier)s. "
                "Available currencies: %(currency_list)s" % {
                    "identifier": target,
                    "currency_list": u", ".join(self.currencies.keys())})

        btc = self.currencies[money.identifier].to_btc(money.amount)
        return Money(target, self.currencies[target].from_btc(btc))

class Money(object):
    def __init__(self, identifier, amount, *args, **kwargs):
        self.identifier = identifier
        self.amount = decimal.Decimal(amount)

    def __add__(self, other):
        if (not hasattr(other, "identifier")
            or other.identifier != self.identifier):
            raise ConversionError("Cannot add different currencies "
                                  "or non-currencies together")
        return Money(self.identifier, self.amount + other.amount)

    def __sub__(self, other):
        if (not hasattr(other, "identifier")
            or other.identifier != self.identifier):
            raise ConversionError("Cannot subtract different currencies "
                                  "or non-currencies together")
        return Money(self.identifier, self.amount - other.amount)

    def __mul__(self, other):
        if hasattr(other, "identifier"):
            raise ConversionError("Cannot multiply currency "
                                  "with any currency")
        return Money(self.identifier, self.amount * other)

    def __div__(self, other):
        if hasattr(other, "identifier"):
            raise ConversionError("Cannot divide currency "
                                  "with any currency")
        return Money(self.identifier, self.amount / other)

    def __unicode__(self):
        return u"%s %s" % (self.identifier, self.amount)

class Currency(object):
    def to_btc(self, amount):
        raise NotImplementedError
    def from_btc(self, amount):
        raise NotImplementedError

class BTCCurrency(Currency):
    identifier = "BTC"

    def to_btc(self, amount):
        return amount

    def from_btc(self, amount):
        return amount

class BitcoinChartsCurrency(Currency):
    period = "24h"

    def __init__(self):
        self.cache_key = "%s_in_btc" % self.identifier
        self.cache_key_old = "%s_was_in_btc" % self.identifier

    def populate_cache(self):
        try:
            f = urllib2.urlopen(
                u"http://bitcoincharts.com/t/weighted_prices.json")
            result=f.read()
            j=json.loads(result)
            base_price = j[self.identifier]
            cache.set(self.cache_key, base_price, 60*60)
            #print result
        except:
            print "Unexpected error:", sys.exc_info()[0]

        if not cache.get(self.cache_key):
            if not cache.get(self.cache_key_old):
                raise TemporaryConversionError(
                    "Cache not enabled, reliable exchange rate is not available for %s" % self.identifier)
            cache.set(self.cache_key, cache.get(self.cache_key_old), 60*60)

        cache.set(self.cache_key_old, cache.get(self.cache_key), 60*60*24*7)

    def get_factor(self):
        cached = cache.get(self.cache_key)
        if cached:
            factor = cached[self.period]
        else:
            self.populate_cache()
            factor = cache.get(self.cache_key)[self.period]
        return decimal.Decimal(factor)

    def to_btc(self, amount):
        return amount * self.get_factor()

    def from_btc(self, amount):
        return amount / self.get_factor()

class EURCurrency(BitcoinChartsCurrency):
    identifier = "EUR"

class USDCurrency(BitcoinChartsCurrency):
    identifier = "USD"

exchange = Exchange()

# simple utility functions for conversions

CURRENCY_CHOICES = (
    ('BTC', 'BTC'),
    ('USD', 'USD'),
    ('EUR', 'EUR'),
    ('AUD', 'AUD'),
    ('BRL', 'BRL'),
    ('CAD', 'CAD'),
    ('CHF', 'CHF'),
    ('CNY', 'CNY'),
    ('GBP', 'GBP'),
    ('NZD', 'NZD'),
    ('PLN', 'PLN'),
    ('RUB', 'RUB'),
    ('SEK', 'SEK'),
    ('SLL', 'SLL'),
)

RATE_PERIOD_CHOICES=("24h", "7d", "30d",)

market_parameters=('high', 'low', 'bid', 'ask', 'close',)


def markets_chart():
    cache_key="bitcoincharts_markets"
    cache_key_old="bitcoincharts_markets_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                u"http://bitcoincharts.com/t/markets.json")
            result=f.read()
            j=json.loads(result)
            final_markets={}
            for market in j:
                b=True
                for mp in market_parameters:
                    if not market[mp]:
                        b=False
                        break
                if b:
                    # print market['symbol']
                    final_markets[market['symbol'].lower()]=market
            cache.set(cache_key, final_markets, 60*5)
            #print result
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise Exception(
                    "Cache not enabled, reliable market data is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*5)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)


def currency_exchange_rates():
    cache_key="currency_exchange_rates"
    cache_key_old="currency_exchange_rates_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                u"http://openexchangerates.org/latest.json")
            result=f.read()
            j=json.loads(result)
            cache.set(cache_key, j, 60*5)
            #print result
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise Exception(
                    "Cache not enabled, reliable market data is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*5)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)


MTGOX_CURRENCIES = ("USD", "EUR", "AUD", "CAD", "CHF", "CNY", "DKK",
    "GBP", "HKD", "JPY", "NZD", "PLN", "RUB", "SEK", "SGD", "THB")

def get_mtgox_rate_table():
    cache_key_old="bitcoincharts_all_old"
    old_table = cache.get(cache_key_old)
    if not old_table:
        old_table = {}
        for c in MTGOX_CURRENCIES:
            old_table[c] = {'24h': None, '7d': None, '30d': None}
    for c in MTGOX_CURRENCIES:
        try:
            f = urllib2.urlopen(
                u"https://mtgox.com/api/1/BTC"+c+"/ticker")
            result=f.read()
            j=json.loads(result)
            old_table[c]['24h'] = Decimal(j['vwap']['value'])
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err


def get_rate_table():
    cache_key="bitcoincharts_all"
    cache_key_old="bitcoincharts_all_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                u"http://bitcoincharts.com/t/weighted_prices.json")
            result=f.read()
            j=json.loads(result)
            cache.set(cache_key, j, 60*60)
            print result
        # except ValueError:

        except:
            print "Unexpected error:", sys.exc_info()[0]

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise TemporaryConversionError(
                    "Cache not enabled, reliable exchange rate is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*60)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)


def currency_exchange_rates():
    cache_key="currency_exchange_rates"
    cache_key_old="currency_exchange_rates_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                settings.BITCOIN_OPENEXCHANGERATES_URL)
            result=f.read()
            j=json.loads(result)
            cache.set(cache_key, j, 60*5)
            #print result
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise Exception(
                    "Cache not enabled, reliable market data is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*60*2)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)

def currency_list():
    return get_rate_table().keys()

def big_currency_list():
    return sorted(["BTC"] + currency_exchange_rates()["rates"].keys())

def get_currency_rate(currency="USD", rate_period="24h"):
    try:
        return Decimal(get_rate_table()[currency][rate_period])
    except KeyError:
        try:
            return Decimal(currency_exchange_rates()['rates'][currency])*Decimal(get_rate_table()['USD'][rate_period])
        except:
            return None

def btc2currency(amount, currency="USD", rate_period="24h"):
    if currency == "BTC":
        return amount
    rate=get_currency_rate(currency, rate_period)
    if rate==None:
        return None
    return (amount*rate).quantize(Decimal("0.01"))

def currency2btc(amount, currency="USD", rate_period="24h"):
    if currency == "BTC":
        return amount
    rate=get_currency_rate(currency, rate_period)
    if rate==None:
        return None
    return (amount/rate).quantize(Decimal("0.00000001"))


