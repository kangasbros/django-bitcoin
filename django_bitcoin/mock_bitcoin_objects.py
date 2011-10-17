# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

import decimal

import mock

from django_bitcoin import utils

## bitcoin mock objects

## Patch your test cases which access bitcoin with these decorators
## eg:
#@mock.patch('django_bitcoin.utils.bitcoind', new=mock_bitcoin_objects.mock_bitcoind)
#@mock.patch('django_bitcoin.models.bitcoind', new=mock_bitcoin_objects.mock_bitcoind)
#def test_wallet_received():
#    ...

## FIRST
mock_bitcoind = mock.Mock(wraps=utils.bitcoind, spec=utils.bitcoind)

mock_received_123 = mock.Mock()
mock_received_123.return_value = decimal.Decimal(123)

mock_bitcoind.total_received = mock.mocksignature(utils.bitcoind.total_received, mock=mock_received_123)

mock_bitcoind.send = mock.mocksignature(utils.bitcoind.send)

mock_bitcoind_address = mock.Mock()
mock_bitcoind_address.return_value = '15EJtRsZAwwxtC4AiUS1ZsypGzk8WDLRFn'

mock_bitcoind.create_address = mock.mocksignature(utils.bitcoind.create_address, mock=mock_bitcoind_address)

## SECOND
mock_bitcoind_other = mock.Mock(wraps=utils.bitcoind, spec=utils.bitcoind)

mock_received_65535 = mock.Mock()
mock_received_65535.return_value = decimal.Decimal(65535)

mock_bitcoind_other.total_received = mock.mocksignature(utils.bitcoind.total_received, mock=mock_received_65535)

mock_bitcoind_other.send = mock.mocksignature(utils.bitcoind.send)

mock_bitcoind_other_address = mock.Mock()
mock_bitcoind_other_address.return_value = '15EJtRsZAwwxtC4AiUS1ZsypGzk8WDLRFn'

mock_bitcoind_other.create_address = mock.mocksignature(utils.bitcoind.create_address, mock=mock_bitcoind_other_address)

# EOF

