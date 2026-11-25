##########################################################
##########################################################
########### Stochastic randomization #####################
##########################################################
##########################################################


# doe_engine.py



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
import sys
import json
from CoreModules.backend_app import *
from CoreModules.Data_processing import *
from CoreModules.Visualization_engine import *
from CoreModules.Stochastic_simulator import (
    build_grand_correlation_matrices,
    generate_3D_simulation_tensors,
    create_prosumer_time_matrix_stochastic,
    get_month_day_counts,
)
from CoreModules.Digital_Twin_engine import twin, compute_prosumer_kpis


def _get_period_day_counts(master_data_map, fallback_n_days):
    month_names = (
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december'
    )
    periods = next(iter(master_data_map.values()))
    if tuple(periods) == month_names:
        return get_month_day_counts(master_data_map)
    return {period: fallback_n_days for period in periods}


##########################################################
## Importing the Design of Experiment (DoE) excel
##########################################################


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



##########################################################
## Montecarlo
##########################################################



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
        "Community total consumption in kWh",
        "Community total energy surplus in kWh",
        "Community P2P trading index in surplus",
        "Community Profit in %",
        "Community Payback time",
        "Community total invested in €",
        "Community total final bill in €",
        "Community total saved in €",
        "Fairness index", 'Baseline poverty help', 
        'Avoided emissions (Kg CO2 eq)', 'Enviromental impact',
        'TOTAL carbon payback time']
    
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



def montecarlo(number_iterations, n_days, prosumer_based_data, df_EC_parameters, master_data_map, season, P2P_method, seed):
    print(f'Starting Monte Carlo analysis...')
    all_prosumer = []
    all_community = []
    all_sum_analysis = []

    num_prosumers = prosumer_based_data.shape[1]
    n_days_by_period = _get_period_day_counts(master_data_map, n_days)
    period = season.lower()
    if period not in n_days_by_period:
        raise ValueError(f"Unknown simulation period: {season}")
    time_periods = n_days_by_period[period] * 24
    
    ## Creating the coorelation matrices
    grand_corr_matrices_dict =  build_grand_correlation_matrices(master_data_map);
    
    if seed is not None:
        np.random.seed(seed)
        
    for rep in range(number_iterations):
        final_simulation_data = generate_3D_simulation_tensors(n_days_by_period, master_data_map, grand_corr_matrices_dict)
        
        solar_m = final_simulation_data[period][0].flatten()
        wind_m  = final_simulation_data[period][1].flatten()
        BP_m    = final_simulation_data[period][2].flatten()
        SP_m    = final_simulation_data[period][3].flatten()
            
        C1_m = final_simulation_data[period][4].flatten()
        C2_m = final_simulation_data[period][5].flatten()
        C3_m = final_simulation_data[period][6].flatten()
        C4_m = final_simulation_data[period][7].flatten()
        C5_m = final_simulation_data[period][8].flatten()

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


##########################################################
## Full factorial analysis
##########################################################



def export_doe_results_to_excel(doe_matrix, community_stats_list, prosumer_stats_list, save_name="Master_DoE_Results.xlsx"):
    print("Formatting DoE results with Multi-Level Excel Headers...")
    
    # We format the DoE Matrix Inputs to have a "Experiment Settings" top header
    df_doe_reset = doe_matrix.reset_index()
    df_doe_inputs = df_doe_reset.copy()
    # This creates the 2-level header: Top level is 'Experiment Settings', Bottom is 'Month', 'Battery', etc.
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



def fullfactorial(doe_matrix, number_iterations, n_days, prosumer_based_data, df_EC_parameters, master_data_map, seed):
    print(f'Starting Full factorial experiment...')

    ## Creating the coorelation matrices & needed variables
    grand_corr_matrices_dict =  build_grand_correlation_matrices(master_data_map);
    num_prosumers = prosumer_based_data.shape[1]
    periods = list(master_data_map['Solar'])
    n_days_by_period = _get_period_day_counts(master_data_map, n_days)

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
        final_simulation_data = generate_3D_simulation_tensors(n_days_by_period, master_data_map, grand_corr_matrices_dict)
        
        for period in periods:
            time_periods = n_days_by_period[period] * 24
            solar_m = final_simulation_data[period][0].flatten()
            wind_m  = final_simulation_data[period][1].flatten()
            BP_m    = final_simulation_data[period][2].flatten()
            SP_m    = final_simulation_data[period][3].flatten()
            
            C1_m = final_simulation_data[period][4].flatten()
            C2_m = final_simulation_data[period][5].flatten()
            C3_m = final_simulation_data[period][6].flatten()
            C4_m = final_simulation_data[period][7].flatten()
            C5_m = final_simulation_data[period][8].flatten()

            # Stack the 5 arrays into a single 2D matrix of shape (5_prosumers, hours)
            load_matrix = np.vstack([C1_m, C2_m, C3_m, C4_m, C5_m])
            
            # 3. Build the time-based data matrix
            time_based_data, _ = create_prosumer_time_matrix_stochastic(num_prosumers, time_periods,prosumer_based_data,
                                                                        load_matrix, solar_m, wind_m, BP_m, SP_m)
            #shared generation
            E_pv_pr = solar_m * df_EC_parameters.loc['pw_pv_pr', 'Value']
            E_wt_pr = wind_m * df_EC_parameters.loc['pw_wt_pr', 'Value']

            time_based_data_dictionary[period] = time_based_data
            E_pv_pr_dictionary[period] = E_pv_pr
            E_wt_pr_dictionary[period] = E_wt_pr

        # We save the dictionaries into lists for each iteration.
        time_based_data_list.append(time_based_data_dictionary)
        E_pv_pr_list.append(E_pv_pr_dictionary)
        E_wt_pr_list.append(E_wt_pr_dictionary)

    
    ### STARTING THE EXPERIMENT LOOP
    for experiment_number in doe_matrix.index:
        start_time = time.time() # Start stopwatch
        current_row = doe_matrix.loc[experiment_number]

        # Current conditions
        period_column = 'Month' if 'Month' in current_row.index else 'Season'
        period = current_row[period_column].lower()
        raw_p2p = current_row['P2P method']
        P2P_method = p2p_mapping[raw_p2p]
        tariff = current_row['BP tariff']
        battery = current_row['Batteries']
        consumption = current_row['Consumption']

        print(f"\n--- Running Experiment {experiment_number}/576 ---")
        print(f"Config: {period}, {P2P_method}, Tariff: {tariff}, Bat: {battery}, Cons: {consumption}")

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
                time_based_data = time_based_data_list[rep][period]
                E_pv_pr = E_pv_pr_list[rep][period]
                E_wt_pr = E_wt_pr_list[rep][period]
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
                all_prosumer, all_community, all_sum_analysis, number_iterations, n_days_by_period[period], period, P2P_method)
        
        
            community_stadistics_per_experiment.append(stats_comm)
            prosumer_stadistics_per_experiment.append(stats_prosumer)

            today = datetime.now().strftime("%Y-%m-%d")

            checkpoint_folder = f"Results/Results_DOE/{today}_Experiment/DOE_Individual_Experiments"
            os.makedirs(checkpoint_folder, exist_ok=True) # Creates the folder safely
        
            # Create a clean, identifiable file name
            file_name = f"Exp_{experiment_number}_{period}_{P2P_method}.xlsx"
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



