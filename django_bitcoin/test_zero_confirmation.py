from django.core.management import setup_environ
import settings
setup_environ(settings)

# Tests only with internal transf
from decimal import Decimal
import unittest
from django_bitcoin import Wallet


class InternalChangesTest(unittest.TestCase):
    def setUp(self):
        self.origin = Wallet.objects.all()[0]

        self.w1 = Wallet.objects.create()
        self.w2 = Wallet.objects.create()
        self.w3 = Wallet.objects.create()
        self.w4 = Wallet.objects.create()
        self.w5 = Wallet.objects.create()
        self.w6 = Wallet.objects.create()
        self.w7 = Wallet.objects.create()

    def testTransactions(self):
        # t1
        self.origin.send_to_wallet(self.w1, Decimal('5'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('5')))

        # t2
        self.w1.send_to_wallet(self.w2, Decimal('1'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('4')))
        self.assertEquals(self.w2.balance(), (Decimal('0'), Decimal('1')))

        # t3
        self.w1.send_to_wallet(self.w3, Decimal('2'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('2')))
        self.assertEquals(self.w3.balance(), (Decimal('0'), Decimal('2')))

        # t1'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w1.static_receiving_address())

        # t4
        self.w1.send_to_wallet(self.w4, Decimal('4'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('0')))
        self.assertEquals(self.w4.balance(), (Decimal('2'), Decimal('2')))

        # t2'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w3.static_receiving_address())

        # t5
        self.w3.send_to_wallet(self.w4, Decimal('4'))
        self.assertEquals(self.w3.balance(), (Decimal('0'), Decimal('0')))
        self.assertEquals(self.w4.balance(), (Decimal('4'), Decimal('4')))

        # t3'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w4.static_receiving_address())

        # t6
        self.w4.send_to_wallet(self.w1, Decimal('10'))
        self.assertEquals(self.w1.balance(), (Decimal('6'), Decimal('4')))
        self.assertEquals(self.w4.balance(), (Decimal('0'), Decimal('0')))

        # t7
        self.w1.send_to_wallet(self.w5, Decimal('6'))
        self.assertEquals(self.w1.balance(), (Decimal('4'), Decimal('0')))
        self.assertEquals(self.w5.balance(), (Decimal('2'), Decimal('4')))

        # t4'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w5.static_receiving_address())

        # t8
        self.w5.send_to_wallet(self.w6, Decimal('8'))
        self.assertEquals(self.w5.balance(), (Decimal('0'), Decimal('0')))
        self.assertEquals(self.w6.balance(), (Decimal('4'), Decimal('4')))

        # t9
        self.w6.send_to_wallet(self.w7, Decimal('4'))
        self.assertEquals(self.w6.balance(), (Decimal('4'), Decimal('0')))
        self.assertEquals(self.w7.balance(), (Decimal('0'), Decimal('4')))

        # t5'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w7.static_receiving_address())

        # t10
        self.w7.send_to_wallet(self.w5, Decimal('6'))
        self.assertEquals(self.w5.balance(), (Decimal('2'), Decimal('4')))
        self.assertEquals(self.w7.balance(), (Decimal('0'), Decimal('0')))

        # t11
        self.w6.send_to_wallet(self.w5, Decimal('2'))
        self.assertEquals(self.w5.balance(), (Decimal('4'), Decimal('4')))
        self.assertEquals(self.w6.balance(), (Decimal('2'), Decimal('0')))

        self.clear()

    def clear(self):
        self.w1.delete()
        self.w2.delete()
        self.w3.delete()
        self.w4.delete()
        self.w5.delete()
        self.w6.delete()
        self.w7.delete()

if __name__ == '__main__':
    unittest.main()
