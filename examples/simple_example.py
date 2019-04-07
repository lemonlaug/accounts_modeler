from accounts_modeler.account import *

def simple_example():
    #Establish how long we want to do our forecast for.
    model = Model(pd.Period.now("M").start_time, periods=36, freq='M')
    forecast_period = model.forecast_range
    #Predicted income over forecast period.
    ## Start as annual
    predicted_income = pd.Series([100000, 108000, 113000],
                                 forecast_period.asfreq("A").unique()[:3])
    #Convert to monthly
    predicted_income = predicted_income.asfreq('M', how='s')
    predicted_income = predicted_income.reindex(forecast_period, method='ffill')/12

    #Predicted expenses
    annual_expenses = pd.Series([50000,],
                                   (pd.Period.now('M'),))
    monthly_expenses = annual_expenses.reindex(forecast_period, method='ffill')/12

    checking_account = Account('Checking', balance=10000)
    savings_account = Account('Savings', balance=50000)
    savings_account.add_repeating_data('interest_rate', .03)
    income = Account('Income')
    income.add_repeating_data('predicted_income', predicted_income)
    expenses = Account('Expenses', balance=0)
    expenses.add_repeating_data('monthly_expenses', monthly_expenses)
    down_payment = pd.Series([100000,], (pd.Period.now('M')+30,))
    expenses.add_one_time_data('down_payment', down_payment)
    for account in [checking_account, savings_account, income, expenses]:
        model.add_account(account)

    #Transfers
    savings_interest = Transfer('Savings Interest', income, savings_account,
                                lambda x, y: y.balance*y.interest_rate)
    pay_expenses = Transfer('Pay Expenses', checking_account, expenses,
                            lambda x, y: y.monthly_expenses)
    check_direct_deposit = Transfer('Checking direct deposit', income, checking_account,
                              lambda x, y: .6*x.predicted_income)
    savings_direct_deposit = Transfer('Savings direct depost', income, savings_account,
                                      lambda x, y: .4*x.predicted_income)
    down_payment = Transfer('Down payment', savings_account, expenses,
                            lambda x, y: y.down_payment)

    for transfer in [savings_interest, pay_expenses, check_direct_deposit, savings_direct_deposit, down_payment]:
        model.add_transfer(transfer)

    model.simulate()

    return model

    
if __name__ == "__main__":
    model = simple_example()
    print(savings_account.data)
    print(checking_account.data)
    
