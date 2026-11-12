#!/usr/bin/env python
# coding: utf-8

# In[1]:


##########################################################
##########################################################
########### Stochastic randomization #####################
##########################################################
##########################################################


# In[2]:


# doe_engine.py


# In[3]:


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


# In[4]:


##########################################################
## Importing the Design of Experiment (DoE) excel
##########################################################


# In[5]:


def import_doe_matrix(filepath):
    """
    Imports the DoE matrix excel file into a pandas DataFrame.
    """
    try:
        # Load the file
        df_doe = pd.read_excel(filepath)
        df_doe.columns = df_doe.columns.str.strip()
        df_doe.set_index('Run Order', inplace=True)
        
        print(f"DoE matrix successfully loaded. Shape: {df_doe.shape}")
        return df_doe
        
    except FileNotFoundError:
        print(f"Error: Could not find the file at {filepath}.")
        return None



# In[6]:


##########################################################
## Montecarlo
##########################################################


# In[7]:


def analyse_montecarlo_no_plots(all_prosumer, all_community, all_sum_analysis,
                       number_iterations, n_days, season, P2P_method):

    save_folder = "Std montecarlo"
    run_folder_name = f"{P2P_method}_{season}_{number_iterations}it_of_{n_days}days"

#stat analysis community kpis
    
    df_comm = pd.DataFrame(all_community)

    ordered_cols = [
        "Community Self-Sufficiency", "Self-sufficiency difference between prosumers",
        "Community Grid Dependency",
        "Community Self-Consumption",
        "Community total final bill in €",
        "Community total saved in €",
        "Fairness index", 'Baseline poverty help', 
        'Avoided anual emissions (Kg CO2 eq)', 'Enviromental impact', 
        'TOTAL carbon payback time in years']
    
    df_comm = df_comm[ordered_cols]

    # Compute stats
    stats_comm = pd.DataFrame(index=df_comm.columns)
    stats_comm["mean"] = df_comm.mean()
    stats_comm["median"] = df_comm.median()
    stats_comm["min"] = df_comm.min()
    stats_comm["max"] = df_comm.max()
    stats_comm["std"] = df_comm.std()
    stats_comm["Q1"] = df_comm.quantile(0.25)
    stats_comm["Q3"] = df_comm.quantile(0.75)
    stats_comm["CV"] = stats_comm["std"] / stats_comm["mean"]

    CI_low = []
    CI_high = []
    for col in df_comm.columns:
        values = df_comm[col].values
        mean = np.nanmean(values)
        std = np.nanstd(values, ddof=1)
        n = len(values)
        margin = 1.96 * std / np.sqrt(n)
        CI_low.append(mean - margin)
        CI_high.append(mean + margin)

    stats_comm["CI"] = 1.96 * stats_comm["std"] / np.sqrt(n)
    stats_comm["CI_low"] = CI_low
    stats_comm["CI_high"] = CI_high

    # REORDERING THE COLUMNS 
    stats_comm = stats_comm[["mean", "CI", "median", "min", "max", "std", "Q1", "Q3", "CV", "CI_low", "CI_high"]]

    #Prosumer stat analysis
    kpi_array = np.stack([df.values for df in all_prosumer])
    num_iter, num_prosumers, num_kpis = kpi_array.shape

    prosumer_labels = all_prosumer[0].index.tolist()
    kpi_names = all_prosumer[0].columns.tolist()

    stats_prosumer = pd.DataFrame(
        index=pd.MultiIndex.from_product([prosumer_labels, kpi_names], names=["Prosumer", "KPI"]),
        columns=["mean", "CI", "median", "min", "max", "std", "Q1", "Q3", "CV", "CI_low", "CI_high"]
    )

    for p_idx, prosumer in enumerate(prosumer_labels):
        for k_idx, kpi in enumerate(kpi_names):
            values = kpi_array[:, p_idx, k_idx]

            mean = np.nanmean(values)
            std = np.nanstd(values, ddof=1)
            n = len(values)
            margin = 1.96 * std / np.sqrt(n)

            stats_prosumer.loc[(prosumer, kpi), "mean"] = mean
            stats_prosumer.loc[(prosumer, kpi), "CI"] = margin
            stats_prosumer.loc[(prosumer, kpi), "median"] = np.nanmedian(values)
            stats_prosumer.loc[(prosumer, kpi), "min"] = np.nanmin(values)
            stats_prosumer.loc[(prosumer, kpi), "max"] = np.nanmax(values)
            stats_prosumer.loc[(prosumer, kpi), "std"] = std
            stats_prosumer.loc[(prosumer, kpi), "Q1"] = np.nanpercentile(values, 25)
            stats_prosumer.loc[(prosumer, kpi), "Q3"] = np.nanpercentile(values, 75)
            stats_prosumer.loc[(prosumer, kpi), "CV"] = std / mean if mean != 0 else np.nan
            stats_prosumer.loc[(prosumer, kpi), "CI_low"] = mean - margin
            stats_prosumer.loc[(prosumer, kpi), "CI_high"] = mean + margin

    return stats_comm,stats_prosumer, prosumer_labels, kpi_names


# In[8]:


