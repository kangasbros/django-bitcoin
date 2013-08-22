# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DepositTransaction.transaction'
        db.add_column('django_bitcoin_deposittransaction', 'transaction',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['django_bitcoin.WalletTransaction'], null=True),
                      keep_default=False)


        # Changing field 'WalletTransaction.from_wallet'
        db.alter_column('django_bitcoin_wallettransaction', 'from_wallet_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['django_bitcoin.Wallet']))
        # Adding field 'BitcoinAddress.migrated_to_transactions'
        db.add_column('django_bitcoin_bitcoinaddress', 'migrated_to_transactions',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        pass
        # Deleting field 'DepositTransaction.transaction'
        # db.delete_column('django_bitcoin_deposittransaction', 'transaction_id')


        # User chose to not deal with backwards NULL issues for 'WalletTransaction.from_wallet'
        #raise RuntimeError("Cannot reverse this migration. 'WalletTransaction.from_wallet' and its values cannot be restored.")
        # Deleting field 'BitcoinAddress.migrated_to_transactions'
        # db.delete_column('django_bitcoin_bitcoinaddress', 'migrated_to_transactions')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'migrated_to_transactions': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'confirmations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.WalletTransaction']", 'null': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.outgoingtransaction': {
            'Meta': {'object_name': 'OutgoingTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'executed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'outgoing_transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.OutgoingTransaction']", 'null': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['django_bitcoin']