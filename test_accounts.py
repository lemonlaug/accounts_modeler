import unittest
from account import *
from datetime import date
from numpy import testing as npt

def get_account(label = 'test account'):
    return Account(label,
                   opening_balance=100,
                   apy=0.1)

class TestAccount(unittest.TestCase):
    def test_initialize_scalar(self):
        a = get_account()

        self.assertEqual(a.label, 'test account')
        this_period = pd.Period.now("D")
        expect_balance = pd.Series((100,), index=(this_period,))
        expect_apy = pd.Series((.1,), index=(this_period,))
        npt.assert_almost_equal(a.data.balance, expect_balance)
        npt.assert_almost_equal(a.data.apy, expect_apy)

    def test_account_raw_data(self):
        apy_index = pd.period_range('2019-05', periods=2)
        a = Account("test data",
                    opening_balance=1000,
                    apy = pd.Series((.1, .2), index=apy_index))
        expect_opening_balance = pd.Series((1000,),
                                           index=(pd.Period.now("D"),))
        pd.testing.assert_series_equal(a.raw_data['opening_balance'],
                                    expect_opening_balance)
        self.assertRaises(TypeError, lambda x: Account("bad init",
                                                       wontwork = {"one", 1}))

class TestFrequencyConversion(unittest.TestCase):
    def test_conversion_to_higher_freq(self):
        a = Account('test acccount',
                    balance = pd.Series((100,),
                                         index=(pd.Period('2019'),)))
        forecast_index = pd.period_range("2019-02", periods=4, freq="M")
        balance = a._index_series_to(a.raw_data['balance'],
                                     forecast_index)
        expect_balance = pd.Series([100]*4, index = forecast_index)
        pd.testing.assert_series_equal(balance, expect_balance)
                                       

    def test_conversion_to_lower_freq(self):
        pass
    
    def test_custom_conversion_logic(self):
        pass
        

class TestTransfer(unittest.TestCase):
    def test_initialize_transfer(self):
        a = get_account('from')
        b = get_account('to')
        t = Transfer('interest', a, b,
                     lambda x, y: x.balance*x.apy,
                     lambda x: x.xs('from', level=0, axis=1, drop_level=False)*.1)

        columns = pd.MultiIndex.from_tuples([('from', 'transfer to to'),
                                             ('to', 'transfer from from')])
        expect_gross_transfer = pd.Series([-10., 10.], index=columns).to_frame(2019).T
        calc_gross_transfer = t._gross_transfers(2019)

        pd.testing.assert_frame_equal(calc_gross_transfer['gross transfers'],
                                      expect_gross_transfer)

        calc_tax = t._taxes(2019, calc_gross_transfer)
        columns = pd.MultiIndex.from_tuples([('taxes',
                                              'from',
                                              'transfer to to')])
        expect_tax = pd.DataFrame({'foo': [-1.]}, index=(2019,))
        expect_tax.columns = columns
        pd.testing.assert_frame_equal(calc_tax, expect_tax)

        #check net tax
        t.calc_transfers(2019)
        pd.testing.assert_frame_equal(t.data['net'],
                                      t.data['gross transfers'] - t.data['taxes'])
        #So I guess we need another hierarchical index level in our dataframe.

        #Add to account data?
        

    def Xtest_interest_transfer(self):
        a = get_account("interest account")
        t = Interest(a)
        transfer = t.calculate_transfer(2019)
        npt.assert_almost_equal(transfer.values, np.array([[10, -10]]))

class TestModel(unittest.TestCase):
    def test_initialize(self):
        m = Model('2019-01-01', periods=3, freq="M")
        self.assertEqual(len(m.forecast_range), 3)

        calc_period_interest = m._period_interest_rate(.1)

        expect_period_interest = [0.0081276, 0.0073382, 0.0081276]
        expect_period_interest = pd.Series(expect_period_interest,
                                           index=m.forecast_range)
        
        pd.testing.assert_series_equal(calc_period_interest,
                                       expect_period_interest,
                                       check_less_precise=True)
        
if __name__ == "__main__":
    unittest.main()