def montecarlo(number_iterations, n_days, prosumer_based_data, df_EC_parameters, master_data_map, season, P2P_method, seed):
    print(f'Starting Monte Carlo analysis...')
    all_prosumer = []
    all_community = []
    all_sum_analysis = []

    num_prosumers = prosumer_based_data.shape[1]
    time_periods = n_days * 24   # 720 hours per iteration
    
    ## Creating the coorelation matrices
    grand_corr_matrices_dict =  build_grand_correlation_matrices(master_data_map);
    
    if seed is not None:
        np.random.seed(seed)
        
    for rep in range(number_iterations):
        final_simulation_data = generate_3D_simulation_tensors(n_days, master_data_map, grand_corr_matrices_dict);
        
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
        #shared generation
        E_pv_pr = solar_m * df_EC_parameters.loc['pw_pv_pr', 'Value']
        E_wt_pr = wind_m * df_EC_parameters.loc['pw_wt_pr', 'Value']
        

        # 4. Run the simulation
        _, results_data, time_based_data0, _, flow_P2P_0 = twin(time_based_data, prosumer_based_data, df_EC_parameters,
                                                                E_pv_pr, E_wt_pr, P2P_method)

        # 5. Compute KPIs
        kpis, community, economic_kpis, social_kpis, enviromental_kpis, sum_analysis_data = compute_prosumer_kpis(prosumer_based_data, results_data, 
                                                                                  flow_P2P_0,time_based_data0, df_EC_parameters)

        # 7. Store KPIs for this iteration
        combined = pd.concat([kpis, economic_kpis, social_kpis, enviromental_kpis], axis=1)
        all_prosumer.append(combined)
        all_community.append(community)
        all_sum_analysis.append(sum_analysis_data)
        print(f'Finished iteration {rep+1}')
    return all_prosumer, all_community, all_sum_analysis


# In[9]:


##########################################################
## Full factorial analysis
##########################################################


# In[10]:


def export_doe_results_to_excel(doe_matrix, community_stats_list, prosumer_stats_list, save_name="Master_DoE_Results.xlsx"):
    print("Formatting DoE results with Multi-Level Excel Headers...")
    
    # We format the DoE Matrix Inputs to have a "Experiment Settings" top header
    df_doe_reset = doe_matrix.reset_index()
    df_doe_inputs = df_doe_reset.copy()
    # This creates the 2-level header: Top level is 'Experiment Settings', Bottom is 'Season', 'Batteries', etc.
    df_doe_inputs.columns = pd.MultiIndex.from_product([['Experiment Settings'], df_doe_inputs.columns])

    # Formating the community sheet
    comm_data = {} 
    
    for stats_df in community_stats_list:
        for kpi_name in stats_df.index:
            # We create a tuple key: (Top Header, Bottom Header)
            col_key = ("Community KPIs", f"{kpi_name}")
            
            if col_key not in comm_data:
                comm_data[col_key] = []
            comm_data[col_key].append(stats_df.at[kpi_name, 'mean'])
            
    df_comm_stats = pd.DataFrame(comm_data)
    df_final_community = pd.concat([df_doe_inputs, df_comm_stats], axis=1)

    # Formating the prosumer sheet
    pros_data = {}
    
    for stats_df in prosumer_stats_list:
        # stats_df has a MultiIndex: (Prosumer_Name, KPI_Name)
        for (prosumer, kpi_name) in stats_df.index:
            # We create a tuple key: (Prosumer 1, Mean - Fairness)
            col_key = (prosumer, f"{kpi_name}")
            
            if col_key not in pros_data:
                pros_data[col_key] = []
            pros_data[col_key].append(stats_df.at[(prosumer, kpi_name), 'mean'])
            
    df_pros_stats = pd.DataFrame(pros_data)
    df_final_prosumer = pd.concat([df_doe_inputs, df_pros_stats], axis=1)

    # Saving to excel
    today = datetime.now().strftime("%Y-%m-%d")
    save_folder = f"Results/Results_DOE/{today}_Experiment/MasterDoE"
    os.makedirs(save_folder, exist_ok=True)
    file_path = os.path.join(save_folder, save_name)
    
    with pd.ExcelWriter(file_path) as writer:
        # We removed index=False so Pandas doesn't crash!
        df_final_community.to_excel(writer, sheet_name="Community DoE")
        df_final_prosumer.to_excel(writer, sheet_name="Prosumer DoE")
        
    print(f"Success! Master DoE Excel file saved to: {file_path}")
    return df_final_community, df_final_prosumer


# In[11]:


def fullfactorial(doe_matrix, number_iterations, n_days, prosumer_based_data, df_EC_parameters, master_data_map, seed):
    print(f'Starting Full factorial experiment...')

    ## Creating the coorelation matrices & needed variables
    grand_corr_matrices_dict =  build_grand_correlation_matrices(master_data_map);
    num_prosumers = prosumer_based_data.shape[1]
    seasons = ['winter', 'spring', 'summer', 'autumn']
    time_periods = n_days * 24   

    ## Saving variables
    time_based_data_list = []
    E_pv_pr_list = []
    E_wt_pr_list = []
    community_stadistics_per_experiment = []
    prosumer_stadistics_per_experiment = []

    # Mapping dictionary to translate Excel names to your Python names
    p2p_mapping = {
        'Market': 'P2P_market',
        'One price': 'P2P_one_price', 
        'Social': 'P2P_social',
        'Enviromental': 'P2P_enviromental'
    }
    
    np.random.seed(seed)

    ### We do one first loop to create the randomized data
    for rep in range(number_iterations):
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
            #shared generation
            E_pv_pr = solar_m * df_EC_parameters.loc['pw_pv_pr', 'Value']
            E_wt_pr = wind_m * df_EC_parameters.loc['pw_wt_pr', 'Value']

            time_based_data_dictionary[season] = time_based_data
            E_pv_pr_dictionary[season] = E_pv_pr
            E_wt_pr_dictionary[season] = E_wt_pr

        # We save the dictionaries into lists for each iteration.
        time_based_data_list.append(time_based_data_dictionary)
        E_pv_pr_list.append(E_pv_pr_dictionary)
        E_wt_pr_list.append(E_wt_pr_dictionary)

    
    ### STARTING THE EXPERIMENT LOOP
    for experiment_number in doe_matrix.index:
        start_time = time.time() # Start stopwatch
        current_row = doe_matrix.loc[experiment_number]

        # Current conditions
        season = current_row['Season'].lower()
        raw_p2p = current_row['P2P method']
        P2P_method = p2p_mapping[raw_p2p]
        tariff = current_row['BP tariff']
        battery = current_row['Batteries']
        consumption = current_row['Consumption']

        print(f"\n--- Running Experiment {experiment_number}/576 ---")
        print(f"Config: {season}, {P2P_method}, Tariff: {tariff}, Bat: {battery}, Cons: {consumption}")

        # TARIFF MULTIPLIER (Symmetrical ±25%)
        if tariff == 'Low':
            tariff_mult = 0.75  
        elif tariff == 'High':
            tariff_mult = 1.25  
        else: # Baseline
            tariff_mult = 1.0   

        # CONSUMPTION MULTIPLIER (Symmetrical ±20%)
        if consumption == 'Low':
            cons_mult = 0.80  
        elif consumption == 'High':
            cons_mult = 1.20  
        else: # Baseline
            cons_mult = 1.0   
 
        # BATTERY ASSIGNMENT (Symmetrical Adoption)
        current_prosumer_data = prosumer_based_data.copy()
        
        if battery == 'Baseline':
            current_prosumer_data[6, :] = [0.0, 0.0, 0.0, 0.0, 0.0]
        elif battery == 'Low':
            current_prosumer_data[6, :] = [2.336, 0.0, 0.0, 0.0, 0.0]
        elif battery == 'Medium':
            current_prosumer_data[6, :] = [2.336, 0.0, 2.336, 0.0, 2.336]
        elif battery == 'High':
            current_prosumer_data[6, :] = [2.336, 2.336, 2.336, 2.336, 2.336]

        # STARTING MONTECARLO
        # print(f'Starting Monte Carlo analysis...') # Optional: mute this to keep console clean
        try:
            all_prosumer = []
            all_community = []
            all_sum_analysis = []
        
            # Starting iteration loop
            for rep in range(number_iterations):
                # Get the right data
                time_based_data = time_based_data_list[rep][season]
                E_pv_pr = E_pv_pr_list[rep][season]
                E_wt_pr = E_wt_pr_list[rep][season]
                current_time_based_data = time_based_data.copy()
    
                # FIXED: Multiply by cons_mult, not the string word!
                current_time_based_data[:,2,:] = current_time_based_data[:,2,:] * tariff_mult
                current_time_based_data[:,0,:] = current_time_based_data[:,0,:] * cons_mult 
                
                # Run the simulation
                _, results_data, time_based_data_results, _, flow_P2P = twin(
                    current_time_based_data, current_prosumer_data, df_EC_parameters, E_pv_pr, E_wt_pr, P2P_method)
        
                # Compute KPIs
                kpis, community, economic_kpis, social_kpis, enviromental_kpis, sum_analysis_data = compute_prosumer_kpis(
                    current_prosumer_data, results_data, flow_P2P, current_time_based_data, df_EC_parameters)
        
                # Store KPIs for this iteration
                combined = pd.concat([kpis, economic_kpis, social_kpis, enviromental_kpis], axis=1)
                all_prosumer.append(combined)
                all_community.append(community)
                all_sum_analysis.append(sum_analysis_data)
            

            stats_comm, stats_prosumer, prosumer_labels, kpi_names = analyse_montecarlo_no_plots(
                all_prosumer, all_community, all_sum_analysis, number_iterations, n_days, season, P2P_method)
        
        
            community_stadistics_per_experiment.append(stats_comm)
            prosumer_stadistics_per_experiment.append(stats_prosumer)

            today = datetime.now().strftime("%Y-%m-%d")

            checkpoint_folder = f"Results/Results_DOE/{today}_Experiment/DOE_Individual_Experiments"
            os.makedirs(checkpoint_folder, exist_ok=True) # Creates the folder safely
        
            # Create a clean, identifiable file name
            file_name = f"Exp_{experiment_number}_{season}_{P2P_method}.xlsx"
            file_path = os.path.join(checkpoint_folder, file_name)
        
            # Save the two dataframes into one Excel file
            with pd.ExcelWriter(file_path) as writer:
                stats_comm.to_excel(writer, sheet_name="Community KPIs")
                stats_prosumer.to_excel(writer, sheet_name="Prosumer KPIs")
            
            print(f"--> Saved checkpoint: {file_name}")

        except Exception as e:
            print(f"\nFATAL ERROR IN EXPERIMENT {experiment_number}: {e}")
            print("Stopping the massive loop early, but saving all completed experiments safely!")
            
            # Slice the DoE matrix so it perfectly matches the experiments that actually finished
            doe_matrix = doe_matrix.iloc[:len(community_stadistics_per_experiment)]
            break # This exits the 576-experiment loop immediately!

        # STOPING THE STOPWATCH AND ESTIMATING TIME
        end_time = time.time()
        duration_minutes = (end_time - start_time) / 60
        runs_completed = list(doe_matrix.index).index(experiment_number) + 1
        runs_left = len(doe_matrix) - runs_completed
        est_hours = (runs_left * duration_minutes) / 60
        
        print(f"--> Run time: {duration_minutes:.2f} mins. Estimated time remaining: {est_hours:.2f} hours.\n")

    df_master_comm, df_master_pros = export_doe_results_to_excel(
        doe_matrix, community_stadistics_per_experiment, prosumer_stadistics_per_experiment
    )
    
    print("\n--- Full Factorial DoE Complete! ---")
    return df_master_comm, df_master_pros


# In[12]:


def load_doe_results_from_excel(file_path= "Results/Results_DOE/Original_Experiment/MasterDoE/Master_DOE_Results.xlsx"):
    print(f"Loading DoE results from {file_path}...")
    
    df_master_comm = pd.read_excel(
            file_path, 
            sheet_name="Community DoE", 
            header=[0, 1], 
            index_col=0
    )
    df_master_comm.columns = df_master_comm.columns.get_level_values(1)
    df_master_comm.columns = df_master_comm.columns.str.replace('Mean - ', '')
    
    print("Community Data loaded successfully.")

        
    df_master_pros = pd.read_excel(
        file_path, 
        sheet_name="Prosumer DoE", 
        header=[0, 1], 
        index_col=0
    )

    clean_columns = []
    for top_level, bottom_level in df_master_pros.columns:
        new_bottom = bottom_level.replace('Mean - ', '')
        clean_columns.append((top_level, new_bottom))
    df_master_pros.columns = pd.MultiIndex.from_tuples(clean_columns)

    print("Prosumer Data loaded successfully.")
        
    return df_master_comm, df_master_pros


