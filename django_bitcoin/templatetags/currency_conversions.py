from django import template
from django_bitcoin import currency

from decimal import Decimal

from django.core.urlresolvers import reverse,  NoReverseMatch

register = template.Library()

# currency conversion functions

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

@register.inclusion_tag('wallet_history.html')
def wallet_history(wallet):
    return {'wallet': wallet}

@register.filter
def show_addr(address, arg):
    '''
    Display a bitcoin address with plus the link to its blockexplorer page.
    '''
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
    qr="bitcoin:"+address+("", "?amount="+str(amount))[amount>0]
    address_qrcode = reverse('qrcode', args=(address,))
    return {'address': address, 
            'address_qrcode': address_qrcode,
            'amount': amount, 
            'description': description, 
            'display_currency': display_currency,
            'currency_amount': currency_amount,
            }
