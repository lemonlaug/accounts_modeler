import pandas as pd
import numpy as np


class Account(object):
    """A class representing an account.
    """

    def __init__(self, label, opening_balance=0, interest_rate=0.0):
        """
        Args:
            label: A string naming the acct
            opening_balance: A scalar representing the current balance of 
                the acct.
            interest_rate: A scalar in value representing the interest 
                rate of the account.
        """
        self.label = label
        self.opening_balance = opening_balance
        self.interest_rate = interest_rate

    
    
        
