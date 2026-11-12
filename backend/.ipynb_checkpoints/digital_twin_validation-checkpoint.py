#!/usr/bin/env python
# coding: utf-8

# In[1]:


##########################################################
##########################################################
########### Digital Twin Validation ##############
##########################################################
##########################################################


# In[2]:


##########################################################
# Importing files
##########################################################


# In[172]:


# --- IMPORTS & SETUP ---
get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from matplotlib.colors import LinearSegmentedColormap
from CoreModules.Data_processing import *
from CoreModules.Visualization_engine import *
from CoreModules.Stochastic_simulator import *
from CoreModules.Digital_Twin_engine import *
from CoreModules.doe_engine import *


# In[173]:


def save_plot(fig, folder, filename):
    os.makedirs(folder, exist_ok=True)
    fig.savefig(os.path.join(folder, filename), dpi=300, bbox_inches='tight')
    plt.close(fig)
    
def save_plotty(fig, folder, filename):
    os.makedirs(folder, exist_ok=True)
    fig.write_html(os.path.join(folder, filename + ".html"))


# In[174]:


##########################################################
# 1.Processing data
##########################################################


# In[175]:


##########################################################
## 1.1. General data
##########################################################


# In[177]:


### Defining general parameters
parameters_values = np.array([
    1000, 25, 2000, 30, 800, 10, 0.15, 0.15, 1, 0, 1.5762295081967206, 0, 0.1677, 1887, 1235, 55, 0.308
])


param_names = [
    "UIC_PV", "UL_PV", "UIC_WT", "UL_WT", "UIC_B", "UL_B", 
    "MCH", "MDCH", "PR", "pw_pv_pr", "pw_wt_pr", "ic_pr", "BP_charging_allowed", "CO2_eq_upfront_PV", "CO2_eq_upfront_WT", "CO2_eq_upfront_batt", "CO2_eq_emission_grid"
]

descriptions = [
    "Unit Investment Cost PV (€/kW)", "Useful Life PV (years)",
    "Unit Investment Cost Wind (€/kW)", "Useful Life Wind (years)",
    "Unit Investment Cost Battery (€/kWh)", "Useful Life Battery (years)",
    "Maintenance Cost (fraction of CAPEX)", "Maintenance Cost (fraction of CAPEX)",
    "Performance Ratio", "Installed PV Prosumer (reference)", 
    "Installed Wind Prosumer (reference)", "Installed Battery Prosumer (reference)",
    "Threshold buying price from the grid, from which charging battery from the grid is allowed",
    "Fixed CO2 eq. mass of PV installation (CO2 eq / KW installed)",
    "Fixed CO2 eq. mass of WT installation (CO2 eq / KW installed)",
    "Fixed CO2 eq. mass of BATT installation (CO2 eq / KW installed)",
    "CO2 eq emission of the Spanish grid (CO2 eq / KHh)"
]

# Create the DataFrame
df_EC_parameters = pd.DataFrame({
    'Variable': param_names,
    'Value': parameters_values,
    'Description': descriptions
})
df_EC_parameters.set_index('Variable', inplace=True)
print(df_EC_parameters)


# In[179]:


##########################################################
## 1.2 Loading the prosumer based data
##########################################################


# In[181]:


### Loading prosumers data
prosumer_based_data, row_names_prosumer_based = loading_CSV_data("Datasets/UPC_data_wind_dominant", 'prosumer_based_data.csv', 5)

# Create the DataFrame
df_prosumer_data = pd.DataFrame(row_names_prosumer_based, columns= ['Prosumer based data'])
df_prosumer_data.index.name = 'Attribute_ID'
print(df_prosumer_data)


# In[186]:


print('Prosumer_based_data_shape = ')
print(prosumer_based_data.shape)


# In[188]:


##########################################################
## 1.3 External datasets
##########################################################


# In[190]:


folder_name = 'Datasets'

#1. Market Prices
file_BP = 'Spanish_Buying_price_ESIOS.csv'
file_SP = 'Spanish_Selling_price_ESIOS.csv'

