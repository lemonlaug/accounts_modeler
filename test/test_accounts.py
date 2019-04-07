import unittest
from accounts_modeler.account import *
from accounts_modeler.converters import * 
from datetime import date
from numpy import testing as npt

def get_account(label = 'test account'):
    per = pd.Period("2019-01", freq="M")    
    account = Account(label,
                   balance=pd.Series((100,), index=(per,)))

    account.add_repeating_data('apy', pd.Series((0.1,), index=(per,)))
    return account

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
                    balance=pd.Series((1000,), index=(apy_index[0],)))
        a.add_repeating_data('apy',pd.Series((.1, .2), index=apy_index))
        expect_opening_balance = pd.Series((1000,),
                                           index=(pd.Period.now("M"),))
        #pd.testing.assert_series_equal(a.raw_data['balance'],
        #                            expect_opening_balance) This
        #                            doesn't happen at this time now,
        #                            need to wait till after adding to
        #                            model.


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
        self.m = Model('2019-01-01', periods=4, freq="M")
        opening_balance=pd.Series((100.,), index = (pd.Period("2019-01"),))
        self.apy = pd.Series((.1,), index = (pd.Period("2019-01"), ))
        self.a = Account("test", balance=opening_balance)
        self.a.add_repeating_data('apy', self.apy)
        self.b = Account("Income", balance = opening_balance)
        self.m.add_account(self.a)
        self.m.add_account(self.b)
        self.t = Transfer('test', self.b, self.a,
                          lambda x, y: y.balance*y.apy)
        self.m.add_transfer(self.t)
        
    def test_initialize(self):
        self.assertEqual(len(self.m.forecast_range), 4)

        expect_opening_balance = pd.Series([100.]*4,
                                           index=self.m.forecast_range,
                                           name="balance")
        self.assertTrue(hasattr(self.a, 'data'))
        pd.testing.assert_series_equal(self.a.data.balance,
                                       expect_opening_balance)

    def test_simple_interest_simulation(self):
        self.m.simulate()
        expect_a_data = pd.DataFrame(
            {'apy': [.1]*4, # Sparse data is filled.
             'balance': (100., 110., 121., 133.1)}, # Balance is forecast.
            index = self.m.forecast_range
        )
        pd.testing.assert_frame_equal(expect_a_data, self.a.data)

    def test_simple_income_simulation(self):
        m = Model('2019-01-01', periods=4, freq='M')
        monthly_income = pd.Series([333.]*4, index=self.m.forecast_range)
        self.b.add_repeating_data('monthly_income', monthly_income)
        bonus_income = pd.Series((500., ), (pd.Period('2019-02'),))
        self.b.add_one_time_data('bonus', bonus_income)
        m.add_account(self.b)
        m.add_account(self.a)

        expect_account_data = (pd.concat({'monthly_income': monthly_income,
                                          'bonus': bonus_income}, axis=1)
                               .assign(balance=100.))
        pd.testing.assert_frame_equal(expect_account_data, self.b.data, check_like = True)

        self.assertEqual(len(self.b.data['monthly_income']), 4)

        income_transfer = Transfer('salary', self.b, self.a,
                                   lambda x, y: x.drop('balance',axis=1).sum(axis=1))
        m.add_transfer(income_transfer)
        m.simulate()
        expect_income_data = pd.Series((100., 433., 1266., 1599.),
                                       index=m.forecast_range, name='balance')
        pd.testing.assert_series_equal(expect_income_data,
                                      self.a.data.balance)

class TestConverters(unittest.TestCase):
    def setUp(self):
        self.higher_freq = pd.period_range('2019-01', periods=3, freq="M")

    def test_convert_repeating(self):
        data = pd.Series((10,), (pd.Period('2019'),))
        converted = convert_repeating(data, self.higher_freq)

        expect_converted = pd.Series([10]*3, self.higher_freq)
        pd.testing.assert_series_equal(converted, expect_converted)

    def test_convert_one_time(self):
        data = pd.Series((120,), (pd.Period('2019'), ))
        converted = convert_one_time(data, self.higher_freq)
        expect_converted = pd.Series([10.]*3, self.higher_freq)
        pd.testing.assert_series_equal(converted, expect_converted)

        data = pd.Series((120,), (pd.Period('2019-01'),))
        lower_freq = pd.period_range("2019", periods=1, freq="A")
        converted = convert_one_time(data, lower_freq)
        
if __name__ == "__main__":
    unittest.main()

