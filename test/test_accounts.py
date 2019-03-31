import unittest
from accounts_modeler.account import *
from datetime import date
from numpy import testing as npt

def get_account(label = 'test account'):
    per = pd.Period("2019-01", freq="M")    
    return Account(label,
                   balance=pd.Series((100,), index=(per,)),
                   apy=pd.Series((0.1,), index=(per,)))

class TestAccount(unittest.TestCase):
    def Xtest_initialize_scalar(self):
        a = get_account()

        self.assertEqual(a.label, 'test account')
        this_period = pd.Period.now("M")
        expect_balance = pd.Series((100,), index=(this_period,))
        expect_apy = pd.Series((.1,), index=(this_period,))
        pd.testing.assert_series_equal(a.raw_data['balance'], expect_balance)
        pd.testing.assert_series_equal(a.raw_data['apy'], expect_apy)

    def test_account_raw_data(self):
        apy_index = pd.period_range('2019-05', periods=2)
        a = Account("test data",
                    opening_balance=1000,
                    apy = pd.Series((.1, .2), index=apy_index))
        expect_opening_balance = pd.Series((1000,),
                                           index=(pd.Period.now("M"),))
        pd.testing.assert_series_equal(a.raw_data['opening_balance'],
                                    expect_opening_balance)
        self.assertRaises(TypeError, lambda x: Account("bad init",
                                                       wontwork = {"one", 1}))


class TestTransfer(unittest.TestCase):
    def setUp(self):
        self.a = get_account('from')
        self.b = get_account('to')
        self.m = Model('2019-01-01', periods=3, freq="M")
        self.m.add_account(self.a)
        self.m.add_account(self.b)
        self.t = Transfer('test', self.a, self.b, lambda x, y: x.balance*x.apy)
        self.per = pd.Period('2019-01')
        self.per2 = pd.Period('2019-02')
        
    def test_calc_gross_transfer(self):
        gt = self.t._gross_transfers(self.per)
        expected_gt = pd.DataFrame({('gross transfers', 'from', 'transfer to to'): -10.,
                                    ('gross transfers', 'to', 'transfer from from'): 10.
        },
                                   index=(self.per,))
        pd.testing.assert_frame_equal(expected_gt, gt)

    def test_calc_transfers(self):
        self.t.calc_transfers(self.per)

        expected_data = pd.DataFrame(
            {('gross transfers', 'from', 'transfer to to'): -10.,
             ('gross transfers', 'to', 'transfer from from'): 10.
        },
            index=(self.per,))
        self.t.calc_transfers(self.per) #Even if called twice the result is the same.
        pd.testing.assert_frame_equal(expected_data, self.t.data)

        #And it works for multiple periods
        self.t.calc_transfers(self.per2)
        expected_data2 = pd.DataFrame(
            {('gross transfers', 'from', 'transfer to to'): (-10., -10.),
             ('gross transfers', 'to', 'transfer from from'): (10., 10.)
        },
            index=(self.per, self.per2))
        pd.testing.assert_frame_equal(expected_data2, self.t.data)


    def test_transfers_added_to_acct(self):
        self.t.calc_transfers(self.per)
        self.t.calc_transfers(self.per2)
        
        pd.testing.assert_frame_equal(
            self.a.transfer_data,
            self.t.data.xs('from', level=1, axis=1))

        pd.testing.assert_frame_equal(
            self.b.transfer_data,
            self.t.data.xs('to', level=1, axis=1))

        self.assertEqual(
            self.b.total_transfers('2019-01'), 10.)

        self.a.update_balances(self.per2)
        self.assertTrue(self.a.data.balance[self.per2], 110)


class TestModel(unittest.TestCase):
    def setUp(self):
        self.m = Model('2019-01-01', periods=3, freq="M")
        opening_balance=pd.Series((100.,), index = (pd.Period("2019-01"),))
        self.apy = pd.Series((.1,), index = (pd.Period("2019-01"), ))
        self.a = Account("test", balance=opening_balance, apy=self.apy)
        self.b = Account("Income", balance = opening_balance)
        self.m.add_account(self.a)
        self.m.add_account(self.b)
        self.t = Transfer('test', self.b, self.a,
                          lambda x, y: y.balance*y.apy)
        self.m.add_transfer(self.t)
        
    def test_initialize(self):
        self.assertEqual(len(self.m.forecast_range), 3)

        expect_opening_balance = pd.Series([100.]*3,
                                           index=self.m.forecast_range,
                                           name="balance")
        self.assertTrue(hasattr(self.a, 'data'))
        pd.testing.assert_series_equal(self.a.data.balance,
                                       expect_opening_balance)

    def test_simple_interest_simulation(self):
        self.m.simulate()
        expect_a_data = pd.DataFrame(
            {'apy': [.1]*3, # Sparse data is filled.
             'balance': (100., 110., 121.)}, # Balance is forecast.
            index = self.m.forecast_range
        )
        pd.testing.assert_frame_equal(expect_a_data, self.a.data)

    def test_simple_income_simulation(self):
        m = Model('2019-01-01', periods=3, freq='M')
        monthly_income = pd.Series([333]*3, index=self.m.forecast_range)
        self.b.add_raw_data(monthly_income=monthly_income)
        m.add_account(self.b)
        m.add_account(self.a)
        self.assertEqual(len(self.b.raw_data['monthly_income']), 3)

        income_transfer = Transfer('salary', self.b, self.a,
                                   lambda x, y: x.monthly_income)
        m.add_transfer(income_transfer)
        m.simulate()
        expect_income_data = pd.Series((100., 433., 766.,),
                                       index=m.forecast_range, name='balance')
        pd.testing.assert_series_equal(expect_income_data,
                                      self.a.data.balance)
        
if __name__ == "__main__":
    unittest.main()

