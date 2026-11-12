##########################################################
##########################################################
########### Running Full Factorial Analysis ##############
##########################################################
##########################################################


##########################################################
# Importing files
##########################################################


# --- IMPORTS & SETUP ---

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import time
import statsmodels.api as sm
import statsmodels.formula.api as smf
import scipy.stats as stats
from datetime import datetime

from matplotlib.colors import LinearSegmentedColormap
from CoreModules.Data_processing import *
from CoreModules.Visualization_engine import *
from CoreModules.Stochastic_simulator import *
from CoreModules.Digital_Twin_engine import *
from CoreModules.doe_engine import *



##########################################################
# 1. Importing data
##########################################################


##########################################################
## 1.1. General data
##########################################################


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

time_periods = 744

#usr_pv = np.loadtxt('Datasets/UPC_data/radiation.txt')[:time_periods]
#usr_wt = np.loadtxt('Datasets/UPC_data/gross_power.txt')[:time_periods]
#pw_pv_pr = df_EC_parameters.loc['pw_pv_pr', 'Value']
#pw_wt_pr = df_EC_parameters.loc['pw_wt_pr', 'Value']

#E_pv_pr = pw_pv_pr * usr_pv
#E_wt_pr = pw_wt_pr * usr_wt
#E_pv_pr = pw_pv_pr*usr_pv
#E_wt_pr = pw_wt_pr*usr_wt 



##########################################################
## 1.2 Loading the prosumer based data
##########################################################


### Loading prosumers data
prosumer_based_data, row_names_prosumer_based = loading_CSV_data("Datasets/UPC_data_wind_dominant", 'prosumer_based_data.csv', 5)

# Create the DataFrame
df_prosumer_data = pd.DataFrame(row_names_prosumer_based, columns= ['Prosumer based data'])
df_prosumer_data.index.name = 'Attribute_ID'
print(df_prosumer_data)



print('Prosumer_based_data_shape = ')
print(prosumer_based_data.shape)



##########################################################
## 1.3 External datasets
##########################################################


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

print(f"\nArray Shape: {C.shape} with (number_prosumers, time, value)")
print(f"Value=0 is timestamp datatype object and Value=1 is the KWh, datatype object")

print("\nALL DATA LOADED SUCCESSFULLY! Ready for Stochastic Simulation.")




##########################################################
### 1.3.1 Spliting data into seasons
##########################################################




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



##########################################################
## 1.4 Importing the Design of Experiment (DoE) excel
##########################################################



doe_matrix = import_doe_matrix('Datasets/doe_randomized.xlsx')
print(doe_matrix)



##########################################################
# 2. Monte Carlo 
##########################################################


## Note! If one wanted to run the full factorial experiment would have to run this line. It has a duration of approximatelly 12 hours.

#df_master_comm, df_master_pros = fullfactorial(doe_environmental_only, 200, 31, prosumer_based_data, df_EC_parameters, master_data_map, 10)



##########################################################
# 3. Processing the data
##########################################################

### Importing the data from previous experiments
df_comm, df_pros = load_doe_results_from_excel()

print(df_comm)
print(df_pros)




##########################################################
# 4. Obtaining the results for the KPi and their confidence intervals for the baseline configurations
##########################################################


## Choosing the desired KPIs
target_kpis = [
    'Community total saved in €',
    'Avoided anual emissions (Kg CO2 eq)',
    'Community Self-Sufficiency',
    'Community Grid Dependency',
    'Fairness index'
]
target_prosumer_kpis = [
    'Anual profit in %', 
    'EC savings appropiation',
    'Saved by entering community € per month'
]



## Defining the baseline configurations
baseline_yearly_matrix = pd.DataFrame({
    'Season':     ['Winter', 'Spring', 'Summer', 'Autumn'],
    'P2P method': ['Market', 'Market', 'Market', 'Market'],
    'BP tariff':  ['Baseline', 'Baseline', 'Baseline', 'Baseline'],
    'Batteries':  ['Baseline', 'Baseline', 'Baseline', 'Baseline'],
    'Consumption':['Baseline', 'Baseline', 'Baseline', 'Baseline'],
}, index=[126, 4, 19, 13])  # ← replace with the real run numbers
baseline_yearly_matrix.index.name = 'Run Order'

print(baseline_yearly_matrix)


## Creating the dataframes

df_comm_baseline = build_kpi_table_with_ci(baseline_yearly_matrix, 'Market', 'DT_market', target_kpis, is_community=True)
df_pros_baseline = build_kpi_table_with_ci(baseline_yearly_matrix, 'Market', 'DT_market', target_prosumer_kpis, is_community=False)

print(df_comm_baseline)
print(df_pros_baseline)


## Saving the dataframes if desired
folder = f"Results/Results_DOE/Original_Experiment/KPI_results_baseline"
file = f"Baseline_KPI_results.xlsx"
os.makedirs(folder, exist_ok=True)
path = f"{folder}/{file}"

