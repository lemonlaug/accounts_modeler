import unittest
from account import *

class TestAccount(unittest.TestCase):
    def test_initialize_scalar(self):
        a = Account('test account',
                    opening_balance=100,
                    interest_rate=0.1
        )

        self.assertEqual(a.label, 'tests_account')
        self.assertEqual(opening_balance, 100)
        self.assertEqual(interest_rate, .1)

if __name__ == "__main__":
    unittest.main()