BP_array = process_esios_price_data(f"{folder_name}/{file_BP}", price_name="Buying Price")
SP_array = process_esios_price_data(f"{folder_name}/{file_SP}", price_name="Selling Price")


# In[192]:


#Weather Data
seasonal_time_based, seasonal_upc, row_names = build_and_split_yearly_UPC_matrices(
    objective = 'Economic',
    folder_name='Datasets/UPC_data_wind_dominant', 
    num_prosumers=5, 
    prosumer_based_data=prosumer_based_data, 
    BP_yearly=BP_array[:, 1],
    SP_yearly=SP_array[:, 1])


# In[14]:


#UPC Results Data
UPC_results_data_winter = seasonal_upc['winter']
UPC_results_data_spring = seasonal_upc['spring']
UPC_results_data_summer = seasonal_upc['summer']
UPC_results_data_autumn = seasonal_upc['autumn']


# In[15]:


print('\n--- Winter ---')
print('\nResults_data_shape = ')
print(UPC_results_data_winter.shape)
time_periods_winter = UPC_results_data_winter.shape[2]

print('\n--- Spring ---')
print('\nResults_data_shape = ')
print(UPC_results_data_spring.shape)
time_periods_spring = UPC_results_data_spring.shape[2]

print('\n--- Summer ---')
print('\nResults_data_shape = ')
print(UPC_results_data_summer.shape)
time_periods_summer = UPC_results_data_summer.shape[2]

print('\n--- Autumn ---')
print('\nResults_data_shape = ')
print(UPC_results_data_autumn.shape)
time_periods_autumn = UPC_results_data_autumn.shape[2]


# In[16]:


### UPC data example - Winter

"--- Consumption ---"
print('Consuption P1 = ', -UPC_results_data_winter[0, 10, :].sum().round(2))
print('Consuption P2 = ', -UPC_results_data_winter[1, 10, :].sum().round(2))
print('Consuption P3 = ', -UPC_results_data_winter[2, 10, :].sum().round(2))
print('Consuption P4 = ', -UPC_results_data_winter[3, 10, :].sum().round(2))
print('Consuption P5 = ', -UPC_results_data_winter[4, 10, :].sum().round(2))
"--- PV Energy ---"
print('PV Energy P1 = ', UPC_results_data_winter[0, 0, :].sum().round(2))
print('PV Energy P2 = ', UPC_results_data_winter[1, 0, :].sum().round(2))
print('PV Energy P3 = ', UPC_results_data_winter[2, 0, :].sum().round(2))
print('PV Energy P4 = ', UPC_results_data_winter[3, 0, :].sum().round(2))
print('PV Energy P5 = ', UPC_results_data_winter[4, 0, :].sum().round(2))
"--- Wind Energy ---"
print('Wind Energy P1 = ', UPC_results_data_winter[0, 1, :].sum().round(2))
print('Wind Energy P2 = ', UPC_results_data_winter[1, 1, :].sum().round(2))
print('Wind Energy P3 = ', UPC_results_data_winter[2, 1, :].sum().round(2))
print('Wind Energy P4 = ', UPC_results_data_winter[3, 1, :].sum().round(2))
print('Wind Energy P5 = ', UPC_results_data_winter[4, 1, :].sum().round(2))


# In[17]:


time_based_data_winter = seasonal_time_based['winter']
time_based_data_spring = seasonal_time_based['spring']
time_based_data_summer = seasonal_time_based['summer']
time_based_data_autumn = seasonal_time_based['autumn']


# In[194]:


# Create the DataFrame
df_time_data = pd.DataFrame(row_names, columns= ['Time based data per prosumer'])
df_time_data.index.name = 'Attribute_ID'
print(df_time_data)


# In[196]:


print('\n--- Winter ---')
print('\nTime_based_shape = ')
print(time_based_data_winter.shape)

print('\n--- Spring ---')
print('\nTime_based_shape = ')
print(time_based_data_spring.shape)

print('\n--- Summer ---')
print('\nTime_based_shape = ')
print(time_based_data_summer.shape)

