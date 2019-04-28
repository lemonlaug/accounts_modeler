import pandas as pd
import numpy as np
from datetime import date
from accounts_modeler.converters import *

class Model(object):
    """Class representing our overall forecast parametes.
    """
    def __init__(self, *args, **kwargs):
        self.forecast_range = pd.date_range(*args, **kwargs).to_period()
        self.accounts = []
        self.transfers = []

    def add_account(self, account):
        account._index_to(self.forecast_range)
        self.accounts.append(account)

    def add_transfer(self, transfer):
        self.transfers.append(transfer)

    def _step(self, period):
        """Iterate forward one period.
        """
        for account in self.accounts:
            self.execute_transfers(period-1)
            account.update_balances(period)

    def execute_transfers(self, period):
        for transfer in self.transfers:
            transfer.calc_transfers(period)
            
    def simulate(self):
        for period in self.forecast_range.values[1:]:
            self._step(period)

    def report_balances(self, account_names=None,
                        exclude={"Expenses", "Income"}):
        if not account_names:
            account_names = {acct.label for acct in self.accounts}
        report = (pd.concat({acct.label: acct.data.balance
                             for acct in self.accounts
                             if acct.label in account_names-exclude},
                         axis=1)
                  .assign(Total=lambda x: x.sum(axis=1)))
        return report
        

class Account(object):
    """A class representing an account.
    """

    def __init__(self, label, balance=0):
        """
        Args:
            label: A string naming the acct
            opening_balance: A scalar representing the current balance of 
                the acct.
        
        """
        self.label = label
        self.raw_data = {}
        self.data = pd.DataFrame()
        self.transfer_data = pd.DataFrame()
        self.add_repeating_data('balance', balance)

    def add_raw_data(self, label, data, converter):
        new_data = {label: (data, converter)}
        self.raw_data.update(new_data)

    def add_repeating_data(self, label, data):
        self.add_raw_data(label, data, convert_repeating)

    def add_one_time_data(self, label, data):
        self.add_raw_data(label, data, convert_one_time)
        
    def _is_valid_data_series(self, value):
        return isinstance(value, pd.Series) and isinstance(value.index, pd.PeriodIndex)

    def _index_to(self, index):
        data = {key: self._index_series_to(series, index, converter)
                for key, (series, converter)  in self.raw_data.items()}
        self.data = pd.concat(data, axis = 1)
    
    def _index_series_to(self, series, index, converter):
        return converter(series, index)
        
    def total_transfers(self, period):
        return self.transfer_data.sum(axis=1).get(period, 0)
        
    def update_balances(self, period):
        old_balance = self.data.balance[period-1]
        new_balance = (old_balance + self.total_transfers(period-1))
        new_balance = pd.DataFrame({'balance': (new_balance,)}, index=(period,))
        self.data = new_balance.combine_first(self.data)

    def iterate_forecast(self, period):
        pass

    def add_transfers_data(self, data):
        this_accounts_transfers = data.xs(self.label, level=1, axis=1)
        if self.transfer_data.index.empty:
            self.transfer_data = this_accounts_transfers
        else:
            index_union = self.transfer_data.columns.union(this_accounts_transfers.columns)
            this_accounts_transfers.reindex(columns = index_union)
            self.transfer_data = this_accounts_transfers.combine_first(self.transfer_data)
        

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
        self.label = label
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
            (-transfer).rename(self.transfer_to_label),
            transfer.rename(self.transfer_from_label)
        ], axis = 1)
        
        return pd.concat({'gross transfers': transfers}, axis = 1)

    def calc_transfers(self, period):
        ## gross transfers
        gross = self._gross_transfers(period)
        if self.data.index.empty:
            self.data = gross
        else:
            self.data = gross.combine_first(self.data)
        self.to_acct.add_transfers_data(self.data)
        self.from_acct.add_transfers_data(self.data)

    @property
    def transfer_to_label(self):
        return (self.from_acct.label,
                'transfer to {}'.format(self.to_acct.label))

    @property
    def transfer_from_label(self):
        return (self.to_acct.label,
                'transfer from {}'.format(self.from_acct.label))
