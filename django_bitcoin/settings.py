from django.conf import settings
from decimal import Decimal

MAIN_ACCOUNT = getattr(
    settings,
    "BITCOIND_MAIN_ACCOUNT",
    "somerandomstring14aqqwd")
BITCOIND_CONNECTION_STRING = getattr(
    settings,
    "BITCOIND_CONNECTION_STRING",
    "")
BITCOIN_PAYMENT_BUFFER_SIZE = getattr(
    settings,
    "BITCOIN_PAYMENT_BUFFER_SIZE",
    5)
BITCOIN_ADDRESS_BUFFER_SIZE = getattr(
    settings,
    "BITCOIN_ADDRESS_BUFFER_SIZE",
    5)
PAYMENT_VALID_HOURS = getattr(
    settings,
    "BITCOIND_PAYMENT_VALID_HOURS",
    128)
REUSE_ADDRESSES = getattr(
    settings,
    "BITCOIND_REUSE_ADDRESSES",
    True)
ESCROW_PAYMENT_TIME_HOURS = getattr(
    settings,
    "BITCOIND_ESCROW_PAYMENT_TIME_HOURS",
    4)
ESCROW_RELEASE_TIME_DAYS = getattr(
    settings,
    "BITCOIND_ESCROW_RELEASE_TIME_DAYS",
    14)
BITCOIN_MINIMUM_CONFIRMATIONS = getattr(
    settings,
    "BITCOIN_MINIMUM_CONFIRMATIONS",
    3)
BITCOIN_TRANSACTION_CACHING = getattr(
    settings,
    "BITCOIN_TRANSACTION_CACHING",
    False)
BITCOIN_TRANSACTION_SIGNALING = getattr(
    settings,
    "BITCOIN_TRANSACTION_SIGNALING",
    False)
BITCOIN_DISABLE_OUTGOING = getattr(
    settings,
    "BITCOIN_DISABLE_OUTGOING",
    False)
BITCOIN_CURRENCIES = getattr(
    settings,
    "BITCOIN_CURRENCIES",
    [
        "django_bitcoin.currency.BTCCurrency",
        "django_bitcoin.currency.EURCurrency",
        "django_bitcoin.currency.USDCurrency"
        ])
# Allow transfer of unconfirmed ammounts between wallets
BITCOIN_UNCONFIRMED_TRANSFERS = getattr(
    settings,
    "BITCOIN_UNCONFIRMED_TRANSFERS",
    False)

BITCOIN_PRIVKEY_FEE = getattr(
    settings,
    "BITCOIN_PRIVKEY_FEE",
    Decimal("0.0005"))

BITCOIN_OPENEXCHANGERATES_URL = getattr(
    settings,
    "BITCOIN_OPENEXCHANGERATES_URL",
    "http://openexchangerates.org/api/latest.json")

HISTORICALPRICES_FETCH_TIMESPAN_MINUTES = getattr(
    settings,
    "HISTORICALPRICES_FETCH_TIMESPAN_HOURS",
    60)
