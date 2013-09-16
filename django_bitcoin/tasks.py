from __future__ import with_statement

import datetime
import random
import hashlib
import base64
from decimal import Decimal

from django.db import models

from django_bitcoin.utils import bitcoind
from django_bitcoin import settings

from django.utils.translation import ugettext as _
from django_bitcoin.models import DepositTransaction, BitcoinAddress

import django.dispatch

import jsonrpc

from BCAddressField import is_valid_btc_address

from django.db import transaction as db_transaction
from celery import task
from distributedlock import distributedlock, MemcachedLock, LockNotAcquiredError
from django.core.cache import cache

@task()
def query_transactions():
    if not cache.get("query_transactions_ongoing"):
        cache.set("query_transactions_ongoing", 1)
        blockcount = bitcoind.bitcoind_api.getblockcount()
        max_query_block = blockcount - settings.BITCOIN_MINIMUM_CONFIRMATIONS - 1
        if cache.get("queried_block_index"):
            query_block = min(int(cache.get("queried_block_index")), max_query_block)
        else:
            query_block = blockcount - 100
        blockhash = bitcoind.bitcoind_api.getblockhash(query_block)
        print query_block, blockhash
        transactions = bitcoind.bitcoind_api.listsinceblock(blockhash)
        transactions = [tx for tx in transactions["transactions"] if tx["category"]=="receive"]
        print transactions
        for tx in transactions:
            ba = BitcoinAddress.objects.filter(address=tx[u'address'])
            if ba.count() > 1:
                raise Exception(u"Too many addresses!")
            if ba.count() == 0:
                continue
            dps = DepositTransaction.objects.filter(txid=tx[u'txid'], amount=tx['amount'])
            if dps.count() > 1:
                raise Exception(u"Too many deposittransactions for the same ID!")
            elif dps.count() == 0:
                deposit_tx = DepositTransaction.objects.create(wallet=ba.wallet,
                    address=ba,
                    amount=tx['amount'],
                    confirmations=int(tx['confirmations']))
                if deposit_tx.confirmations >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                    ba.query_bitcoin_deposit(deposit_tx)
                else:
                    ba.query_unconfirmed_deposits(deposit_tx)
            elif dps.count() == 1 and dps[0].confirmations < int(tx['confirmations']):
                deposit_tx = dps[0]
                if deposit_tx.confirmations < settings.BITCOIN_MINIMUM_CONFIRMATIONS and\
                    int(tx['confirmations']) >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                    ba.query_bitcoind_deposit(deposit_tx)
                DepositTransaction.objects.filter(id=deposit_tx.id).update(confirmations=int(tx['confirmations']))

        cache.set("queried_block_index", max_query_block)
        cache.delete("query_transactions_ongoing")