# In[13]:


##########################################################
# Obtaining the results for the KPi and their confidence intervals for the baseline configurations
##########################################################


# In[14]:


def build_kpi_table_with_ci(doe_matrix, p2p_method, source_name, target_kpis, is_community=True, ci_col_name='CI', checkpoint_folder="Results/Results_DOE/Original_Experiment/DOE_Individual_Experiments"):
    
    decimal_config = {
    2: ['Community total saved in €', 'Avoided anual emissions (Kg CO2 eq)', 
        'Saved by entering community € per month', 'Anual profit in %'],
    4: ['Community Self-Sufficiency', 'Community Grid Dependency', 
        'Fairness index', 'EC savings appropiation']
    }
    
    kpi_decimals = {kpi: dec for dec, kpis in decimal_config.items() for kpi in kpis}


    
    mask = (
        (doe_matrix['P2P method'] == p2p_method) &
        (doe_matrix['BP tariff'] == 'Baseline') &
        (doe_matrix['Batteries'] == 'Baseline') &
        (doe_matrix['Consumption'] == 'Baseline')
    )
    baseline_exps = doe_matrix[mask]
    
    p2p_mapping = {
        'Market': 'P2P_market',
        'One price': 'P2P_one_price', 
        'Social': 'P2P_social',
        'Enviromental': 'P2P_enviromental'
    }
    mapped_p2p = p2p_mapping[p2p_method]
    
    all_data = []
    for exp_num, row in baseline_exps.iterrows():
        season = row['Season'].lower()
        file_name = f"Exp_{exp_num}_{season}_{mapped_p2p}.xlsx"
        file_path = os.path.join(checkpoint_folder, file_name)
        
        if not os.path.exists(file_path):
            print(f"Warning: File not found -> {file_name}")
            continue
        sheet = "Community KPIs" if is_community else "Prosumer KPIs"
        
        if is_community:
            df_stats = pd.read_excel(file_path, sheet_name=sheet, index_col=0)
            
            row_data = {'Source': source_name, 'Season': season.capitalize()}
            for kpi in target_kpis:
                try:
                    mean_val = df_stats.loc[kpi, 'mean']
                    ci_val = df_stats.loc[kpi, ci_col_name]
                    dec = kpi_decimals.get(kpi, 4)
                    row_data[kpi] = f"{mean_val:.{dec}f} ± {ci_val:.{dec}f}"
                except KeyError:
                    row_data[kpi] = "N/A"
            all_data.append(row_data)
            
        else:
            df_stats = pd.read_excel(file_path, sheet_name=sheet, index_col=[0, 1])
            
            prosumers = [f"P{i}" for i in range(1, 6)]
            for p in prosumers:
                p_row = {'Source': source_name, 'Season': season.capitalize(), 'Prosumer': p}
                for kpi in target_kpis:
                    try:
                        mean_val = df_stats.loc[(p, kpi), 'mean']
                        ci_val = df_stats.loc[(p, kpi), ci_col_name]
                        dec = kpi_decimals.get(kpi, 4)
                        p_row[kpi] = f"{mean_val:.{dec}f} ± {ci_val:.{dec}f}"
                    except KeyError:
                        p_row[kpi] = "N/A"
                all_data.append(p_row)

    df_final = pd.DataFrame(all_data)
    
    if not df_final.empty:
        if is_community:
            return (df_final
                .set_index(['Source', 'Season'])
                .stack()
                .unstack('Season')
                .rename_axis(index=['Source', 'KPI'])
               )
        else:
            return (df_final
                .set_index(['Source', 'Season', 'Prosumer'])
                .stack()
                .unstack('Season')
                .rename_axis(index=['Source', 'Prosumer', 'KPI'])
                .reorder_levels(['Source', 'KPI', 'Prosumer'])
                .sort_index()
               )
            
    return pd.DataFrame()


# In[15]:


##########################################################
## SENSITIVITY ANALYSIS: MAIN EFFECTS PLOTS
##########################################################


# In[53]:


def plot_main_effect(df, factor_col, kpi_col, kpi_unit, prosumer=None, save_image = False):
    
    if prosumer is None:
        print(f"Generating Main Effects Plot for: {factor_col} vs {kpi_col}")
    
        # Group by the factor (e.g., P2P method) and calculate the mean of the KPI
        effect_means = df.groupby(factor_col)[kpi_col].mean()
    
        # Calculate the Grand Mean (the average of every single experiment)
        grand_mean = df[kpi_col].mean()
        
        folder = f'Community_KPIs'
        name_image = f'LINEplot_FACTOR_{factor_col}_KPI_{kpi_col}'
     
    else:
        print(f"Generating Main Effects Plot for: {factor_col} vs {kpi_col} for {prosumer}")
    
        # Group by the factor (e.g., P2P method) and calculate the mean of the KPI
        factor_data = df[('Experiment Settings', factor_col)]
        kpi_data = df[(prosumer, kpi_col)]
        effect_means = kpi_data.groupby(factor_data).mean()
    
        # Calculate the Grand Mean (the average of every single experiment)
        grand_mean = kpi_data.mean()

        folder = f'Prosumer_KPIs/{prosumer}'
        name_image = f'LINEplot_FACTOR_{factor_col}_KPI_{kpi_col}_{prosumer}'

    # Defining an order for the factors:

    if factor_col == 'Batteries':
        order=['Baseline', 'Low', 'Medium', 'High']  
    elif factor_col == 'Season':
        order=['winter', 'spring', 'summer', 'autumn']
    elif factor_col == 'P2P method':
        order=['One price', 'Market', 'Social', 'Enviromental']
    elif factor_col == 'BP tariff':
        order=['Low', 'Baseline', 'High']
    elif factor_col == 'Consumption':
        order=['Low', 'Baseline', 'High']
    else:
        order= None

    if order is not None:
       effect_means = effect_means.reindex(order)

    # Seting up the plot
    plt.figure(figsize=(8, 5))
    
    # Plot the Main Effect line (with nice big dots for the actual values)
    plt.plot(
        effect_means.index, 
        effect_means.values, 
        marker='o', 
        markersize=10, 
        linewidth=2.5, 
        color='#1f77b4', 
        label=f'Mean {kpi_col}'
    )
    
    # Plot the Grand Mean reference line
    plt.axhline(
        y=grand_mean, 
        color='red', 
        linestyle='--', 
        linewidth=1.5, 
        label=f'Grand Mean ({grand_mean:.2f} {kpi_unit})'
    )
    
    # Formating the chart 
    plt.title(f'Main Effect of {factor_col} on\n{kpi_col}', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel(factor_col, fontsize=12, fontweight='bold')
    plt.ylabel(f'Average {kpi_col}', fontsize=12, fontweight='bold')
    
    # Adding a grid for easier reading and a legend
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend(loc='best')

    y_min, y_max = plt.ylim()
    plt.ylim(y_min - (y_max-y_min)*0.1, y_max + (y_max-y_min)*0.1)

    plt.tight_layout()
    if save_image:
        folder_path = f'Results/Results_DOE/Original_Experiment/Plots/Line_Plots/{folder}'
        os.makedirs(make_long_path(folder_path), exist_ok=True)
    
        safe_name_image = name_image.replace('/', '_').replace('\\', '_').replace(' ', '_')
        save_path = make_long_path(f'{folder_path}/{safe_name_image}.png')
    
        plt.savefig(save_path, dpi=200, bbox_inches='tight')
        plt.close() 
    else:
        plt.show()


# In[55]:


def plot_difference_ci(df, factor_col, kpi_col, kpi_unit, prosumers=None, save_image=False, reference_level='Baseline'):
    """
    Generates a Zero-Line Confidence Interval plot.
    If 'prosumers' is a list, it groups all prosumers side-by-side for each factor level.
    """
    
    # --- KPI NAME MAPPING ---
    community_kpis = [
        "Community Self-Sufficiency", "Self-sufficiency difference between prosumers",
        "Community Grid Dependency", "Community Self-Consumption",
        "Community total final bill in €", "Community total saved in €",
        "Fairness index", 'Baseline poverty help', 'Avoided anual emissions (Kg CO2 eq)', 
        'Enviromental impact', 'TOTAL carbon payback time in years'
    ]
    community_kpis_name = [
        "Community Self-Sufficiency", "Self-sufficiency difference between prosumers",
        "Community Grid Dependency", "Community Self-Consumption",
        "Community total final bill", "Community total saved",
        "Fairness index", 'Baseline poverty help', 'Avoided anual emissions', 
        'Enviromental impact', 'TOTAL carbon payback time'
    ]
    
    prosumer_kpis = [
        'Self-Consumption Ratio', 'Self-Sufficiency Ratio', 'Grid Dependency', 
        'Net P2P Balance in KWh per simulated period', 'P2P Participation in KWh per simulated period', 
        'Shared energy in KWH (G2P-P2G) per simulated period', 'P2P trading index in deficit', 
        'P2P trading index in surplus', 'Total final bill in € per month', 
        'Saved by entering community € per month', 'Anual profit in %', 
        'Anual profit PV in %', 'Anual profit WT in %', 'Anual profit bateries in %', 
        'Payback time PV', 'Payback time WT', 'Payback time BATT', 'Bill reduction in %', 
        'EC gain appropiation', 'EC savings appropiation', 'Contribution into EC investment', 
        'Avoided anual emissions (Kg CO2 eq)', 'Enviromental impact', 'Upfront carbon debt (Kg CO2 eq)', 
        'TOTAL carbon payback time in years', 'PV carbon payback time in years', 
        'WT carbon payback time in years', 'BATT carbon payback time in years'
    ]
    prosumer_kpis_name = [
        'Self-Consumption Ratio', 'Self-Sufficiency Ratio', 'Grid Dependency', 
        'Net P2P Balance in KWh', 'P2P Participation in KWh', 
        'Shared energy (G2P-P2G)', 'P2P trading index in deficit', 
        'P2P trading index in surplus', 'Total final bill', 
        'Saved by entering community', 'Anual profit', 
        'Anual profit PV', 'Anual profit WT', 'Anual profit bateries', 
        'Payback time PV', 'Payback time WT', 'Payback time BATT', 'Bill reduction', 
        'EC gain appropiation', 'EC savings appropiation', 'Contribution into EC investment', 
        'Avoided anual emissions', 'Enviromental impact', 'Upfront carbon debt', 
        'TOTAL carbon payback time', 'PV carbon payback times', 
        'WT carbon payback time', 'BATT carbon payback time'
    ]

    # Create a dictionary to map the original column name to the desired short name
    kpi_map = dict(zip(community_kpis + prosumer_kpis, community_kpis_name + prosumer_kpis_name))
    
    # Get the display name (if it doesn't exist in the list, it defaults to the original name)
    kpi_display_name = kpi_map.get(kpi_col, kpi_col)
    
    # --- SETUP FOLDERS AND LABELS ---
    if prosumers is None:
        print(f"Generating CI Plot for: {factor_col} vs {kpi_display_name} (Community)")
        folder = 'Community_KPIs'
        name_image = f'CI_plot_FACTOR_{factor_col}_KPI_{kpi_display_name}'
    elif isinstance(prosumers, list):
        print(f"Generating Grouped CI Plot for: {factor_col} vs {kpi_display_name} (All Prosumers)")
        folder = 'Prosumer_KPIs/Grouped_CI_Plots'
        name_image = f'CI_plot_FACTOR_{factor_col}_KPI_{kpi_display_name}_AllProsumers'
    else:
        print(f"Generating CI Plot for: {factor_col} vs {kpi_display_name} for {prosumers}")
        folder = f'Prosumer_KPIs/{prosumers}'
        name_image = f'CI_plot_FACTOR_{factor_col}_KPI_{kpi_display_name}_{prosumers}'

    # --- DEFINING CATEGORY ORDER & BASELINE ---
    if factor_col == 'Batteries':
        order=['Baseline', 'Low', 'Medium', 'High']  
    elif factor_col == 'Season':
        order=['Winter', 'Spring', 'Summer', 'Autumn']
        reference_level = 'Spring'
    elif factor_col == 'P2P method':
        order=['One price', 'Market', 'Social', 'Enviromental']
        reference_level = 'Market'
    elif factor_col == 'BP tariff':
        order=['Low', 'Baseline', 'High']
    elif factor_col == 'Consumption':
        order=['Low', 'Baseline', 'High']
    else:
        order = None # Will be determined dynamically if not in this list

    # --- STATISTICAL MATH SETUP (Bonferroni) ---
    alpha_total = 0.05
    # We compare everything EXCEPT the baseline to the baseline
    num_comparisons = len(order) - 1 if order else 3 
    alpha_adjusted = alpha_total / num_comparisons
    z_score = stats.norm.ppf(1 - alpha_adjusted / 2)

    # Helper function to calculate differences and margins for a single data series
    def calculate_series_stats(group_stats, ref_level, cat_order):
        diff_means, ci_margins = [], []
        
        try:
            base_mean = group_stats.loc[ref_level, 'mean']
            base_std = group_stats.loc[ref_level, 'std']
            base_n = group_stats.loc[ref_level, 'count']
        except KeyError:
            print(f"  -> Warning: Reference '{ref_level}' not found. Returning zeros.")
            return [0]*len(cat_order), [0]*len(cat_order)

        for cat in cat_order:
            if cat == ref_level:
                diff_means.append(0.0)
                ci_margins.append(0.0)
            else:
                try:
                    cat_mean = group_stats.loc[cat, 'mean']
                    cat_std = group_stats.loc[cat, 'std']
                    cat_n = group_stats.loc[cat, 'count']
                    
                    diff = cat_mean - base_mean
                    se_diff = np.sqrt((cat_std**2 / cat_n) + (base_std**2 / base_n))
                    diff_means.append(diff)
                    ci_margins.append(z_score * se_diff)
                except KeyError:
                    diff_means.append(0.0)
                    ci_margins.append(0.0)
                    
        return diff_means, ci_margins

    # --- PLOTTING ---
    plt.figure(figsize=(10, 6)) # Slightly wider to fit all the grouped bars
    x_positions = np.arange(len(order))
    
    # 1. COMMUNITY PLOT (Single Line)
    # IMPORTANTE: Aquí se sigue usando kpi_col original para filtrar el DataFrame
    if prosumers is None:
        group_stats = df.groupby(factor_col)[kpi_col].agg(['mean', 'std', 'count']).reindex(order)
        diffs, margins = calculate_series_stats(group_stats, reference_level, order)
        
        plt.errorbar(x_positions, diffs, yerr=margins, fmt='o', markersize=10, 
                     linewidth=2.5, capsize=8, capthick=2, color='#1f77b4', label='Community CI')

    # 2. GROUPED PROSUMERS PLOT (Multiple Lines)
    elif isinstance(prosumers, list):
        width = 0.7 # Total width allocated per category
        offsets = np.linspace(-width/2, width/2, len(prosumers))
        colors = plt.cm.tab10.colors # Use distinct default colors
        
        for i, p in enumerate(prosumers):
            factor_data = df[('Experiment Settings', factor_col)]
            kpi_data = df[(p, kpi_col)] # Seguimos usando kpi_col
            group_stats = kpi_data.groupby(factor_data).agg(['mean', 'std', 'count']).reindex(order)
            
            diffs, margins = calculate_series_stats(group_stats, reference_level, order)
            
            # Plot with offset
            plt.errorbar(x_positions + offsets[i], diffs, yerr=margins, fmt='o', 
                         markersize=6, linewidth=1.5, capsize=4, capthick=1.5, 
                         color=colors[i % len(colors)], label=p)

    # 3. SINGLE PROSUMER PLOT (Fallback)
    else:
        factor_data = df[('Experiment Settings', factor_col)]
        kpi_data = df[(prosumers, kpi_col)] # Seguimos usando kpi_col
        group_stats = kpi_data.groupby(factor_data).agg(['mean', 'std', 'count']).reindex(order)
        diffs, margins = calculate_series_stats(group_stats, reference_level, order)
        plt.errorbar(x_positions, diffs, yerr=margins, fmt='o', markersize=10, 
                     linewidth=2.5, capsize=8, capthick=2, label=f'{prosumers} CI')

    # --- FORMATTING ---
    # Apply category labels to the X-axis positions
    plt.xticks(x_positions, order)
    
    # Draw Zero Line
    plt.axhline(y=0, color='red', linestyle='--', linewidth=1.5, label='Zero Difference')
    
    # IMPORTANTE: Aquí usamos el nombre corto (kpi_display_name)
    plt.title(f'Statistical Difference from {reference_level} {factor_col}\n{kpi_display_name}', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel(factor_col, fontsize=12, fontweight='bold')
    plt.ylabel(f'Difference in {kpi_display_name} ({kpi_unit})', fontsize=12, fontweight='bold')
    
    plt.grid(True, linestyle=':', alpha=0.7)
    
    # Legend handling: Put it outside if it's grouped so it doesn't cover data
    if isinstance(prosumers, list):
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    else:
        plt.legend(loc='best')

    y_min, y_max = plt.ylim()
    plt.ylim(y_min - (y_max-y_min)*0.1, y_max + (y_max-y_min)*0.1)

    plt.tight_layout()
    if save_image:
        folder_path = f'Results/Results_DOE/Original_Experiment/Plots/CI_plots/{folder}'
        os.makedirs(make_long_path(folder_path), exist_ok=True)
    
        safe_name_image = name_image.replace('/', '_').replace('\\', '_').replace(' ', '_')
        save_path = make_long_path(f'{folder_path}/{safe_name_image}.png')
    
        plt.savefig(save_path, dpi=200, bbox_inches='tight')
        plt.close() 
    else:
        plt.show()


# In[18]:


# Function that saves all plots:


# In[19]:


def get_kpi_unit(kpi_name):
    """Parses the KPI string to determine the correct unit for the plot labels."""
    kpi_lower = kpi_name.lower()
    
    # Financial metrics (€)
    if '€' in kpi_lower or 'saved' in kpi_lower:
        return '€/month'
        
    # Percentages, Ratios, and Indexes (%)
    elif any(word in kpi_lower for word in ['%', 'profit', 'reduction']):
        return '%' # Change to '' if you prefer ratios to have no unit
        
    # Energy metrics (kWh)
    elif 'kwh' in kpi_lower or 'energy' in kpi_lower or 'balance' in kpi_lower or 'participation' in kpi_lower:
        return 'kWh/month'
        
    # Environmental metrics (Kg CO2 eq)
    elif 'co2' in kpi_lower or 'emissions' in kpi_lower or 'debt' in kpi_lower or 'impact' in kpi_lower:
        return 'Kg CO2 eq'
        
    # Time metrics (years)
    elif 'years' in kpi_lower or 'payback' in kpi_lower:
        return 'years'
        
    else:
        return ''


# In[20]:


def make_long_path(path):
    """Prefix path to support >260 chars on Windows. No admin rights needed."""
    if sys.platform == 'win32' and not path.startswith('\\\\?\\'):
        return '\\\\?\\' + os.path.abspath(path)
    return path


# In[21]:


def generate_all_main_effects_plots(df_comm, df_pros, plot_to_vizualize):
    print(f"Starting plotting: {plot_to_vizualize}...")

    factors_list = ['Season', 'P2P method', 'BP tariff', 'Batteries', 'Consumption']
    prosumers_list = ['P1', 'P2', 'P3', 'P4', 'P5']
    
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
        'TOTAL carbon payback time in years'
    ]
    
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
    
    # Looping every factor
    for factor in factors_list:
        print(f"\n--- Generating plots for factor: {factor} ---")
        
        # Community KPIs   
        for kpi in community_kpis:
            kpi_unit = get_kpi_unit(kpi) # Assumes you have your get_kpi_unit function defined
            if  plot_to_vizualize == 'Main_Effect':
                plot_main_effect(
                    df=df_comm, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                    prosumer=None, save_image=True
                )
            else:
                # Calls the new difference_ci for the community (single line)
                plot_difference_ci(
                    df=df_comm, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                    prosumers=None, save_image=True
                )
        print(f"Saved Community plots for {factor}")

        # Prosumer KPIs
        if plot_to_vizualize == 'Main_Effect':
            # For Main Effects, we loop through prosumers individually
            for prosumer in prosumers_list:
                for kpi in prosumer_kpis:
                    kpi_unit = get_kpi_unit(kpi)
                    plot_main_effect(
                        df=df_pros, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                        prosumer=prosumer, save_image=True
                    )
        else:
            # For Confidence Intervals, we loop ONLY through KPIs and pass the whole list of prosumers!
            for kpi in prosumer_kpis:
                kpi_unit = get_kpi_unit(kpi)
                plot_difference_ci(
                    df=df_pros, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                    prosumers=prosumers_list, save_image=True
                )
                
        print(f"Saved all Prosumer plots for {factor}")

    print("\nDONE! All plots are cleanly organized in your Results_data directory.")


# In[22]:


##########################################################
## SENSITIVITY ANALYSIS: PARETO PLOTS
##########################################################


# In[23]:


def pareto_plots_grid(df, kpi_x, kpi_y, maximize_x, maximize_y):

    # Compute Pareto frontier
    data = df[[kpi_x, kpi_y]].copy().values
    sx = 1 if maximize_x else -1
    sy = 1 if maximize_y else -1
    points = np.column_stack([sx * data[:, 0], sy * data[:, 1]])

    # Correct Pareto mask (keep NON-dominated points)
    pareto_mask = np.ones(points.shape[0], dtype=bool)

    for i in range(points.shape[0]):
        if not pareto_mask[i]:
            continue

        for j in range(points.shape[0]):
            if i == j or not pareto_mask[j]:
                continue

            # j dominates i if j >= i in all and > in at least one
            if np.all(points[j] >= points[i]) and np.any(points[j] > points[i]):
                pareto_mask[i] = False
                break

    pareto_df = df.iloc[pareto_mask].copy()

    # If no Pareto points found, fallback to best single point
    if pareto_df.empty:
        print(f"WARNING: No Pareto points for {kpi_x} vs {kpi_y}. Using global best point.")
        best_idx = np.argmax(points.sum(axis=1))
        pareto_df = df.iloc[[best_idx]].copy()

    # Sort frontier
    pareto_df = pareto_df.sort_values(by=kpi_x, ascending=not maximize_x)

    # -----------------------------
    # Knee point (safe version)
    # -----------------------------
    if len(pareto_df) == 1:
        knee_idx = pareto_df.index[0]
        knee_point = pareto_df.iloc[0]
    else:
        x_range = pareto_df[kpi_x].max() - pareto_df[kpi_x].min()
        y_range = pareto_df[kpi_y].max() - pareto_df[kpi_y].min()

        # Avoid division by zero
        if x_range == 0:
            x_norm = np.zeros(len(pareto_df))
        else:
            x_norm = (pareto_df[kpi_x] - pareto_df[kpi_x].min()) / x_range

        if y_range == 0:
            y_norm = np.zeros(len(pareto_df))
        else:
            y_norm = (pareto_df[kpi_y] - pareto_df[kpi_y].min()) / y_range

        dist = np.sqrt((1 - x_norm)**2 + (1 - y_norm)**2)

        # Safe idxmin
        knee_idx = dist.idxmin()
        knee_point = pareto_df.loc[knee_idx]

    factor_cols = ["Season", "P2P method", "BP tariff", "Batteries", "Consumption"]

    # -----------------------------
    # Create 2×3 subplot matrix
    # -----------------------------
    fig, axes = plt.subplots(2, 3, figsize=(22, 12))
    axes = axes.flatten()

    # --- Cell (0,0): Title + knee point info ---
    axes[0].axis("off")

    knee_text = (
        f"Pareto Frontier Analysis\n\n"
        f"{kpi_x} vs {kpi_y}\n"
        f"Maximize {kpi_x}: {maximize_x}\n"
        f"Maximize {kpi_y}: {maximize_y}\n\n"
        f"--- Knee Point ---\n"
        f"Index: {knee_idx}\n"
        f"{kpi_x}: {knee_point[kpi_x]:.3f}\n"
        f"{kpi_y}: {knee_point[kpi_y]:.3f}\n\n"
        f"--- Factors ---\n"
        + "\n".join([f"{col}: {knee_point[col]}" for col in factor_cols])
    )

    axes[0].text(
        0.5, 0.5,
        knee_text,
        ha="center", va="center",
        fontsize=14,
        family="monospace"
    )

    # --- Remaining 5 cells: plots ---
    for ax, factor in zip(axes[1:], factor_cols):

        sns.scatterplot(
            data=df,
            x=kpi_x,
            y=kpi_y,
            hue=factor,
            palette="tab10",
            alpha=0.4,
            s=60,
            ax=ax
        )

        ax.plot(
            pareto_df[kpi_x],
            pareto_df[kpi_y],
            color="red",
            linewidth=2,
            label="Pareto frontier"
        )

        ax.scatter(
            pareto_df[kpi_x],
            pareto_df[kpi_y],
            color="red"
        )

        ax.scatter(
            knee_point[kpi_x],
            knee_point[kpi_y],
            color="gold",
            s=250,
            edgecolor="black",
            label="Knee point"
        )

        ax.set_title(f"Colored by {factor}")
        ax.grid(alpha=0.4)

    plt.tight_layout()

    save_dir = "Results/Results_DOE/Original_Experiment/Plots/Pareto_plots"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"Pareto_{kpi_x}_vs_{kpi_y}.png".replace(" ", "_")
    save_path = os.path.join(save_dir, filename)

    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"Saved: {save_path}")

    plt.close(fig)


