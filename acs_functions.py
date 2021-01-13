#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
ACS Collection
Author: Dominic Ridley
"""

import pandas as pd
pd.set_option("display.max_rows", None)
import pickle

import numpy as np

def acs_est(estimates):
    
    return estimates.sum(axis=1)


def acs_est_pct(estimates, unis):
    
    est_sum = estimates.sum(axis=1)
    
    uni_sum = unis.sum(axis=1)

    return round((est_sum.divide(uni_sum) * 100), 2)
    
def acs_moe(estimates):
    
    cols = estimates.columns
    zero_ind = set()
    
    for c in cols:
        zero_ind.update(set(estimates[(estimates[c] == 0)].index))

    nonzero_ind = set(estimates.index).difference(zero_ind)
                  
    moe_cols = [c.replace('E', 'M') for c in cols]
    
    #Applies moe formula [1]
    g = test.loc[nonzero_ind, moe_cols].applymap(np.square).sum(axis=1)
    
    t = estimates[(estimates[cols] == 0)].dropna(how='all')

    t_2 = t.apply(lambda x: getMOE2(x))
    t_3 = t.apply(lambda x: getMOE(x))
    t_2 = t_2.max(axis=1)

    m = (t_3.apply(np.square).sum(axis=1) + t_2.apply(np.square)).apply(np.sqrt)
    
    iz = g.append(m)
    iz = iz.apply(np.sqrt)
    iz.name = 'moe'
    estimates = estimates.join(iz)
        
    return estimates['moe']

def acs_moe_pct(estimates, unis):
    
    
    
    #est_sum, est_uni_sum, moe_sum, moe_uni_sum
    est_sum = acs_est(estimates)
    uni_sum = acs_est(unis)
    moe_sum = acs_moe(estimates)
    moe_uni_sum = acs_moe(unis)
    
    tbl_1 = moe_sum**2 - (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2
    tbl_2 = moe_sum**2 + (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2
    check_1 = ((moe_sum**2 - (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2) < 0)
    check_2 = ((moe_sum**2 - (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2) >= 0)

    y_1 = 100 / uni_sum[check_1] * np.sqrt(tbl_2[check_1])
    y_2 = 100 / uni_sum[check_2] * np.sqrt(tbl_1[check_2])
        
    return y_1.append(y_2)
    
    
""" Helper Functions """
def getMOE(x): #Replaces NaN with MOE estimates
    has_value = x[pd.isnull(x)].index
    x[has_value] = test.loc[has_value, x.name.replace('E', 'M')]
    return x

def getMOE2(x): #Replaces zero values with MOE estimates
    #Get values that are NaN
    not_zero = x[(np.isnan(x))].index
    df = test.loc[x.index, x.name.replace('E', 'M')]
    df[not_zero] = np.nan
    return df
    

