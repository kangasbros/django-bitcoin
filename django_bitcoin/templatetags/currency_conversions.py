from django import template
from django_bitcoin import currency

from decimal import Decimal

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

@register.inclusion_tag('wallet_tagline.html')
def wallet_tagline(wallet):
    return {'wallet': wallet, 'balance_usd': btc2usd(wallet.total_balance())}
