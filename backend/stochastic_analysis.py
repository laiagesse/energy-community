##########################################################
##########################################################
############### Stochastic randomization #################
##########################################################
##########################################################




##########################################################
# Importing files
##########################################################



    
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import skew
import scipy.stats as stats
from scipy.stats import norm, beta
import os

from matplotlib.colors import LinearSegmentedColormap
from CoreModules.Data_processing import *
from CoreModules.Visualization_engine import *
from CoreModules.Stochastic_simulator import *
from CoreModules.Digital_Twin_engine import *



##########################################################
# 1. Importing data:
#########################################################



##########################################################
## 1.1 Normalized photovoltaic production in KWh/KW (USR_PV)
##########################################################


#The data was extracted from the EU PVGIS website for Catalonia, exactly from the center of Barcelona at coordinate: 41.384, 2.179
#The data used is the photovoltaic power generated in W for a 1KW installation. This is found in column P.
#As this power is looked by hour, column P gives us Wh/KW. 


folder_name = 'Datasets'
file_pv = 'Photovoltaic_generation_data_EU_PVGIS.csv'
USR_PV = process_pvgis_data(f"{folder_name}/{file_pv}")

# Let's verify our array:
print(f"\nShape of the NumPy array: {USR_PV.shape}")
max_gen = np.max(USR_PV[:, 1])
print(f"Max generation capacity factor: {max_gen:.3f} kW")



##########################################################
### 1.2 Normalized wind production in KWh/KW (USR_WT)
##########################################################

#The data was extracted from the https://www.renewables.ninja/ database. The location is the same as for PV: center of Barcelona, coor. 41.384, 2.179
#The data used is the wind power generated in KW for a 1KW installation. This is found in column electricity.
#As this power is grouped by hour, column 'electricity' gives us the value in KWh/KW. 



file_wt = 'Wind_generation_data_Ninja_database.csv'
USR_WT = process_ninja_wind_data(f"{folder_name}/{file_wt}")

# Let's verify our array:
print(f"\nShape of the NumPy array: {USR_WT.shape}")
max_gen = np.max(USR_WT[:, 1])
print(f"Max generation capacity factor: {max_gen:.3f} kW")


##########################################################
### 1.3 Buying price from the grid "Precio Voluntario para el Pequeño Consumidor" in €/KWh (BP)
##########################################################

#The data was extracted from the European ESIOS (Red Eléctrica de España) data for Spain. 
#As established it was originally obtained in €/MWh, but is already converted to €/KWh.


file_BP = 'Spanish_Buying_price_ESIOS.csv'
BP_array = process_esios_price_data(f"{folder_name}/{file_BP}", price_name="Buying Price")

# Let's verify our array:
print(f"\nShape of the NumPy array: {BP_array.shape}")
print(f"Average Buying Price: {np.mean(BP_array[:, 1]):.4f} €/kWh")



##########################################################
### 1.4 Exporting price into the grid "Mecanismo de compensación simplificada" in €/KWh (SP)
##########################################################


#The data was extracted from the European ESIOS (Red Eléctrica de España) data for Spain. 
#As established it was originally obtained in €/MWh, but is already converted to €/KWh.


file_SP = 'Spanish_Selling_price_ESIOS.csv'
SP_array = process_esios_price_data(f"{folder_name}/{file_SP}", price_name="Selling Price")

# Let's verify our array:
print(f"\nShape of the NumPy array: {SP_array.shape}")
print(f"Average Selling Price: {np.mean(SP_array[:, 1]):.4f} €/kWh")



##########################################################
### 1.5 Consumption per prosumer (KWh)
##########################################################


#The consumption per prosumer was obtained by the "LoadProfileGenerator" by Pflugradt et al (2022).
#See thesis paper for the referencing.
#The prosumer profiles were choosen according to the profiles designed by the UPC model:

## => PROSUMER 1: working couple
## => PROSUMER 2: couple with 3 children
## => PROSUMER 3: couple with 1 child and 2 elderly
## => PROSUMER 4: one retired person
## => PROSUMER 5: a retired couple


C = loading_all_consumptions("Datasets/ConsumptionProsumer", 5)
print(f"Array Shape: {C.shape} with (number_prosumers, time, value)")
print(f"Value=0 is timestamp datatype object and Value=1 is the KWh, datatype object")


##########################################################
## 2. Segmenting data into four seasons
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



##########################################################
## 3. Exploratory Data Analysis
##########################################################

stats_USR_PV = analyze_seasonal_hours(solar_seasons, variable_name="USR_PV", save_images = False)
save_seasonal_stats_to_excel(stats_USR_PV, variable_name="Solar")


#Extracting a specific season into its own variable
winter_df = stats_USR_PV['winter']
spring_df = stats_USR_PV['spring']
summer_df = stats_USR_PV['summer']
autumn_df = stats_USR_PV['autumn']

print("--- Winter Solar Statistics ---")
print(winter_df)

print("\n--- Spring Solar Statistics ---")
print(spring_df)

print("\n--- Summer Solar Statistics ---")
print(summer_df)

print("\n--- Autum Solar Statistics ---")
print(autumn_df)


stats_USR_WT = analyze_seasonal_hours(wind_seasons, variable_name="USR_WT", save_images = False)
save_seasonal_stats_to_excel(stats_USR_WT, variable_name="Wind")


stats_BP = analyze_seasonal_hours(BP_seasons, variable_name="BP", save_images = False)
save_seasonal_stats_to_excel(stats_BP, variable_name="BP")


stats_SP = analyze_seasonal_hours(SP_seasons, variable_name="SP", save_images = False)
save_seasonal_stats_to_excel(stats_SP, variable_name="SP")