##########################################################
# Obtaining the results for the KPi and their confidence intervals for the baseline configurations
##########################################################


def build_kpi_table_with_ci(doe_matrix, p2p_method, source_name, target_kpis, is_community=True, ci_col_name='CI', checkpoint_folder="Results/Results_DOE/Original_Experiment/DOE_Individual_Experiments", baseline_levels=None):
    
    decimal_config = {
    2: ['Community total saved in €', 'Community total invested in €',
        'Total invested in €', 'Avoided emissions (Kg CO2 eq)',
        'Saved by entering community €'],
    4: ['Community Self-Sufficiency', 'Community Grid Dependency', 
        'Fairness index', 'EC savings appropiation', 'Profit in %',
        'Profit PV in %', 'Profit WT in %', 'Profit batteries in %']
    }
    
    kpi_decimals = {kpi: dec for dec, kpis in decimal_config.items() for kpi in kpis}


    
    p2p_col = 'P2P Method' if 'P2P Method' in doe_matrix.columns else ('P2P method' if 'P2P method' in doe_matrix.columns else None)
    if p2p_col is None:
        raise KeyError("Could not find a P2P method column ('P2P Method' or 'P2P method') in the DoE matrix.")

    mask = (doe_matrix[p2p_col] == p2p_method)

    if baseline_levels is None:
        baseline_levels = {}

    numeric_factor_candidates = ['Tariff', 'Consumption', 'Battery', 'PV Installed', 'WT Installed']
    for col in numeric_factor_candidates:
        if col in doe_matrix.columns and pd.api.types.is_numeric_dtype(doe_matrix[col]):
            baseline_val = baseline_levels.get(col, _detect_baseline_level(doe_matrix[col]))
            mask &= (doe_matrix[col] == baseline_val)

    legacy_baseline = {'BP tariff': 'Baseline', 'Batteries': 'Baseline', 'Consumption': 'Baseline'}
    for col, baseline_val in legacy_baseline.items():
        if col in doe_matrix.columns and doe_matrix[col].dtype == object:
            mask &= (doe_matrix[col] == baseline_val)

    baseline_exps = doe_matrix[mask]
    
    p2p_mapping = {
        'Market': 'P2P_market',
        'One price': 'P2P_one_price', 
        'Social': 'P2P_social',
        'Enviromental': 'P2P_enviromental',   # legacy CLI spelling
        'Environmental': 'P2P_enviromental',  # app selectbox spelling
    }
    mapped_p2p = p2p_mapping[p2p_method]
    
    all_data = []
    period_column = 'Month' if 'Month' in doe_matrix.columns else 'Season'
    for exp_num, row in baseline_exps.iterrows():
        period = str(row[period_column]).lower()
        file_name = f"Exp_{exp_num}_{period}_{mapped_p2p}.xlsx"
        file_path = os.path.join(checkpoint_folder, file_name)
        
        if not os.path.exists(file_path):
            print(f"Warning: File not found -> {file_name}")
            continue
        sheet = "Community KPIs" if is_community else "Prosumer KPIs"
        
        if is_community:
            df_stats = pd.read_excel(file_path, sheet_name=sheet, index_col=0)
            
            row_data = {'Source': source_name, period_column: period.capitalize()}
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
                p_row = {'Source': source_name, period_column: period.capitalize(), 'Prosumer': p}
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
                .set_index(['Source', period_column])
                .stack()
                .unstack(period_column)
                .rename_axis(index=['Source', 'KPI'])
               )
        else:
            return (df_final
                .set_index(['Source', period_column, 'Prosumer'])
                .stack()
                .unstack(period_column)
                .rename_axis(index=['Source', 'Prosumer', 'KPI'])
                .reorder_levels(['Source', 'KPI', 'Prosumer'])
                .sort_index()
               )
            
    return pd.DataFrame()



