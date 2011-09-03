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

mock_bitcoind = mock.Mock(wraps=utils.bitcoind, spec=utils.bitcoind)

mock_received_123 = mock.Mock()
mock_received_123.return_value = decimal.Decimal(123)

mock_bitcoind.total_received = mock.mocksignature(utils.bitcoind.total_received, mock=mock_received_123)

mock_bitcoind.send = mock.mocksignature(utils.bitcoind.send)

mock_bitcoind.create_address = mock.Mock(return_value='15EJtRsZAwwxtC4AiUS1ZsypGzk8WDLRFn')

# EOF