kpi_pairs = [

    ("Community total final bill in €", "Avoided anual emissions (Kg CO2 eq)", False, True),
    ("Community total saved in €", "Avoided anual emissions (Kg CO2 eq)", True, True),
    ("Fairness index", "Avoided anual emissions (Kg CO2 eq)", True, True),
    ("Fairness index", "Community total saved in €", True, True),
    ("Community Self-Sufficiency", "Avoided anual emissions (Kg CO2 eq)", True, True),
    ("Community Self-Consumption", "Avoided anual emissions (Kg CO2 eq)", True, True),
    ("Community Self-Sufficiency", "Fairness index", True, True),
    ("Community total final bill in €", "Fairness index", False, True),
    ("Community Self-Consumption", "Community total final bill in €", True, False),
]

def run_all_pareto_plots(df):
    for kpi_x, kpi_y, max_x, max_y in kpi_pairs:
        print(f"\n=== Plotting {kpi_x} vs {kpi_y} ===")
        pareto_plots_grid(df, kpi_x, kpi_y, max_x, max_y)


# In[24]:


def sobol_like_anova(df, kpi_name):
    df2 = df.copy()

    # Clean column names for formula compatibility
    df2 = df2.rename(columns={
        "P2P method": "P2P_method",
        "BP tariff": "BP_tariff"
    })

    formula = f"{kpi_name} ~ C(Season) + C(P2P_method) + C(BP_tariff) + C(Batteries) + C(Consumption)"
    model = smf.ols(formula, data=df2, eval_env=0).fit()

    anova_table = sm.stats.anova_lm(model, typ=2)

    ss_total = anova_table["sum_sq"].sum()
    anova_table["Sobol_index"] = anova_table["sum_sq"] / ss_total

    return anova_table

