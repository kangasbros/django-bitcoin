# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

from django.contrib import admin

from django_bitcoin import models

class TransactionAdmin(admin.ModelAdmin):
    """Management of ``Transaction`` - Disable address etc editing
    """

    list_display = ('address', 'created_at', 'amount')
    readonly_fields = ('address', 'created_at', 'amount')


class BitcoinAddressAdmin(admin.ModelAdmin):
    """Deal with ``BitcoinAddress``
    No idea in being able to edit the address, as that would not
    sync with the network
    """

    list_display = ('address', 'label', 'created_at', 'least_received', 'active')
    readonly_fields = ('address',)


class PaymentAdmin(admin.ModelAdmin):
    """Allow the edit of ``description``
    """

    list_display = ('created_at', 'description', 'paid_at', 'address', 'amount', 'amount_paid', 'active')
    readonly_fields = ('address', 'amount', 'amount_paid', 'created_at', 'updated_at', 'paid_at', 'withdrawn_total', 'transactions')


class WalletTransactionAdmin(admin.ModelAdmin):
    """Inter-site transactions
    """

    list_display = ('created_at', 'from_wallet', 'to_wallet', 'to_bitcoinaddress', 'amount')
    readonly_fields = ('created_at', 'from_wallet', 'to_wallet', 'to_bitcoinaddress', 'amount')


class WalletAdmin(admin.ModelAdmin):
    """Admin ``Wallet``
    """
    addresses = lambda wallet: wallet.addresses.all()
    addresses.short_description = 'Addresses'

    list_display = ('created_at', 'label', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', addresses, 'transactions_with')


admin.site.register(models.Transaction, TransactionAdmin)
admin.site.register(models.BitcoinAddress, BitcoinAddressAdmin)
admin.site.register(models.Payment, PaymentAdmin)
admin.site.register(models.WalletTransaction, WalletTransactionAdmin)
admin.site.register(models.Wallet, WalletAdmin)

# EOF