##########################################################
## SENSITIVITY ANALYSIS: MAIN EFFECTS PLOTS
##########################################################


def plot_main_effect(df, factor_col, kpi_col, kpi_unit, prosumer=None, save_image=False, plots_root="Results/Results_DOE/Original_Experiment/Plots"):
    
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
    elif factor_col == 'Month':
        order=['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
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
        folder_path = f'{plots_root}/Line_Plots/{folder}'
        os.makedirs(make_long_path(folder_path), exist_ok=True)
    
        safe_name_image = name_image.replace('/', '_').replace('\\', '_').replace(' ', '_')
        save_path = make_long_path(f'{folder_path}/{safe_name_image}.png')
    
        plt.savefig(save_path, dpi=200, bbox_inches='tight')
        plt.close() 
    else:
        plt.show()



def plot_difference_ci(df, factor_col, kpi_col, kpi_unit, prosumers=None, save_image=False, reference_level='Baseline', plots_root="Results/Results_DOE/Original_Experiment/Plots"):
    """
    Generates a Zero-Line Confidence Interval plot.
    If 'prosumers' is a list, it groups all prosumers side-by-side for each factor level.
    """
    
    # --- KPI NAME MAPPING ---
    community_kpis = [
        "Community Self-Sufficiency", "Self-sufficiency difference between prosumers",
        "Community Grid Dependency", "Community Self-Consumption",
        "Community total final bill in €", "Community total saved in €",
        "Community total invested in €",
        "Fairness index", 'Baseline poverty help', 'Avoided emissions (Kg CO2 eq)',
        'Enviromental impact', 'TOTAL carbon payback time'
    ]
    community_kpis_name = [
        "Community Self-Sufficiency", "Self-sufficiency difference between prosumers",
        "Community Grid Dependency", "Community Self-Consumption",
        "Community total final bill", "Community total saved",
        "Community total invested",
        "Fairness index", 'Baseline poverty help', 'Avoided emissions',
        'Enviromental impact', 'Carbon payback time (months)'
    ]
    
    prosumer_kpis = [
        'Self-Consumption Ratio', 'Self-Sufficiency Ratio', 'Grid Dependency', 
        'Net P2P Balance in KWh per simulated period', 'P2P Participation in KWh per simulated period', 
        'Shared energy in KWH (G2P-P2G) per simulated period', 'P2P trading index in deficit', 
        'P2P trading index in surplus', 'Total final bill in €',
        'Saved by entering community €', 'Profit in %',
        'Total invested in €',
        'Profit PV in %', 'Profit WT in %', 'Profit batteries in %',
        'Payback time', 'Payback time PV', 'Payback time WT', 'Payback time BATT', 'Bill reduction in %',
        'EC gain appropiation', 'EC savings appropiation', 'Contribution into EC investment', 
        'Avoided emissions (Kg CO2 eq)', 'Enviromental impact', 'Upfront carbon debt (Kg CO2 eq)',
        'TOTAL carbon payback time', 'PV carbon payback time',
        'WT carbon payback time', 'BATT carbon payback time'
    ]
    prosumer_kpis_name = [
        'Self-Consumption Ratio', 'Self-Sufficiency Ratio', 'Grid Dependency', 
        'Net P2P Balance in KWh', 'P2P Participation in KWh', 
        'Shared energy (G2P-P2G)', 'P2P trading index in deficit', 
        'P2P trading index in surplus', 'Total final bill', 
        'Saved by entering community', 'Profit this period',
        'Total invested',
        'Profit PV this period', 'Profit WT this period', 'Profit batteries this period',
        'Payback time', 'Payback time PV', 'Payback time WT', 'Payback time BATT', 'Bill reduction',
        'EC gain appropiation', 'EC savings appropiation', 'Contribution into EC investment', 
        'Avoided emissions', 'Enviromental impact', 'Upfront carbon debt',
        'Carbon payback time', 'PV carbon payback time',
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
    elif factor_col == 'Month':
        order=['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
        reference_level = 'January'
    elif factor_col == 'Season':
        order=['Winter', 'Spring', 'Summer', 'Autumn']
        reference_level = 'Spring'
    elif factor_col == 'P2P method':
        order=['One price', 'Market', 'Social', 'Enviromental']
        reference_level = 'Market'
    elif factor_col == 'BP tariff':
        order=['Low', 'Baseline', 'High']
    elif factor_col == 'Consumption' and reference_level == 'Baseline':
        # Legacy CLI-style string levels
        order=['Low', 'Baseline', 'High']
    else:
        # Dynamic factor (app-driven: 'P2P Method', 'Battery', 'Tariff',
        # 'Consumption' with integer levels, 'PV Installed', 'WT Installed', etc.)
        if prosumers is None:
            unique_vals = df[factor_col].dropna().unique()
        else:
            unique_vals = df[('Experiment Settings', factor_col)].dropna().unique()

        order = sorted(unique_vals.tolist())

        # Pick a sensible reference level: use the caller-supplied one if it's
        # actually present in the data, otherwise fall back to 0 if present,
        # otherwise just take the first (smallest) level.
        if reference_level not in order:
            if 0 in order:
                reference_level = 0
            else:
                reference_level = order[0]


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
        folder_path = f'{plots_root}/CI_plots/{folder}'
        os.makedirs(make_long_path(folder_path), exist_ok=True)
    
        safe_name_image = name_image.replace('/', '_').replace('\\', '_').replace(' ', '_')
        save_path = make_long_path(f'{folder_path}/{safe_name_image}.png')
    
        plt.savefig(save_path, dpi=200, bbox_inches='tight')
        plt.close() 
    else:
        plt.show()


# Function that saves all plots:

def get_kpi_unit(kpi_name):
    """Parses the KPI string to determine the correct unit for the plot labels."""
    kpi_lower = kpi_name.lower()
    
    # Financial metrics (€)
    if 'invested' in kpi_lower or 'investment' in kpi_lower:
        return '€'
    elif '€' in kpi_lower or 'saved' in kpi_lower:
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
        
    # Payback metrics are expressed in simulated months.
    elif 'months' in kpi_lower or 'payback' in kpi_lower:
        return 'months'
        
    else:
        return ''



def make_long_path(path):
    """Prefix path to support >260 chars on Windows. No admin rights needed."""
    if sys.platform == 'win32' and not path.startswith('\\\\?\\'):
        return '\\\\?\\' + os.path.abspath(path)
    return path


def generate_all_main_effects_plots(df_comm, df_pros, plot_to_vizualize, factors_list=None, plots_root=None, reference_levels=None):
    print(f"Starting plotting: {plot_to_vizualize}...")

    if factors_list is None:
        period_factor = 'Month' if ('Experiment Settings', 'Month') in df_comm.columns else 'Season'
        factors_list = [period_factor, 'P2P method', 'BP tariff', 'Batteries', 'Consumption']
    if plots_root is None:
        plots_root = "Results/Results_DOE/Original_Experiment/Plots"
    if reference_levels is None:
        reference_levels = {}

    prosumers_list = ['P1', 'P2', 'P3', 'P4', 'P5']

    community_kpis = [
        "Community Self-Sufficiency",
        "Self-sufficiency difference between prosumers",
        "Community Grid Dependency",
        "Community Self-Consumption",
        "Community total final bill in €",
        "Community total saved in €",
        "Community total invested in €",
        "Fairness index",
        'Baseline poverty help',
        'Avoided emissions (Kg CO2 eq)',
        'Enviromental impact',
        'TOTAL carbon payback time'
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
        'Total final bill in €',
        'Saved by entering community €',
        'Total invested in €',
        'Profit in %',
        'Profit PV in %',
        'Profit WT in %',
        'Profit batteries in %',
        'Payback time',
        'Payback time PV',
        'Payback time WT',
        'Payback time BATT',
        'Bill reduction in %',
        'EC gain appropiation',
        'EC savings appropiation',
        'Contribution into EC investment',
        'Avoided emissions (Kg CO2 eq)',
        'Enviromental impact',
        'Upfront carbon debt (Kg CO2 eq)',
        'TOTAL carbon payback time',
        'PV carbon payback time',
        'WT carbon payback time',
        'BATT carbon payback time'
    ]

    for factor in factors_list:
        print(f"\n--- Generating plots for factor: {factor} ---")
        ref_level = reference_levels.get(factor, 'Baseline')

        for kpi in community_kpis:
            kpi_unit = get_kpi_unit(kpi)
            if plot_to_vizualize == 'Main_Effect':
                plot_main_effect(
                    df=df_comm, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                    prosumer=None, save_image=True, plots_root=plots_root
                )
            else:
                plot_difference_ci(
                    df=df_comm, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                    prosumers=None, save_image=True, reference_level=ref_level, plots_root=plots_root
                )
        print(f"Saved Community plots for {factor}")

        if plot_to_vizualize == 'Main_Effect':
            for prosumer in prosumers_list:
                for kpi in prosumer_kpis:
                    kpi_unit = get_kpi_unit(kpi)
                    plot_main_effect(
                        df=df_pros, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                        prosumer=prosumer, save_image=True, plots_root=plots_root
                    )
        else:
            for kpi in prosumer_kpis:
                kpi_unit = get_kpi_unit(kpi)
                plot_difference_ci(
                    df=df_pros, factor_col=factor, kpi_col=kpi, kpi_unit=kpi_unit,
                    prosumers=prosumers_list, save_image=True, reference_level=ref_level, plots_root=plots_root
                )
        print(f"Saved all Prosumer plots for {factor}")

    print("\nDONE! All plots are cleanly organized in your Results_data directory.")



##########################################################
## SENSITIVITY ANALYSIS: PARETO PLOTS
##########################################################


def pareto_plots_grid(df, kpi_x, kpi_y, maximize_x, maximize_y, save_dir=None, factor_cols=None):

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
        x_vals = pareto_df[kpi_x].to_numpy()
        y_vals = pareto_df[kpi_y].to_numpy()

        x_range = x_vals.max() - x_vals.min()
        y_range = y_vals.max() - y_vals.min()

        # Avoid division by zero
        if x_range == 0:
            x_norm = np.zeros(len(pareto_df))
        else:
            x_norm = (x_vals - x_vals.min()) / x_range

        if y_range == 0:
            y_norm = np.zeros(len(pareto_df))
        else:
            y_norm = (y_vals - y_vals.min()) / y_range

        dist = np.sqrt((1 - x_norm)**2 + (1 - y_norm)**2)

        # Safe argmin: works regardless of whether x_norm/y_norm came from
        # a Series (non-degenerate range) or a plain ndarray (zero range)
        best_pos = int(np.argmin(dist))
        knee_idx = pareto_df.index[best_pos]
        knee_point = pareto_df.iloc[best_pos]


    if factor_cols is None:
        # Fallback: detect whichever known factor columns actually exist in df
        candidate_factors = ["Month", "Season", "P2P Method", "P2P method", "BP tariff", "Batteries",
                              "Consumption", "Tariff", "Battery", "PV Installed", "WT Installed"]
        factor_cols = [c for c in candidate_factors if c in df.columns]
        # Keep it to at most 5, since the plot grid only has 5 slots (2x3 minus the info cell)
        factor_cols = factor_cols[:5]


    # -----------------------------
    # Create a subplot grid sized to the actual number of factors
    # (1 info cell + 1 cell per factor, capped at 6 total cells / 2x3)
    # -----------------------------
    n_factor_plots = len(factor_cols)
    total_cells = n_factor_plots + 1  # +1 for the info/text cell

    if total_cells <= 3:
        n_rows, n_cols = 1, total_cells
        fig_w, fig_h = 7 * total_cells, 6
    elif total_cells <= 6:
        n_rows, n_cols = 2, 3
        fig_w, fig_h = 22, 12
    else:
        # Fallback for more than 5 factors: grow rows as needed, 3 per row
        n_cols = 3
        n_rows = -(-total_cells // n_cols)  # ceil division
        fig_w, fig_h = 22, 6 * n_rows

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_w, fig_h))
    axes = np.atleast_1d(axes).flatten()

    # Hide any leftover unused cells (e.g. total_cells=3 but grid gives 1x3 anyway — usually exact, but safe check)
    for extra_ax in axes[total_cells:]:
        extra_ax.axis("off")
        

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

    if save_dir is None:
        save_dir = "Results/Results_DOE/Original_Experiment/Plots/Pareto_plots"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"Pareto_{kpi_x}_vs_{kpi_y}.png".replace(" ", "_")
    save_path = os.path.join(save_dir, filename)

    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"Saved: {save_path}")

    plt.close(fig)


kpi_pairs = [

    ("Community total final bill in €", "Avoided emissions (Kg CO2 eq)", False, True),
    ("Community total saved in €", "Avoided emissions (Kg CO2 eq)", True, True),
    ("Fairness index", "Avoided emissions (Kg CO2 eq)", True, True),
    ("Fairness index", "Community total saved in €", True, True),
    ("Community Self-Sufficiency", "Avoided emissions (Kg CO2 eq)", True, True),
    ("Community Self-Consumption", "Avoided emissions (Kg CO2 eq)", True, True),
    ("Community Self-Sufficiency", "Fairness index", True, True),
    ("Community total final bill in €", "Fairness index", False, True),
    ("Community Self-Consumption", "Community total final bill in €", True, False),
]

def run_all_pareto_plots(df, save_dir=None, factor_cols=None):
    for kpi_x, kpi_y, max_x, max_y in kpi_pairs:
        print(f"\n=== Plotting {kpi_x} vs {kpi_y} ===")
        pareto_plots_grid(df, kpi_x, kpi_y, max_x, max_y, save_dir=save_dir, factor_cols=factor_cols)


def sobol_like_anova(df, kpi_name, factor_cols=None):
    df2 = df.copy()

    if factor_cols is None:
        period_factor = "Month" if "Month" in df2.columns else "Season"
        factor_cols = [period_factor, "P2P_method", "BP_tariff", "Batteries", "Consumption"]

    # Estimate how many parameters the model needs (1 per level minus 1, per factor, plus intercept)
    n_params = 1
    for f in factor_cols:
        n_levels = df2[f].nunique()
        n_params += max(n_levels - 1, 0)

    n_obs = len(df2)
    if n_obs - n_params < 1:
        raise ValueError(
            f"Not enough experiments ({n_obs}) to estimate Sobol indices for factors "
            f"{factor_cols} (model needs at least {n_params + 1} data points). Skipping."
        )

    formula = f"{kpi_name} ~ " + " + ".join([f"C({f})" for f in factor_cols])
    model = smf.ols(formula, data=df2, eval_env=0).fit()

    anova_table = sm.stats.anova_lm(model, typ=2)

    ss_total = anova_table["sum_sq"].sum()
    anova_table["Sobol_index"] = anova_table["sum_sq"] / ss_total

    return anova_table


def plot_sobol_indices(df, kpi_name, save_dir, factor_cols=None):
    anova_table = sobol_like_anova(df, kpi_name, factor_cols=factor_cols)
    sobol = anova_table["Sobol_index"]

    plt.figure(figsize=(8,5))
    sobol.plot(kind="barh", color="steelblue")
    plt.title(f"Sobol Sensitivity Indices – {kpi_name}")
    plt.xlabel("Variance Contribution")
    plt.grid(axis="x", alpha=0.4)

    filename = f"Sobol_{kpi_name}.png".replace(" ", "_")
    save_path = os.path.join(save_dir, filename)
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {save_path}")
    return sobol

def run_all_sobol_plots(df, save_dir=None, factor_cols=None):
    if save_dir is None:
        save_dir = "Results/Results_DOE/Original_Experiment/Plots/Sobol_plots"
    os.makedirs(save_dir, exist_ok=True)

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
        "Carbon_payback_time"
    ]

    for kpi in kpis:
        print(f"\n=== Processing Sobol indices for: {kpi} ===")
        try:
            plot_sobol_indices(df, kpi, save_dir, factor_cols=factor_cols)
        except ValueError as e:
            print(f"  -> Skipped: {e}")
        except Exception as e:
            print(f"  -> Skipped due to unexpected error: {e}")



