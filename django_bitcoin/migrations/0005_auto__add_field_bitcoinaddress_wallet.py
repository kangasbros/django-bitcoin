# -*- coding: utf-8 -*-
import datetime
from south.db import db

from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'BitcoinAddress.wallet'
        db.add_column('django_bitcoin_bitcoinaddress', 'wallet',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='addresses', null=True, to=orm['django_bitcoin.Wallet']),
                      keep_default=False)

        sql = """
        UPDATE django_bitcoin_bitcoinaddress SET wallet_id = 
        (SELECT wallet_id FROM django_bitcoin_wallet_addresses WHERE bitcoinaddress_id=django_bitcoin_bitcoinaddress.id LIMIT 1)
        """

        db.execute(sql)

        sql = """
        SELECT id, (SELECT wallet_id FROM django_bitcoin_wallet_addresses WHERE bitcoinaddress_id=django_bitcoin_bitcoinaddress.id LIMIT 1)
        FROM django_bitcoin_bitcoinaddress;
        """

        # Removing M2M table for field addresses on 'Wallet'
        db.delete_table('django_bitcoin_wallet_addresses')


    def backwards(self, orm):
        # Deleting field 'BitcoinAddress.wallet'
        raise RuntimeError("Cannot reverse this migration.")


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
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
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
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']