with pd.ExcelWriter(path) as writer:
    df_comm_baseline.to_excel(writer, sheet_name="Community KPIs")
    df_pros_baseline.to_excel(writer, sheet_name="Prosumer KPIs")

print(f"Files properly saved at: {path}!")



##########################################################
### PLOTTING: Line charts
##########################################################


'''
Please note that the community variables to choose from are:

community_kpis = [
        "Community Self-Sufficiency", 
        "Self-sufficiency difference between prosumers",
        "Community Grid Dependency",
        "Community Self-Consumption",
        "Community total final bill in €",
        "Community total saved in €",
        "Fairness index", 
        'Baseline poverty help', 
        'Avoided anual emissions (Kg CO2 eq)', 
        'Enviromental impact', 
        'TOTAL carbon payback time in years']

prosumer_kpis = [
    
        'Self-Consumption Ratio',    
        'Self-Sufficiency Ratio',       
        'Grid Dependency',      
        'Net P2P Balance in KWh per simulated period',       
        'P2P Participation in KWh per simulated period',       
        'Shared energy in KWH (G2P-P2G) per simulated period',        
        'P2P trading index in deficit',        
        'P2P trading index in surplus',      
        'Total final bill in € per month',       
        'Saved by entering community € per month',        
        'Anual profit in %',         
        'Anual profit PV in %',         
        'Anual profit WT in %',         
        'Anual profit bateries in %',         
        'Payback time PV',         
        'Payback time WT',        
        'Payback time BATT',         
        'Bill reduction in %',         
        'EC gain appropiation',         
        'EC savings appropiation',         
        'Contribution into EC investment',        
        'Avoided anual emissions (Kg CO2 eq)',       
        'Enviromental impact', 
        'Upfront carbon debt (Kg CO2 eq)', 
        'TOTAL carbon payback time in years', 
        'PV carbon payback time in years', 
        'WT carbon payback time in years', 
        'BATT carbon payback time in years'
]
''';

'''
community_kpis_name = [
        "Community Self-Sufficiency", 
        "Self-sufficiency difference between prosumers",
        "Community Grid Dependency",
        "Community Self-Consumption",
        "Community total final bill",
        "Community total saved",
        "Fairness index", 
        'Baseline poverty help', 
        'Avoided anual emissions', 
        'Enviromental impact', 
        'TOTAL carbon payback time]

prosumer_kpis_name = [
    
        'Self-Consumption Ratio',    
        'Self-Sufficiency Ratio',       
        'Grid Dependency',      
        'Net P2P Balance in KWh',       
        'P2P Participation in KWh',       
        'Shared energy (G2P-P2G)',        
        'P2P trading index in deficit',        
        'P2P trading index in surplus',      
        'Total final bill',       
        'Saved by entering community',        
        'Anual profit',         
        'Anual profit PV,         
        'Anual profit WT,         
        'Anual profit bateries,         
        'Payback time PV',         
        'Payback time WT',        
        'Payback time BATT',         
        'Bill reduction',         
        'EC gain appropiation',         
        'EC savings appropiation',         
        'Contribution into EC investment',        
        'Avoided anual emissions,       
        'Enviromental impact', 
        'Upfront carbon debt', 
        'TOTAL carbon payback time', 
        'PV carbon payback times', 
        'WT carbon payback time', 
        'BATT carbon payback time'
]
''';

plot_main_effect(df_comm, 'P2P method', 'Community total saved in €', '€')
plot_main_effect(df_comm, 'Batteries', 'Community total saved in €', '€')
plot_main_effect(df_comm, 'Batteries', 'Community total final bill in €', '€')
plot_main_effect(df_pros, 'Batteries', 'Total final bill in € per month', '€', 'P1')
plot_main_effect(df_pros, 'P2P method', 'Anual profit bateries in %', '%', 'P1', '%')


# ### Function that saves all plots:
#The next function can be used to save all plots for:

plot_to_vizualize = ['Main_Effect', 'Difference_CI']
#generate_all_main_effects_plots(df_comm, df_pros, 'Difference_CI')




##########################################################
### PLOTTING: Pareto Plots
##########################################################

#run_all_pareto_plots(df_comm)


##########################################################
### PLOTTING: Sobol Plots
##########################################################


df_clean = df_comm.copy()

df_clean = df_clean.rename(columns={
    "Community total saved in €": "Community_total_saved",
    "Community total final bill in €": "Community_total_final_bill",
    "Avoided anual emissions (Kg CO2 eq)": "Avoided_emissions",
    "P2P method": "P2P_method",
    "BP tariff": "BP_tariff",
    "Self-sufficiency difference between prosumers": "Self_suff_diff",
    "Community Self-Sufficiency": "Community_Self_Sufficiency",
    "Community Grid Dependency": "Community_Grid_Dependency",
    "Community Self-Consumption": "Community_Self_Consumption",
    "Fairness index": "Fairness_index",
    "Baseline poverty help": "Baseline_poverty_help",
    "Enviromental impact": "Environmental_impact",
    "TOTAL carbon payback time in years": "Carbon_payback_years"
})

#run_all_sobol_plots(df_clean)







