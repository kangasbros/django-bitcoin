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

    def get_rate(self, currency, to="BTC"):
        """Rate is inferred from a dummy exchange"""
        start = Money("1.0", currency)
        end = self(start_amount, to)
        return end.amount

    def __call__(self, money, target="BTC"):
        """Gets the current equivalent amount of the given Money in
        the target currency
        """
        if not hasattr(unit, "identifier"):
            raise ConversionError(
                "Use annotated currency (e.g. Money) as "
                "the unit argument")

        if unit.identifier not in self.currencies:
            raise ConversionError(
                "Unknown source currency %(identifier)s. "
                "Available currencies: %(currency_list)s" % {
                    "identifier": unit.identifier, 
                    "currency_list": u", ".join(self.currencies.keys())})

        if to not in self.currencies:
            raise ConversionError(
                "Unknown target currency %(identifier)s. "
                "Available currencies: %(currency_list)s" % {
                    "identifier": to, 
                    "currency_list": u", ".join(self.currencies.keys())})

        btc = self.currencies[unit.identifier].to_btc(unit.amount)
        return Money(to, self.currencies[to].from_btc(unit.amount))

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
        except:
            print "Unexpected error:", sys.exc_info()[0]
            
        if not cache.get(self.cache_key):
            if not cache.get(self.cache_key_old):
                raise TemporaryConversionError(
                    "Reliable exchange rate is not available for %s" % self.identifier)
            cache.set(self.cache_key, cache.get(self.cache_key_old), 60*60)

        cache.set(self.cache_key_old, cache.get(self.cache_key), 60*60*24*7)

    def get_factor(self):
        cached = cache.get(self.cache_key)
        if cached:
            factor = cached[self.period]
        else:
            self.populate_cache()
            factor = cache.get(self.cache_key)[self.period]
        return factor

    def to_btc(self, amount):
        return amount / self.get_factor()

    def from_btc(self, amount):
        return amount * self.get_factor()

class EURCurrency(BitcoinChartsCurrency):
    identifier = "EUR"

class USDCurrency(BitcoinChartsCurrency):
    identifier = "USD"

exchange = Exchange()
