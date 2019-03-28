import pandas as pd
import numpy as np
from datetime import date

class Model(object):
    """Class representing our overall forecast parametes.
    """
    def __init__(self, *args, **kwargs):
        self.forecast_range = pd.date_range(*args, **kwargs).to_period()
        self.accounts = []

    def add_account(self, account):
        account.between_period_interest = self.period_interest_rate()
        self.accounts.append(account)

    def _period_interest_rate(self, apy):
        # Move this logic to account.  Really we should accept an
        # interest rate and then fill it forward in the account to get
        # to the right freq
        """Calculate the period level interest rate
        from an APY."""
        days_in_period = self.forecast_range.start_time
        days_in_period -= self.forecast_range.end_time
        days_in_period = days_in_period.days * -1.
        n_days_in_year = self.forecast_range.is_leap_year + 365
        period_apy = np.ones(days_in_period.shape) + apy
        share_of_year = days_in_period / n_days_in_year
        rates = np.power(period_apy, share_of_year) - 1
        return pd.Series(rates, index=self.forecast_range)        

class Account(object):
    """A class representing an account.
    """

    def __init__(self, label, **kwargs):
        """
        Args:
            label: A string naming the acct
            opening_balance: A scalar representing the current balance of 
                the acct.
            interest_rate: A scalar in value representing the interest 
                rate of the account.
        """
        self.label = label
        self.raw_data = {key: self._convert_raw(value)
                         for key, value in kwargs.items()}
        self.data = pd.DataFrame() #TODO: need to initialize the balance and interest rates to the model.
        self.between_period_interest = None

    def _convert_raw(self, value):
        """If a value is a scalar value, conver to a period index with date
        today.

        Args:
            value: a pandas Series with period index or a numeric value

        Returns:
            a pandas Series with period index.
        """
        if isinstance(value, (int, float)):
            return pd.Series((value), index = (pd.Period.now("D"), ))
        elif self._is_valid_data_series(value):
            return value
        else:
            msg = ("Value supplied to _convert_raw should be numeric"
                   "scalar or Series with PeriodIndex, not {}")
            raise TypeError(msg.format(type(value)))

    def _is_valid_data_series(self, value):
        return isinstance(value, pd.Series) and isinstance(value.index, pd.PeriodIndex)

    def _index_series_to(self, series, index):
        new_freq = series.resample(index.freq, convention="s").pad()
        index_union = pd.Index.union(new_freq.index, index)
        old_and_new_index = new_freq.reindex(index_union, method="ffill")
        new_index_only = old_and_new_index.reindex(index)
        return new_index_only

    def _set_initial_balances(self, period):
        # Set data
        pass
        
    def _period_rate(self, period):
        #Calc interest for this account for a given period.
        pass

    def set_up(self, period_index):
        self._apy_to_index
        self._set_data(period_index[0])

    def execute_transfers(self, period):
        period_data = pd.DataFrame()
        for transfer in self.transfers:
            transfer.calc_transfers(period)
            period_data = pd.concat([period_data, transfer.data], axis = 1)
        self.transfer_data = pd.concat([self.transfer_data, period_data])
        #The above is not idempotent...
        
    def update_balances(self, period):
        old_balance = self.data[period-1]
        new_balance = old_balance + self.total_transfers

    def iterate_forecast(self, period):
        pass
        

class Transfer(object):
    """Class representing a rule for transferring between accounts
    """
    def __init__(self, label, from_acct, to_acct, transfer_rule,
                 tax_rule=lambda x, y: x*0):
        """
        Args:
            from_acct: An account object representing the source.
            to_acct: An account object representing the destination.
            rule: A function that calclulates the transfer amount based on
                current details of the accounts.
        """
        self.from_acct = from_acct
        self.to_acct = to_acct
        self.transfer_rule = transfer_rule
        self.tax_rule = tax_rule
        self.data = pd.DataFrame()

    def _gross_transfers(self, period):
        from_values = self.from_acct.data.loc[[period],:]
        to_values = self.to_acct.data.loc[[period],:]
        transfer = self.transfer_rule(from_values, to_values)

        transfers = pd.concat([
            self._get_transfer_entry(-transfer, self.transfer_to_label),
            self._get_transfer_entry(transfer, self.transfer_from_label)
        ], axis = 1)
        
        return pd.concat({'gross transfers': transfers}, axis = 1)

    def calc_transfers(self, period):
        #Add to account data
        ## gross transfers
        gross = self._gross_transfers(period)
        ## taxes
        taxes = self._taxes(period, gross)
        ## net transfers
        net = gross['gross transfers'] - taxes['taxes']
        net = pd.concat({'net': net}, axis = 1)
        combined = pd.concat([gross, taxes, net], axis=1)
        self.data = pd.concat([self.data, combined], axis =1)

    def _taxes(self, period, gross_transfers):
        taxes = gross_transfers['gross transfers'].pipe(self.tax_rule)
        return pd.concat({'taxes': taxes}, axis = 1)        
        
    @property
    def transfer_to_label(self):
        return (self.from_acct.label,
                'transfer to {}'.format(self.to_acct.label))

    @property
    def transfer_from_label(self):
        return (self.to_acct.label,
                'transfer from {}'.format(self.from_acct.label))
        
    def _get_transfer_entry(self, transfer, name):
        return transfer.rename(name)

class Interest(Transfer):
    """Special case of transfer for describing interest reinvested.

    #This should basically draw interest FROM an income account.
    #Then deposit it to the account.
    """
    def __init__(self, account):
        super().__init__(self, income, account,
                         transfer_rule=lambda x, y: x.balance*x.apy)
        pass
