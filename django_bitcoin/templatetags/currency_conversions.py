from django import template
from django_bitcoin import currency

import json
from decimal import Decimal

import urllib

from django.core.urlresolvers import reverse,  NoReverseMatch

register = template.Library()

# currency conversion functions

@register.filter
def bitcoinformat(value):
    # print "bitcoinformat", value
    if value == None:
        return None
    if not (isinstance(value, float) or isinstance(value, Decimal)):
        return str(value).rstrip('0').rstrip('.')
    return ("%.8f" % value).rstrip('0').rstrip('.')

@register.filter
def currencyformat(value):
    if value == None:
        return None
    if not (isinstance(value, float) or isinstance(value, Decimal)):
        return str(value).rstrip('0').rstrip('.')
    return ("%.2f" % value)

@register.filter
def btc2usd(value):
    return (Decimal(value)*currency.exchange.get_rate('USD')).quantize(Decimal("0.01"))

@register.filter
def usd2btc(value):
    return (Decimal(value)/currency.exchange.get_rate('USD')).quantize(Decimal("0.00000001"))

@register.filter
def btc2eur(value):
    return (Decimal(value)*currency.exchange.get_rate('EUR')).quantize(Decimal("0.01"))

@register.filter
def eur2btc(value):
    return (Decimal(value)/currency.exchange.get_rate('EUR')).quantize(Decimal("0.00000001"))

@register.filter
def btc2currency(value, other_currency="USD", rate_period="24h"):
    if other_currency=="BTC":
        return bitcoinformat(value)
    return currencyformat(currency.btc2currency(value, other_currency, rate_period))

@register.filter
def currency2btc(value, other_currency="USD", rate_period="24h"):
    if other_currency=="BTC":
        return currencyformat(value)
    return bitcoinformat(currency.currency2btc(value, other_currency, rate_period))

@register.simple_tag
def exchangerates_json():
    return json.dumps(currency.get_rate_table())


@register.inclusion_tag('wallet_history.html')
def wallet_history(wallet):
    return {'wallet': wallet}


@register.filter
def show_addr(address, arg):
    '''
    Display a bitcoin address with plus the link to its blockexplorer page.
    '''
    # note: i disapprove including somewhat unnecessary depencies such as this, especially since blockexplorer is  unreliable service
    link ="<a href='http://blockexplorer.com/%s/'>%s</a>"
    if arg == 'long':
        return link % (address, address)
    else:
        return link % (address, address[:8])


@register.inclusion_tag('wallet_tagline.html')
def wallet_tagline(wallet):
    return {'wallet': wallet, 'balance_usd': btc2usd(wallet.total_balance())}


@register.inclusion_tag('bitcoin_payment_qr.html')
def bitcoin_payment_qr(address, amount=Decimal("0"), description='', display_currency=''):
    currency_amount=Decimal(0)
    if display_currency:
        currency_amount=(Decimal(amount)*currency.exchange.get_rate(display_currency)).quantize(Decimal("0.01"))
    try:
        image_url = reverse('qrcode', args=('dummy',))
    except NoReverseMatch,e:
        raise ImproperlyConfigured('Make sure you\'ve included django_bitcoin.urls')
    qr = "bitcoin:"+address+("", "?amount="+str(amount))[amount>0]
    qr = urllib.quote(qr)
    address_qrcode = reverse('qrcode', args=(qr,))
    return {'address': address, 
            'address_qrcode': address_qrcode,
            'amount': amount, 
            'description': description, 
            'display_currency': display_currency,
            'currency_amount': currency_amount,
            }
