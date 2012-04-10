# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Transaction'
        db.create_table('django_bitcoin_transaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('django_bitcoin', ['Transaction'])

        # Adding model 'BitcoinAddress'
        db.create_table('django_bitcoin_bitcoinaddress', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('least_received', self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=16, decimal_places=8)),
        ))
        db.send_create_signal('django_bitcoin', ['BitcoinAddress'])

        # Adding model 'Payment'
        db.create_table('django_bitcoin_payment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('amount_paid', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('paid_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('withdrawn_total', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
        ))
        db.send_create_signal('django_bitcoin', ['Payment'])

        # Adding M2M table for field transactions on 'Payment'
        db.create_table('django_bitcoin_payment_transactions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('payment', models.ForeignKey(orm['django_bitcoin.payment'], null=False)),
            ('transaction', models.ForeignKey(orm['django_bitcoin.transaction'], null=False))
        ))
        db.create_unique('django_bitcoin_payment_transactions', ['payment_id', 'transaction_id'])

        # Adding model 'WalletTransaction'
        db.create_table('django_bitcoin_wallettransaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('from_wallet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sent_transactions', to=orm['django_bitcoin.Wallet'])),
            ('to_wallet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='received_transactions', null=True, to=orm['django_bitcoin.Wallet'])),
            ('to_bitcoinaddress', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('django_bitcoin', ['WalletTransaction'])

        # Adding model 'Wallet'
        db.create_table('django_bitcoin_wallet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
        ))
        db.send_create_signal('django_bitcoin', ['Wallet'])

        # Adding M2M table for field addresses on 'Wallet'
        db.create_table('django_bitcoin_wallet_addresses', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('wallet', models.ForeignKey(orm['django_bitcoin.wallet'], null=False)),
            ('bitcoinaddress', models.ForeignKey(orm['django_bitcoin.bitcoinaddress'], null=False))
        ))
        db.create_unique('django_bitcoin_wallet_addresses', ['wallet_id', 'bitcoinaddress_id'])


    def backwards(self, orm):
        
        # Deleting model 'Transaction'
        db.delete_table('django_bitcoin_transaction')

        # Deleting model 'BitcoinAddress'
        db.delete_table('django_bitcoin_bitcoinaddress')

        # Deleting model 'Payment'
        db.delete_table('django_bitcoin_payment')

        # Removing M2M table for field transactions on 'Payment'
        db.delete_table('django_bitcoin_payment_transactions')

        # Deleting model 'WalletTransaction'
        db.delete_table('django_bitcoin_wallettransaction')

        # Deleting model 'Wallet'
        db.delete_table('django_bitcoin_wallet')

        # Removing M2M table for field addresses on 'Wallet'
        db.delete_table('django_bitcoin_wallet_addresses')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'})
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
            'addresses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'symmetrical': 'False'}),
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