print('\n--- Autumn ---')
print('\nTime_based_shape = ')
print(time_based_data_autumn.shape)


# In[198]:


##########################################################
## 1.4 Loading Time Dependent Data
##########################################################


# In[200]:


#Winter
usr_pv_winter = time_based_data_winter[0, 4, :]/prosumer_based_data[4, 0]
usr_wt_winter = time_based_data_winter[0, 5, :]/prosumer_based_data[5, 0]
pw_pv_pr = df_EC_parameters.loc['pw_pv_pr', 'Value']
pw_wt_pr = df_EC_parameters.loc['pw_wt_pr', 'Value']

E_pv_pr_winter = pw_pv_pr * usr_pv_winter
E_wt_pr_winter = pw_wt_pr * usr_wt_winter


# In[202]:


#Spring
usr_pv_spring = time_based_data_spring[0, 4, :]/prosumer_based_data[4, 0]
usr_wt_spring = time_based_data_spring[0, 5, :]/prosumer_based_data[5, 0]
pw_pv_pr = df_EC_parameters.loc['pw_pv_pr', 'Value']
pw_wt_pr = df_EC_parameters.loc['pw_wt_pr', 'Value']

E_pv_pr_spring = pw_pv_pr * usr_pv_spring
E_wt_pr_spring = pw_wt_pr * usr_wt_spring



# In[203]:


#Summer
usr_pv_summer = time_based_data_summer[0, 4, :]/prosumer_based_data[4, 0]
usr_wt_summer = time_based_data_summer[0, 5, :]/prosumer_based_data[5, 0]
pw_pv_pr = df_EC_parameters.loc['pw_pv_pr', 'Value']
pw_wt_pr = df_EC_parameters.loc['pw_wt_pr', 'Value']

E_pv_pr_summer = pw_pv_pr * usr_pv_summer
E_wt_pr_summer = pw_wt_pr * usr_wt_summer



# In[206]:


#Autumn
usr_pv_autumn = time_based_data_autumn[0, 4, :]/prosumer_based_data[4, 0]
usr_wt_autumn = time_based_data_autumn[0, 5, :]/prosumer_based_data[5, 0]
pw_pv_pr = df_EC_parameters.loc['pw_pv_pr', 'Value']
pw_wt_pr = df_EC_parameters.loc['pw_wt_pr', 'Value']

E_pv_pr_autumn = pw_pv_pr * usr_pv_autumn
E_wt_pr_autumn = pw_wt_pr * usr_wt_autumn


# In[208]:


##########################################################
# 2.Run Digital Twin
##########################################################


# In[210]:


###Winter
results_names_winter, results_data_winter, time_based_data_winter, flow_P2P_names_winter, flow_P2P_winter = twin(time_based_data_winter, prosumer_based_data, df_EC_parameters, E_pv_pr_winter,  E_wt_pr_winter)

# Create the DataFrame
df_results = pd.DataFrame(results_names_winter, columns= ['Results obtained by prosumer - Winter'])
df_results.index.name = 'Attribute_ID'

print(df_results)


# In[212]:


### Saving data to excel
### If one wants to save the energy flows, uncomment the code lines.
### MARKET BASED METHOD:

#export_to_excel_stacked(results_names_winter, results_data_winter, folder_name='Results_data/Comparing_UPC_model_to_DT/Winter', file_name="STACKED_ResultsData_MarketBased.xlsx")
#export_to_excel_stacked(flow_P2P_names_winter, flow_P2P_winter, folder_name='Results_data/Comparing_UPC_model_to_DT/Winter', file_name="STACKED_FlowsP2P_Stacked_MarketBased.xlsx")

### Spring