def plot_sobol_indices(df, kpi_name, save_dir):
    anova_table = sobol_like_anova(df, kpi_name)
    sobol = anova_table["Sobol_index"]

    plt.figure(figsize=(8,5))
    sobol.plot(kind="barh", color="steelblue")
    plt.title(f"Sobol Sensitivity Indices – {kpi_name}")
    plt.xlabel("Variance Contribution")
    plt.grid(axis="x", alpha=0.4)

    # Save figure
    filename = f"Sobol_{kpi_name}.png".replace(" ", "_")
    save_path = os.path.join(save_dir, filename)
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {save_path}")

    return sobol

def run_all_sobol_plots(df):
    save_dir = "Results/Results_DOE/Original_Experiment/Plots/Sobol_plots"
    os.makedirs(save_dir, exist_ok=True)

    # List of all community KPIs (cleaned names)
    kpis = [
        "Community_total_saved",
        "Community_total_final_bill",
        "Avoided_emissions",
        "Community_Self_Sufficiency",
        "Community_Grid_Dependency",
        "Community_Self_Consumption",
        "Fairness_index",
        "Self_suff_diff",
        "Baseline_poverty_help",
        "Environmental_impact",
        "Carbon_payback_years"
    ]


# In[25]:


get_ipython().system('jupyter nbconvert --to script doe_engine.ipynb')

