from django.conf import settings

MAIN_ACCOUNT = getattr(
    settings, 
    "BITCOIND_MAIN_ACCOUNT", 
    "somerandomstring14aqqwd")
CONNECTION_STRING = getattr(
    settings, 
    "BITCOIND_CONNECTION_STRING", 
    "")
PAYMENT_BUFFER_SIZE = getattr(
    settings, 
    "DBITCOIN_PAYMENT_BUFFER_SIZE",
    5)
