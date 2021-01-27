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
    
    return round(estimates.sum(axis=1), 2)


def acs_est_pct(estimates, unis):
    
    est_sum = estimates.sum(axis=1)
    
    uni_sum = unis.sum(axis=1)

    return np.round_((est_sum.divide(uni_sum) * 100), 2)
    
def acs_moe(estimates, census_table):
    
    cols = estimates.columns
    zero_ind = set()
    
    for c in cols:
        zero_ind.update(set(estimates[(estimates[c] == 0)].index))

    nonzero_ind = set(estimates.index).difference(zero_ind)
                  
    moe_cols = [c.replace('E', 'M') for c in cols]
    
    #Applies moe formula [1]
    g = census_table.loc[nonzero_ind, moe_cols].applymap(np.square).sum(axis=1)
    
    t = estimates[(estimates[cols] == 0)].dropna(how='all')

    t_2 = t.apply(lambda x: getMOE2(x, census_table))
    t_3 = t.apply(lambda x: getMOE(x, census_table))
    t_2 = t_2.max(axis=1)

    m = (t_3.apply(np.square).sum(axis=1) + t_2.apply(np.square)) #.apply(np.sqrt)
    
    iz = g.append(m)
    iz = iz.apply(np.sqrt)
    iz.name = 'moe'
    estimates = estimates.join(iz)
        
    return round(estimates['moe'], 2)

def acs_moe_pct(estimates, unis, census_table):
    
    est_sum = acs_est(estimates)
    uni_sum = acs_est(unis)
    moe_sum = acs_moe(estimates, census_table)
    moe_uni_sum = acs_moe(unis, census_table)
    
    tbl_1 = moe_sum**2 - (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2
    tbl_2 = moe_sum**2 + (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2
    check_1 = ((moe_sum**2 - (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2) < 0)
    check_2 = ((moe_sum**2 - (est_sum **2 / uni_sum **2) * moe_uni_sum ** 2) >= 0)

    y_1 = 100 / uni_sum[check_1] * np.sqrt(tbl_2[check_1])
    y_2 = 100 / uni_sum[check_2] * np.sqrt(tbl_1[check_2])
        
    return np.round_(y_1.append(y_2), 2)
    
    
    
""" Helper Functions """
def getMOE(x, census_table): #Replaces NaN with MOE estimates
    has_value = x[pd.isnull(x)].index
    x[has_value] = census_table.loc[has_value, x.name.replace('E', 'M')]
    return x

def getMOE2(x, census_table): #Replaces zero values with MOE estimates
    #Get values that are NaN
    not_zero = x[(np.isnan(x))].index
    df = census_table.loc[x.index, x.name.replace('E', 'M')]
    df[not_zero] = np.nan
    return df
    