##########################################################
## SENSITIVITY ANALYSIS: FUNCTIONS FOR THE APP
##########################################################

def export_doe_results_to_excel_app(doe_matrix, community_stats_list, prosumer_stats_list, experiment_timestamp, save_name="Master_DoE_Results.xlsx"):
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
    save_folder = f"Results/Results_DOE/{experiment_timestamp}_Experiment/MasterDoE"
    os.makedirs(save_folder, exist_ok=True)
    file_path = os.path.join(save_folder, save_name)
    
    with pd.ExcelWriter(file_path) as writer:
        # We removed index=False so Pandas doesn't crash!
        df_final_community.to_excel(writer, sheet_name="Community DoE")
        df_final_prosumer.to_excel(writer, sheet_name="Prosumer DoE")
        
    print(f"Success! Master DoE Excel file saved to: {file_path}")
    return df_final_community, df_final_prosumer



def fullfactorial_app(doe_matrix, level_master_dict, number_iterations, prosumer_based_data, df_EC_parameters, master_data_map, seed, experiment_timestamp=None):
    print(f'Starting Full factorial experiment...')

    grand_corr_matrices_dict =  build_grand_correlation_matrices(master_data_map)
    num_prosumers = prosumer_based_data.shape[1]
    months = list(master_data_map['Solar'])
    n_days_by_month = get_month_day_counts(master_data_map)
    if experiment_timestamp is None:
        experiment_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

    ## Saving variables
    time_based_data_list = []
    solar_m_list = []
    wind_m_list = []
    
    community_stadistics_per_experiment = []
    prosumer_stadistics_per_experiment = []

    p2p_mapping = {
        'Market': 'P2P_market',
        'One price': 'P2P_one_price', 
        'Social': 'P2P_social',
        'Environmental': 'P2P_enviromental' # Note: Fixed spelling to match frontend
    }
    
    np.random.seed(seed)

    ### We do one first loop to create the randomized data
    for rep in range(number_iterations):
        time_based_data_dictionary = {}
        solar_m_dictionary = {}
        wind_m_dictionary = {}

        final_simulation_data = generate_3D_simulation_tensors(n_days_by_month, master_data_map, grand_corr_matrices_dict)
        
        for month in months:
            time_periods = n_days_by_month[month] * 24
            solar_m = final_simulation_data[month][0].flatten()
            wind_m  = final_simulation_data[month][1].flatten()
            BP_m    = final_simulation_data[month][2].flatten()
            SP_m    = final_simulation_data[month][3].flatten()
            
            C1_m = final_simulation_data[month][4].flatten()
            C2_m = final_simulation_data[month][5].flatten()
            C3_m = final_simulation_data[month][6].flatten()
            C4_m = final_simulation_data[month][7].flatten()
            C5_m = final_simulation_data[month][8].flatten()

            load_matrix = np.vstack([C1_m, C2_m, C3_m, C4_m, C5_m])
            
            time_based_data, _ = create_prosumer_time_matrix_stochastic(num_prosumers, time_periods,prosumer_based_data,
                                                                        load_matrix, solar_m, wind_m, BP_m, SP_m)
            time_based_data_dictionary[month] = time_based_data
            solar_m_dictionary[month] = solar_m
            wind_m_dictionary[month] = wind_m

        time_based_data_list.append(time_based_data_dictionary)
        solar_m_list.append(solar_m_dictionary)
        wind_m_list.append(wind_m_dictionary)

    
    ### STARTING THE EXPERIMENT LOOP
    for experiment_number in doe_matrix.index:
        start_time = time.time()
        current_row = doe_matrix.loc[experiment_number]

        month = current_row['Month'].lower()
        raw_p2p = current_row['P2P Method']
        P2P_method = p2p_mapping[raw_p2p]
        
        # These are now integers (0, 1, 2, 3...) instead of strings
        tariff_level = current_row['Tariff']
        cons_level = current_row['Consumption']
        bat_level = current_row['Battery']
        pv_level = current_row['PV Installed']
        wt_level = current_row['WT Installed']

        print(f"\n--- Running Experiment {experiment_number}/{len(doe_matrix)} ---")
        print(f"Config: {month}, {P2P_method}")

        # ---------------------------------------------------------
        # Dynamic Dictionary Lookups
        # ---------------------------------------------------------
        
        # 1. Multipliers (Tariff & Consumption)
        tariff_mult = level_master_dict['Tariff'][tariff_level] if tariff_level != 0 else 1.0
        cons_mult = level_master_dict['Consumption'][cons_level] if cons_level != 0 else 1.0
        
        # Create fresh copies for this experiment
        current_prosumer_data = prosumer_based_data.copy()
        current_EC_parameters = df_EC_parameters.copy()

        # 2. Apply Battery Data
        if bat_level != 0:
            bat_config = level_master_dict['Battery'][bat_level]
            current_EC_parameters.loc['ic_pr', 'Value'] = bat_config['ic_pr']
            # Assuming Battery is row index 6 in your prosumer_based_data array
            current_prosumer_data[6, :] = [bat_config[f'Prosumer_{i+1}'] for i in range(num_prosumers)]
            
        # 3. Apply PV Data
        if pv_level != 0:
            pv_config = level_master_dict['PV Installed'][pv_level]
            current_EC_parameters.loc['pw_pv_pr', 'Value'] = pv_config['pw_pv_pr']
            # Assuming PV installed is row index 4 in your prosumer_based_data array
            current_prosumer_data[4, :] = [pv_config[f'Prosumer_{i+1}'] for i in range(num_prosumers)]

        # 4. Apply WT Data
        if wt_level != 0:
            wt_config = level_master_dict['WT Installed'][wt_level]
            current_EC_parameters.loc['pw_wt_pr', 'Value'] = wt_config['pw_wt_pr']
            # Assuming WT installed is row index 5 in your prosumer_based_data array
            current_prosumer_data[5, :] = [wt_config[f'Prosumer_{i+1}'] for i in range(num_prosumers)]

        
        # STARTING MONTECARLO
        try:
            all_prosumer = []
            all_community = []
            all_sum_analysis = []
        
            for rep in range(number_iterations):
                
                time_based_data = time_based_data_list[rep][month]
                raw_solar = solar_m_list[rep][month]
                raw_wind = wind_m_list[rep][month]
                current_time_based_data = time_based_data.copy()
    
                current_time_based_data[:,2,:] = current_time_based_data[:,2,:] * tariff_mult
                current_time_based_data[:,0,:] = current_time_based_data[:,0,:] * cons_mult 
                
                E_pv_pr = raw_solar * current_EC_parameters.loc['pw_pv_pr', 'Value']
                E_wt_pr = raw_wind * current_EC_parameters.loc['pw_wt_pr', 'Value']
                
                # Run the simulation (Pass current_EC_parameters, NOT the global one)
                _, results_data, time_based_data_results, _, flow_P2P = twin(
                    current_time_based_data, current_prosumer_data, current_EC_parameters, E_pv_pr, E_wt_pr, P2P_method)
        
                kpis, community, economic_kpis, social_kpis, enviromental_kpis, sum_analysis_data = compute_prosumer_kpis(
                    current_prosumer_data, results_data, flow_P2P, current_time_based_data, current_EC_parameters)
        
                combined = pd.concat([kpis, economic_kpis, social_kpis, enviromental_kpis], axis=1)
                all_prosumer.append(combined)
                all_community.append(community)
                all_sum_analysis.append(sum_analysis_data)
            
            stats_comm, stats_prosumer, prosumer_labels, kpi_names = analyse_montecarlo_no_plots(
                all_prosumer, all_community, all_sum_analysis, number_iterations, n_days_by_month[month], month, P2P_method)
        
            community_stadistics_per_experiment.append(stats_comm)
            prosumer_stadistics_per_experiment.append(stats_prosumer)

            checkpoint_folder = f"Results/Results_DOE/{experiment_timestamp}_Experiment/DOE_Individual_Experiments"
            os.makedirs(checkpoint_folder, exist_ok=True) 
        
            file_name = f"Exp_{experiment_number}_{month}_{P2P_method}.xlsx"
            file_path = os.path.join(checkpoint_folder, file_name)
        
            with pd.ExcelWriter(file_path) as writer:
                stats_comm.to_excel(writer, sheet_name="Community KPIs")
                stats_prosumer.to_excel(writer, sheet_name="Prosumer KPIs")
            
            print(f"--> Saved checkpoint: {file_name}")

            try:
                if os.path.exists("Results/current_simulation_status.json"):
                    with open("Results/current_simulation_status.json", "r") as f:
                        status_data = json.load(f)
                        
                    status_data["current"] = list(doe_matrix.index).index(experiment_number) + 1
                    
                    with open("Results/current_simulation_status.json", "w") as f:
                        json.dump(status_data, f)
            except Exception as monitor_error:
                pass

        except Exception as e:
            print(f"\nFATAL ERROR IN EXPERIMENT {experiment_number}: {e}")
            print("Stopping the massive loop early, but saving all completed experiments safely!")
            doe_matrix = doe_matrix.iloc[:len(community_stadistics_per_experiment)]
            break

        # STOPPING THE STOPWATCH AND ESTIMATING TIME
        end_time = time.time()
        duration_minutes = (end_time - start_time) / 60
        runs_completed = list(doe_matrix.index).index(experiment_number) + 1
        runs_left = len(doe_matrix) - runs_completed
        est_hours = (runs_left * duration_minutes) / 60
        
        print(f"--> Run time: {duration_minutes:.2f} mins. Estimated time remaining: {est_hours:.2f} hours.\n")

    df_master_comm, df_master_pros = export_doe_results_to_excel_app(
        doe_matrix, community_stadistics_per_experiment, prosumer_stadistics_per_experiment, experiment_timestamp
    )
    
    print("\n--- Full Factorial DoE Complete! ---")
    return df_master_comm, df_master_pros