results_names_spring, results_data_spring, time_based_data_spring, flow_P2P_names_spring, flow_P2P_spring = twin(time_based_data_spring, prosumer_based_data, df_EC_parameters, E_pv_pr_spring,  E_wt_pr_spring)
#export_to_excel_stacked(results_names_spring, results_data_spring, folder_name='Results_data/Comparing_UPC_model_to_DT/Spring', file_name="STACKED_ResultsData_MarketBased.xlsx")
#export_to_excel_stacked(flow_P2P_names_spring, flow_P2P_spring, folder_name='Results_data/Comparing_UPC_model_to_DT/Spring', file_name="STACKED_FlowsP2P_Stacked_MarketBased.xlsx")

### Summer

results_names_summer, results_data_summer, time_based_data_summer, flow_P2P_names_summer, flow_P2P_summer = twin(time_based_data_summer, prosumer_based_data, df_EC_parameters, E_pv_pr_summer,  E_wt_pr_summer)
#export_to_excel_stacked(results_names_summer, results_data_summer, folder_name='Results_data/Comparing_UPC_model_to_DT/Summer', file_name="STACKED_ResultsData_MarketBased.xlsx")
#export_to_excel_stacked(flow_P2P_names_summer, flow_P2P_summer, folder_name='Results_data/Comparing_UPC_model_to_DT/Summer', file_name="STACKED_FlowsP2P_Stacked_MarketBased.xlsx")

### Autumn

results_names_autumn, results_data_autumn, time_based_data_autumn, flow_P2P_names_autumn, flow_P2P_autumn = twin(time_based_data_autumn, prosumer_based_data, df_EC_parameters, E_pv_pr_autumn,  E_wt_pr_autumn)
#export_to_excel_stacked(results_names_autumn, results_data_autumn, folder_name='Results_data/Comparing_UPC_model_to_DT/Autumn', file_name="STACKED_ResultsData_MarketBased.xlsx")
#export_to_excel_stacked(flow_P2P_names_autumn, flow_P2P_autumn, folder_name='Results_data/Comparing_UPC_model_to_DT/Autumn', file_name="STACKED_FlowsP2P_Stacked_MarketBased.xlsx")


# In[213]:


##########################################################
# 3.KPI analysis
##########################################################


# In[214]:


def tag_and_prep(df, season, source):
    temp_df = df.copy() # We make a copy to not change the original
    temp_df.insert(0, 'Source', source) 
    temp_df.insert(1, 'Season', season)
    return temp_df


# In[215]:


##########################################################
# 3.1 Digital Twin KPI's
##########################################################


# In[217]:


#KPIs P2P market
kpis_market_winter, community_market_winter, economic_kpis_market_winter, social_kpis_market_winter, enviromental_kpis_market_winter, sum_analysis_data_market_winter = compute_prosumer_kpis(prosumer_based_data, results_data_winter, flow_P2P_winter, time_based_data_winter, df_EC_parameters)
kpis_market_spring, community_market_spring, economic_kpis_market_spring, social_kpis_market_spring, enviromental_kpis_market_spring, sum_analysis_data_market_spring = compute_prosumer_kpis(prosumer_based_data, results_data_spring, flow_P2P_spring, time_based_data_spring, df_EC_parameters)
kpis_market_summer, community_market_summer, economic_kpis_market_summer, social_kpis_market_summer, enviromental_kpis_market_summer, sum_analysis_data_market_summer = compute_prosumer_kpis(prosumer_based_data, results_data_summer, flow_P2P_summer, time_based_data_summer, df_EC_parameters)
kpis_market_autumn, community_market_autumn, economic_kpis_market_autumn, social_kpis_market_autumn, enviromental_kpis_market_autumn, sum_analysis_data_market_autumn = compute_prosumer_kpis(prosumer_based_data, results_data_autumn, flow_P2P_autumn, time_based_data_autumn, df_EC_parameters)


# In[221]:


###Preparing the Dataframes
prosumer_kpis_market_winter = pd.concat([economic_kpis_market_winter[['Anual profit in %']], social_kpis_market_winter[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_market_winter = pd.DataFrame([community_market_winter])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()

prosumer_kpis_market_spring = pd.concat([economic_kpis_market_spring[['Anual profit in %']], social_kpis_market_spring[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_market_spring = pd.DataFrame([community_market_spring])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()

prosumer_kpis_market_summer = pd.concat([economic_kpis_market_summer[['Anual profit in %']], social_kpis_market_summer[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_market_summer = pd.DataFrame([community_market_summer])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()

prosumer_kpis_market_autumn = pd.concat([economic_kpis_market_autumn[['Anual profit in %']], social_kpis_market_autumn[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_market_autumn = pd.DataFrame([community_market_autumn])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()


# In[223]:


##########################################################
# 3.2 UPC KPI's
##########################################################


# In[225]:


kpis_UPC_winter, community_UPC_winter, economic_kpis_UPC_winter, social_kpis_UPC_winter, enviromental_kpis_UPC_winter, sum_analysis_data_UPC_winter = compute_prosumer_kpis(prosumer_based_data, results_data_winter, flow_P2P_winter, time_based_data_winter, df_EC_parameters, UPC_results_data_winter)
kpis_UPC_spring, community_UPC_spring, economic_kpis_UPC_spring, social_kpis_UPC_spring, enviromental_kpis_UPC_spring, sum_analysis_data_UPC_spring = compute_prosumer_kpis(prosumer_based_data, results_data_spring, flow_P2P_spring, time_based_data_spring, df_EC_parameters, UPC_results_data_spring)
kpis_UPC_summer, community_UPC_summer, economic_kpis_UPC_summer, social_kpis_UPC_summer, enviromental_kpis_UPC_summer, sum_analysis_data_UPC_summer = compute_prosumer_kpis(prosumer_based_data, results_data_summer, flow_P2P_summer, time_based_data_summer, df_EC_parameters, UPC_results_data_summer)
kpis_UPC_autumn, community_UPC_autumn, economic_kpis_UPC_autumn, social_kpis_UPC_autumn, enviromental_kpis_UPC_autumn, sum_analysis_data_UPC_autumn = compute_prosumer_kpis(prosumer_based_data, results_data_autumn, flow_P2P_autumn, time_based_data_autumn, df_EC_parameters, UPC_results_data_autumn)


# In[226]:


###Preparing the Dataframes
prosumer_kpis_UPC_winter = pd.concat([economic_kpis_UPC_winter[['Anual profit in %']], social_kpis_UPC_winter[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_UPC_winter = pd.DataFrame([community_UPC_winter])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()

prosumer_kpis_UPC_spring = pd.concat([economic_kpis_UPC_spring[['Anual profit in %']], social_kpis_market_spring[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_UPC_spring = pd.DataFrame([community_UPC_spring])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()

prosumer_kpis_UPC_summer = pd.concat([economic_kpis_UPC_summer[['Anual profit in %']], social_kpis_UPC_summer[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_UPC_summer = pd.DataFrame([community_UPC_summer])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()

prosumer_kpis_UPC_autumn = pd.concat([economic_kpis_UPC_autumn[['Anual profit in %']], social_kpis_UPC_autumn[['EC savings appropiation', 'Bill reduction in %', 'Contribution into EC investment']]], axis=1)
global_kpis_UPC_autumn = pd.DataFrame([community_UPC_autumn])[[
    'Community total saved in €', 
    'Avoided anual emissions (Kg CO2 eq)', 
    'Community Self-Sufficiency', 
    'Community Grid Dependency', 
    'Fairness index'
]].copy()


# In[227]:


##########################################################
# 3. Comparisons
##########################################################


# In[229]:


###Prosumer level Comparison
dfs_to_combine = [
    tag_and_prep(prosumer_kpis_UPC_winter, 'Winter', 'UPC'),
    tag_and_prep(prosumer_kpis_UPC_spring, 'Spring', 'UPC'),
    tag_and_prep(prosumer_kpis_UPC_summer, 'Summer', 'UPC'),
    tag_and_prep(prosumer_kpis_UPC_autumn, 'Autumn', 'UPC'),
    
    tag_and_prep(prosumer_kpis_market_winter, 'Winter', 'DT_market'),
    tag_and_prep(prosumer_kpis_market_spring, 'Spring', 'DT_market'),
    tag_and_prep(prosumer_kpis_market_summer, 'Summer', 'DT_market'),
    tag_and_prep(prosumer_kpis_market_autumn, 'Autumn', 'DT_market'),

]


master_prosumer_kpis = pd.concat(dfs_to_combine, axis=0)
master_prosumer_kpis.index.name = 'Prosumer'
master_prosumer_kpis = master_prosumer_kpis.reset_index().set_index(['Source', 'Season', 'Prosumer'])

master_prosumer_kpis_fmt = (
    master_prosumer_kpis
    .reset_index()
    .set_index(['Source', 'Season', 'Prosumer'])
    .stack()
    .unstack('Season')
    .rename_axis(index=['Source', 'Prosumer', 'KPI'])
    .reorder_levels(['Source', 'KPI', 'Prosumer'])
    .sort_index()
)


# In[234]:


with pd.option_context('display.max_rows', None, 'display.max_columns', None): print(master_prosumer_kpis.round(4))


# In[236]:


###Community Level Comparison
dfs_to_combine = [
    
    tag_and_prep(global_kpis_UPC_winter, 'Winter', 'UPC'),
    tag_and_prep(global_kpis_UPC_spring, 'Spring', 'UPC'),
    tag_and_prep(global_kpis_UPC_summer, 'Summer', 'UPC'),
    tag_and_prep(global_kpis_UPC_autumn, 'Autumn', 'UPC'),
    
    tag_and_prep(global_kpis_market_winter, 'Winter', 'DT_market'),
    tag_and_prep(global_kpis_market_spring, 'Spring', 'DT_market'),
    tag_and_prep(global_kpis_market_summer, 'Summer', 'DT_market'),
    tag_and_prep(global_kpis_market_autumn, 'Autumn', 'DT_market'),
    
]
master_global_kpis = pd.concat(dfs_to_combine, axis=0, ignore_index=True).set_index(['Source', 'Season'])

master_global_kpis_fmt = (
    master_global_kpis
    .stack()
    .unstack('Season')
    .rename_axis(index=['Source', 'KPI'])
    .sort_index()
)


# In[238]:


print(master_global_kpis.round(4))


# In[42]:


##########################################################
# 4. Energy Flows Verification
##########################################################


# In[69]:


###Bar chart: compares Digital Twins vs UPC consumption and sharing results 
plot_models_matrix(sum_analysis_data_market_winter, sum_analysis_data_UPC_winter)


# In[70]:


###Sankey plot: compares Digital Twin vs UPC results of P2P flow distribution
plot_sankey_models(sum_analysis_data_market_winter, sum_analysis_data_UPC_winter)


# In[71]:


##########################################################
# 5. Verification of Stochastic Data
##########################################################


# In[51]:


##########################################################
# 5.1 Loading Data
##########################################################


# In[52]:


folder_name = 'Datasets'

# 1. Weather Data
file_pv = 'Photovoltaic_generation_data_EU_PVGIS.csv'
file_wt = 'Wind_generation_data_Ninja_database.csv'

USR_PV = process_pvgis_data(f"{folder_name}/{file_pv}")
USR_WT = process_ninja_wind_data(f"{folder_name}/{file_wt}")

# 2. Market Prices
file_BP = 'Spanish_Buying_price_ESIOS.csv'
file_SP = 'Spanish_Selling_price_ESIOS.csv'

BP_array = process_esios_price_data(f"{folder_name}/{file_BP}", price_name="Buying Price")
SP_array = process_esios_price_data(f"{folder_name}/{file_SP}", price_name="Selling Price")

# 3. Load Profile
C = loading_all_consumptions("Datasets/ConsumptionProsumer", 5)
print(f"Array Shape: {C.shape} with (number_prosumers, time, value)")
print(f"Value=0 is timestamp datatype object and Value=1 is the KWh, datatype object")

print("\nALL DATA LOADED SUCCESSFULLY! Ready for Stochastic Simulation.")


# In[53]:


##########################################################
# 5.2 Splitting Data Into Seasons
##########################################################


# In[54]:


solar_seasons = split_into_seasons(USR_PV)
wind_seasons = split_into_seasons(USR_WT)
BP_seasons = split_into_seasons(BP_array)
SP_seasons = split_into_seasons(SP_array)
C1_seasons = split_into_seasons(C[0,:,:])
C2_seasons = split_into_seasons(C[1,:,:])
C3_seasons = split_into_seasons(C[2,:,:])
C4_seasons = split_into_seasons(C[3,:,:])
C5_seasons = split_into_seasons(C[4,:,:])


print(f"Winter hours: {len(solar_seasons['winter'])}")  
print(f"Spring hours: {len(solar_seasons['spring'])}") 
print(f"Summer hours: {len(solar_seasons['summer'])}")  
print(f"Autumn hours: {len(solar_seasons['autumn'])}")  
print(f"Total hours: {len(solar_seasons['winter'])+len(solar_seasons['autumn'])+len(solar_seasons['spring'])+len(solar_seasons['summer'])}")


# In[55]:


master_data_map = {
    'Solar': solar_seasons,
    'Wind': wind_seasons,
    'BP': BP_seasons, # Buying Price
    'SP': SP_seasons,# Selling Price
    'C1': C1_seasons,
    'C2': C2_seasons,
    'C3': C3_seasons,
    'C4': C4_seasons,
    'C5': C5_seasons
}


# In[56]:


##########################################################
# 5.3 Simulation function
##########################################################


# In[57]:


grand_corr_matrices_dict =  build_grand_correlation_matrices(master_data_map)

final_simulation_data = generate_3D_simulation_tensors(
    n_days=900, 
    master_data_map=master_data_map,
    grand_corr_matrices_dict=grand_corr_matrices_dict
);

print("\nSimulation Complete!")
print("\nChecking Winter Solar array shape:", final_simulation_data['winter'][1].shape) 


# In[58]:


def checking_stochastic_data(n_days, prosumer_based_data, df_EC_parameters, master_data_map, seed):
    seasons = ['winter', 'spring', 'summer', 'autumn']
    num_prosumers = prosumer_based_data.shape[1]
    time_periods = n_days * 24
    
    time_based_data_dictionary = {}
    E_pv_pr_dictionary = {}
    E_wt_pr_dictionary = {}
    
    # 1. Generate a fresh stochastic dataset for this iteration
    final_simulation_data = generate_3D_simulation_tensors(n_days, master_data_map, grand_corr_matrices_dict);
            
    for season in seasons:
        # 2. Extract the 30-day stochastic month
        solar_m = final_simulation_data[season][0].flatten()
        wind_m  = final_simulation_data[season][1].flatten()
        BP_m    = final_simulation_data[season][2].flatten()
        SP_m    = final_simulation_data[season][3].flatten()
                
        C1_m = final_simulation_data[season][4].flatten()
        C2_m = final_simulation_data[season][5].flatten()
        C3_m = final_simulation_data[season][6].flatten()
        C4_m = final_simulation_data[season][7].flatten()
        C5_m = final_simulation_data[season][8].flatten()
    
        # Stack the 5 arrays into a single 2D matrix of shape (5_prosumers, hours)
        load_matrix = np.vstack([C1_m, C2_m, C3_m, C4_m, C5_m])

        # 3. Build the time-based data matrix
        time_based_data, _ = create_prosumer_time_matrix_stochastic(num_prosumers, time_periods,prosumer_based_data,
                                                                            load_matrix, solar_m, wind_m, BP_m, SP_m)

        monthly_load_C1 = C1_m.mean() * 24 * n_days
        monthly_load_C2 = C2_m.mean() * 24 * n_days
        monthly_load_C3 = C3_m.mean() * 24 * n_days
        monthly_load_C4 = C4_m.mean() * 24 * n_days
        monthly_load_C5 = C5_m.mean() * 24 * n_days
        monthly_solar = solar_m.mean() * 24 * n_days
        monthly_wind = wind_m.mean() * 24 * n_days
                    
        print(f"\n--- DATA CHECK: Season: {season} ---")
        print(f"Mean Monthly Load P1: {monthly_load_C1:.2f} kWh")
        print(f"Mean Monthly Load P2: {monthly_load_C2:.2f} kWh")
        print(f"Mean Monthly Load P3: {monthly_load_C3:.2f} kWh")
        print(f"Mean Monthly Load P4: {monthly_load_C4:.2f} kWh")
        print(f"Mean Monthly Load P5: {monthly_load_C5:.2f} kWh")
        print("-" * 45)
        print(f"Mean BP (Grid Buying Price):    {BP_m.mean():.4f} €/kWh")
        print(f"Mean SP (Grid Selling Price):   {SP_m.mean():.4f} €/kWh")
        print("-" * 45)
        "--- PV Energy ---"
        print(f'Mean Monthly PV Energy P1: {time_based_data[0, 4, :].sum():.2f} kWh')
        print(f'Mean Monthly PV Energy P2: {time_based_data[1, 4, :].sum():.2f} kWh')
        print(f'Mean Monthly PV Energy P3: {time_based_data[2, 4, :].sum():.2f} kWh')
        print(f'Mean Monthly PV Energy P4: {time_based_data[3, 4, :].sum():.2f} kWh')
        print(f'Mean Monthly PV Energy P5: {time_based_data[4, 4, :].sum():.2f} kWh')
        print("-" * 45)
        "--- Wind Energy ---"
        print(f'Mean Monthly Wind Energy P1: {time_based_data[0, 5, :].sum():.2f} kWh')
        print(f'Mean Monthly Wind Energy P2: {time_based_data[1, 5, :].sum():.2f} kWh')
        print(f'Mean Monthly Wind Energy P3: {time_based_data[2, 5, :].sum():.2f} kWh')
        print(f'Mean Monthly Wind Energy P4: {time_based_data[3, 5, :].sum():.2f} kWh')
        print(f'Mean Monthly Wind Energy P5: {time_based_data[4, 5, :].sum():.2f} kWh')
                                
        #shared generation
        E_pv_pr = solar_m * df_EC_parameters.loc['pw_pv_pr', 'Value']
        E_wt_pr = wind_m * df_EC_parameters.loc['pw_wt_pr', 'Value']
    
        time_based_data_dictionary[season] = time_based_data
     
    return time_based_data_dictionary


# In[59]:


time_based_data_dictionary = checking_stochastic_data(31, prosumer_based_data, df_EC_parameters, master_data_map, 10)


# In[60]:


##########################################################
# 5.4 Verification plots
##########################################################


# In[64]:


check_plot(
    data_dictionary=time_based_data_dictionary, 
    seasonal_upc=seasonal_upc, 
    seasonal_time_based=seasonal_time_based, 
    attribute_name='Consumption', 
    save_image=True
)


# In[65]:


check_plot(
    data_dictionary=time_based_data_dictionary, 
    seasonal_upc=seasonal_upc, 
    seasonal_time_based=seasonal_time_based, 
    attribute_name='Selling Price Grid', 
    save_image=True
)


# In[66]:


check_plot(
    data_dictionary=time_based_data_dictionary, 
    seasonal_upc=seasonal_upc, 
    seasonal_time_based=seasonal_time_based, 
    attribute_name='Buying Price Grid', 
    save_image=True
)


# In[67]:


check_plot(
    data_dictionary=time_based_data_dictionary, 
    seasonal_upc=seasonal_upc, 
    seasonal_time_based=seasonal_time_based, 
    attribute_name='Energy PV', 
    save_image=True
)


# In[68]:


check_plot(
    data_dictionary=time_based_data_dictionary, 
    seasonal_upc=seasonal_upc, 
    seasonal_time_based=seasonal_time_based, 
    attribute_name='Energy Wind', 
    save_image=True
)


# In[ ]:





# In[240]:


get_ipython().system('jupyter nbconvert --to python digital_twin_validation.ipynb')


# In[ ]:





# In[ ]:





# In[ ]:




