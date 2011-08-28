from django_bitcoin.models import bitcoinprice_eur, bitcoinprice_usd

def bitcoinprice(request):
    return {'bitcoinprice_eur': bitcoinprice_eur(),
        'bitcoinprice_usd': bitcoinprice_usd(),
        }