##########################################################
## APP POST-PROCESSING: baseline KPI export + CI/Pareto/Sobol plots
##########################################################

def _detect_baseline_level(column_values):
    """
    Figures out the correct 'baseline' value for a DoE factor column,
    whether or not that factor was actively swept:
    - If the column only contains 0 (factor was never swept), baseline is 0.
    - If the column contains 2 (Tariff/Consumption style sweep: 1, 2, 3), baseline is 2.
    - If the column contains 0 among other values (Battery/PV/WT style sweep: 0, 1, 2...), baseline is 0.
    - Fallback: the smallest value present.
    """
    unique_vals = pd.unique(column_values.dropna())
    if len(unique_vals) == 0:
        return 0
    if len(unique_vals) == 1 and unique_vals[0] == 0:
        return 0
    if 2 in unique_vals:
        return 2
    if 0 in unique_vals:
        return 0
    return min(unique_vals)


def run_postprocessing_app(doe_matrix, experiment_timestamp, baseline_p2p=None, baseline_levels=None):
    """
    Call this right after fullfactorial_app() finishes successfully.

    baseline_p2p: which P2P Method value counts as "the" baseline for the
                  Baseline_KPI_results.xlsx export (e.g. 'Market'). If None,
                  auto-picks 'Market' if present, else the first value used.
    baseline_levels: dict mapping factor name -> level value that counts as
                      baseline for that factor (e.g. {'Battery': 1, 'Tariff': 2}).
                      If None, auto-detects per factor via _detect_baseline_level.
    """
    experiment_folder = f"Results/Results_DOE/{experiment_timestamp}_Experiment"
    master_path = os.path.join(experiment_folder, "MasterDoE", "Master_DoE_Results.xlsx")
    checkpoint_folder = os.path.join(experiment_folder, "DOE_Individual_Experiments")
    plots_root = os.path.join(experiment_folder, "Plots")

    if baseline_levels is None:
        baseline_levels = {}

    print("Reloading master results for post-processing...")
    df_comm, df_pros = load_doe_results_from_excel(file_path=master_path)

    # ---- 1. Baseline KPI export using build_kpi_table_with_ci (same nicely
    #         formatted "Source / KPI / Month (mean ± CI)" layout as the
    #         CLI script and the "Compare Scenarios" tab) ----
    p2p_col = 'P2P Method' if 'P2P Method' in doe_matrix.columns else 'P2P method'
    p2p_values = doe_matrix[p2p_col].unique().tolist()
    if baseline_p2p is None or baseline_p2p not in p2p_values:
        baseline_p2p = 'Market' if 'Market' in p2p_values else p2p_values[0]
    baseline_source_name = f"DT_{baseline_p2p.lower()}"

    target_kpis = [
        'Community total saved in €',
        'Community total invested in €',
        'Avoided emissions (Kg CO2 eq)',
        'Community Self-Sufficiency',
        'Community Grid Dependency',
        'Fairness index'
    ]
    target_prosumer_kpis = [
        'Profit in %',
        'Total invested in €',
        'Payback time',
        'EC savings appropiation',
        'Saved by entering community €'
    ]

    df_comm_baseline = build_kpi_table_with_ci(
        doe_matrix=doe_matrix,
        p2p_method=baseline_p2p,
        source_name=baseline_source_name,
        target_kpis=target_kpis,
        is_community=True,
        checkpoint_folder=checkpoint_folder,
        baseline_levels=baseline_levels
    )
    df_pros_baseline = build_kpi_table_with_ci(
        doe_matrix=doe_matrix,
        p2p_method=baseline_p2p,
        source_name=baseline_source_name,
        target_kpis=target_prosumer_kpis,
        is_community=False,
        checkpoint_folder=checkpoint_folder,
        baseline_levels=baseline_levels
    )

    baseline_folder = os.path.join(experiment_folder, "KPI_results_baseline")
    os.makedirs(baseline_folder, exist_ok=True)
    baseline_path = os.path.join(baseline_folder, "Baseline_KPI_results.xlsx")
    with pd.ExcelWriter(baseline_path) as writer:
        df_comm_baseline.to_excel(writer, sheet_name="Community KPIs")
        df_pros_baseline.to_excel(writer, sheet_name="Prosumer KPIs")
    print(f"Baseline KPI results saved to: {baseline_path}")

    # ---- 2. CI (Difference) plots ----
    numeric_factors = ['Tariff', 'Consumption', 'Battery', 'PV Installed', 'WT Installed']
    active_numeric_factors = [f for f in numeric_factors if f in doe_matrix.columns]

    reference_levels = {
        f: baseline_levels.get(f, _detect_baseline_level(doe_matrix[f])) for f in active_numeric_factors
    }

    candidate_factors = ['Month', 'P2P Method'] + numeric_factors
    factors_present = [f for f in candidate_factors if f in doe_matrix.columns and doe_matrix[f].nunique() > 1]

    print("Generating CI (Difference) plots...")
    try:
        generate_all_main_effects_plots(
            df_comm, df_pros, 'Difference_CI',
            factors_list=factors_present, plots_root=plots_root, reference_levels=reference_levels
        )
    except Exception as e:
        print(f"CI plots failed: {e}")

    # ---- 3. Pareto plots ----
    print("Generating Pareto plots...")
    try:
        pareto_dir = os.path.join(plots_root, "Pareto_plots")
        run_all_pareto_plots(df_comm, save_dir=pareto_dir, factor_cols=factors_present)
    except Exception as e:
        print(f"Pareto plots failed: {e}")

    # ---- 4. Sobol plots ----
    print("Generating Sobol plots...")
    try:
        df_clean = df_comm.copy()
        rename_map = {
            "Community total saved in €": "Community_total_saved",
            "Community total final bill in €": "Community_total_final_bill",
            "Community total invested in €": "Community_total_invested",
            "Avoided emissions (Kg CO2 eq)": "Avoided_emissions",
            "Self-sufficiency difference between prosumers": "Self_suff_diff",
            "Community Self-Sufficiency": "Community_Self_Sufficiency",
            "Community Grid Dependency": "Community_Grid_Dependency",
            "Community Self-Consumption": "Community_Self_Consumption",
            "Fairness index": "Fairness_index",
            "Baseline poverty help": "Baseline_poverty_help",
            "Enviromental impact": "Environmental_impact",
            "TOTAL carbon payback time": "Carbon_payback_time",
        }
        for f in factors_present:
            rename_map[f] = f.replace(" ", "_")
        df_clean = df_clean.rename(columns=rename_map)

        sobol_factor_cols = [rename_map[f] for f in factors_present]
        sobol_dir = os.path.join(plots_root, "Sobol_plots")
        run_all_sobol_plots(df_clean, save_dir=sobol_dir, factor_cols=sobol_factor_cols)
    except Exception as e:
        print(f"Sobol plots failed: {e}")

    print("\n--- Post-processing complete! ---")