stats_C1 = analyze_seasonal_hours(C1_seasons, variable_name="ConsumptionProsumer1", save_images = False)
save_seasonal_stats_to_excel(stats_C1, variable_name="ConsumptionProsumer1")


stats_C2 = analyze_seasonal_hours(C2_seasons, variable_name="ConsumptionProsumer2", save_images = False)
save_seasonal_stats_to_excel(stats_C2, variable_name="ConsumptionProsumer2")


stats_C3 = analyze_seasonal_hours(C3_seasons, variable_name="ConsumptionProsumer3", save_images = False)
save_seasonal_stats_to_excel(stats_C3, variable_name="ConsumptionProsumer3")


stats_C4 = analyze_seasonal_hours(C4_seasons, variable_name="ConsumptionProsumer4", save_images = False)
save_seasonal_stats_to_excel(stats_C4, variable_name="ConsumptionProsumer4")


stats_C5 = analyze_seasonal_hours(C5_seasons, variable_name="ConsumptionProsumer5", save_images = False)
save_seasonal_stats_to_excel(stats_C5, variable_name="ConsumptionProsumer5")



##########################################################
## 4. Finding the correlation matrix between hours
##########################################################


# --- COMPUTING THE CORRELATION MATRIXES ---
# --- Ploting the correlation matrixes between hours is necessary to plot the goodness-of-fit plots.
C1_corr = get_and_save_correlation_matrices(C1_seasons, "C1")
C2_corr = get_and_save_correlation_matrices(C2_seasons, "C2")
C3_corr = get_and_save_correlation_matrices(C2_seasons, "C3")
C4_corr = get_and_save_correlation_matrices(C2_seasons, "C4")
C5_corr = get_and_save_correlation_matrices(C2_seasons, "C5") 
solar_corr = get_and_save_correlation_matrices(solar_seasons, "Solar")
wind_corr = get_and_save_correlation_matrices(wind_seasons, "Wind")
sp_corr = get_and_save_correlation_matrices(SP_seasons, "Selling_Price")
bp_corr = get_and_save_correlation_matrices(BP_seasons, "Buying_Price")




##########################################################
## 5. Beta distribution
##########################################################


# -- The first tried distribution was the Beta distribution
# -- Obtaining the beta parameters:



# Solar and Wind (Strictly 0 to 1)
solar_params = get_mle_beta_parameters(solar_seasons, is_normalized=True)
wind_params = get_mle_beta_parameters(wind_seasons, is_normalized=True)

# Prices and Load (Dynamic boundaries)
sp_params = get_mle_beta_parameters(SP_seasons, is_normalized=False)
bp_params = get_mle_beta_parameters(BP_seasons, is_normalized=False)
C1_params = get_mle_beta_parameters(C1_seasons, is_normalized=False)
C2_params = get_mle_beta_parameters(C2_seasons, is_normalized=False)
C3_params = get_mle_beta_parameters(C3_seasons, is_normalized=False)
C4_params = get_mle_beta_parameters(C4_seasons, is_normalized=False)
C5_params = get_mle_beta_parameters(C5_seasons, is_normalized=False)


print("Merging Statistics and Parameters...")
master_C1  = combine_stat_and_param_dicts(stats_C1, C1_params)
master_C2  = combine_stat_and_param_dicts(stats_C2, C2_params)
master_C3  = combine_stat_and_param_dicts(stats_C3, C3_params)
master_C4  = combine_stat_and_param_dicts(stats_C4, C4_params)
master_C5  = combine_stat_and_param_dicts(stats_C5, C5_params)
master_solar = combine_stat_and_param_dicts(stats_USR_PV, solar_params)
master_wind  = combine_stat_and_param_dicts(stats_USR_WT, wind_params)
master_sp    = combine_stat_and_param_dicts(stats_SP, sp_params)
master_bp    = combine_stat_and_param_dicts(stats_BP, bp_params)

print("All dictionaries successfully merged!")


# Generate artificial days using the beta distribution
# The following plot shows the goodness-of-fit of the Beta distribution. 
# It was decided the the beta distribution is not representative enough, so we analyse the ECDF distribution


plot_goodness_of_fit(C1_seasons, master_C1['summer'], "Prosumer 1 Consumption", 'kWh', season='summer')



##########################################################
## 6. Identifying the ECDF distributions
##########################################################


variables_to_process = [
    ("Consumption_P1", C1_seasons, C1_corr, 'kWh'),
    ("Consumption_P2", C2_seasons, C2_corr, 'kWh'),
    ("Consumption_P3", C3_seasons, C3_corr, 'kWh'),
    ("Consumption_P4", C4_seasons, C4_corr, 'kWh'),
    ("Consumption_P5", C5_seasons, C5_corr, 'kWh'),
    ("Solar", solar_seasons, solar_corr, 'kWh'),
    ("Wind", wind_seasons, wind_corr, 'kWh'),
    ("Selling_Price", SP_seasons, sp_corr, '€/kWh'),
    ("Buying_Price", BP_seasons, bp_corr, '€/kWh')
]



#run_all_ecdf_validations(variables_to_process, n_days=1000)



##########################################################
## 7. Correlation matrix between all input features
##########################################################

# In order to be able to do the NORTA system (Normal-to-Anything) we need the correlation matrix between all inputs.


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

grand_correlation_matrices = build_grand_correlation_matrices(master_data_map, True)


##########################################################
## 8. Stochastic input generation  of all variables
##########################################################



final_simulation_data = generate_3D_simulation_tensors(
    n_days=1000, 
    master_data_map=master_data_map, 
    grand_corr_matrices_dict=grand_correlation_matrices
)

print("\nSimulation Complete!")
print("Checking Winter Solar array shape:", final_simulation_data['winter'][1].shape) # [1] is Solar. Shape will be (1000, 24)
print()
print(final_simulation_data['winter'][1])



