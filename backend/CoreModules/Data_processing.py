##########################################################
###########################################################
##################### Data processing #####################
###########################################################
###########################################################



#Data_processing.py


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import streamlit as st



##########################################################
# 1. UPC data processing
##########################################################


##########################################################
### Importing CSVs
##########################################################



def loading_CSV_data(folder_name, file_name, num_prosumers):
    
    #Checking if folder exists
    os.makedirs(folder_name, exist_ok=True)
    file_path = f"{folder_name}/{file_name}"
    
    # 1. Get the first row to count columns
    with open(file_path, 'r') as f:
        first_line = f.readline()
        # Count commas to find total columns
        num_cols = len(first_line.split(',')) 

    # 2. Load the numeric data (skipping column 0)
    members_data = np.genfromtxt(
        file_path, 
        delimiter=",", 
        skip_header=1, 
        usecols=range(1, num_cols) # This is now dynamic
    )

    # 3. Load the row names (column 0 only)
    row_names = np.genfromtxt(
        file_path, 
        delimiter=",", 
        skip_header=1, 
        usecols=0,
        dtype=str
    )
    
    if file_name == 'results_instance_ene_1_fo_eco_p_5_t_744.csv':
        members_data = members_data.reshape(num_prosumers, 17, -1)
        row_names = row_names.reshape(5, -1).T
    else:
        members_data = members_data.reshape(-1, num_prosumers)
        row_names = row_names.reshape(1, -1).T
    members_data[np.abs(members_data) < 1e-9] = 0.0
    members_data = np.nan_to_num(members_data, nan=0.0)
    
    # Reshape logic would go here...
    return members_data, row_names


# In[5]:


##########################################################
### Preparing data into input format
##########################################################



def tariff_per_member(prosumer, time_period, tariff_matrix, BP):
    ''' 
    if 1: fixed tarif
    if 2: time of use tarig
    if 3: hourly tariff
    '''
    if tariff_matrix[prosumer-1] == 1:
        BP = 0.1699
    elif tariff_matrix[prosumer-1] == 2:
        hour_of_day = time_period % 24
        if (10 <= hour_of_day < 14) or (18 <= hour_of_day < 22):
            BP = 0.2186  # Peak Price
        elif (8 <= hour_of_day < 10) or (14 <= hour_of_day < 18):
            BP = 0.1677  # Mid Price
        else:
            BP = 0.1279  # Off-Peak Price
    else:
        BP = BP[time_period]

    return BP

def price_between_members(prosumer, time_period, rates_data_document_name, tariff_matrix):
    BP = tariff_per_member(prosumer, time_period, rates_data_document_name, tariff_matrix)
    PS = (0.15+BP)/2
    return PS



##########################################################
### Creating a time based INPUT MATRIX
##########################################################


def create_prosumer_time_matrix(num_prosumers, time_periods, prosumer_based_data, consumption_list,
                                pv_file_name, wt_file_name, BP, folder_name):

    #Checking if folder exists
    os.makedirs(folder_name, exist_ok=True)
    
    # Initialize the master matrix: [Prosumers, 6 Parameters, Time]
    master_matrix = np.zeros((num_prosumers, 6, time_periods))
    
    # 1. Load Universal Data (PV, WT)
    pv_path = os.path.join(folder_name, pv_file_name)
    wt_path = os.path.join(folder_name, wt_file_name)
    usr_pv = np.loadtxt(pv_path)[:time_periods]
    usr_wt = np.loadtxt(wt_path)[:time_periods]
    
    # Optimization: Load rates once here if tariff type 3 is used
    # to avoid opening the file 745 times per prosumer.
    
    # 2. Iterate through each prosumer
    for p in range(num_prosumers):
        # A. Load Consumption (C) - Row 0
        
        consumption_path = os.path.join(folder_name, consumption_list[p])
        c_data = np.loadtxt(consumption_path)[:time_periods]
        master_matrix[p, 0, :] = c_data
        
        # B. Calculate Buying Price (BP) - Row 2
        # Extract the tariff types row (assuming index 6 is correct)
        tariff_types = prosumer_based_data[6, :] 
        
        # Vectorized-style call (using your existing function)
        bp_vector = np.array([
            tariff_per_member(p + 1, t, tariff_types, BP) 
            for t in range(time_periods)
        ])
        master_matrix[p, 2, :] = bp_vector
        
        # C. Price between Prosumers (PS) - Row 3
        master_matrix[p, 3, :] = (0.15 + bp_vector) / 2
        
        # D. Constant Selling Price (SP) - Row 1
        master_matrix[p, 1, :] = 0.15
        
        # E. Scale Energy Generation - Rows 4 and 5
        pw_pv = prosumer_based_data[4, p]
        pw_wt = prosumer_based_data[5, p]
        master_matrix[p, 4, :] = usr_pv * pw_pv
        master_matrix[p, 5, :] = usr_wt * pw_wt
        
    # 3. Create the Name Matrix
    # Shape [6, 1] to describe the 6 rows in the second dimension
    row_names = np.array([
        ['Consumption (C)'],
        ['Selling Price Grid (SP)'],
        ['Buying Price Grid (BP)'],
        ['Price Prosumer (PS)'],
        ['Energy PV (E_PV) in KWh'],
        ['Energy Wind (E_WT) in KWh']
    ])
        
    return master_matrix, row_names



def create_master_matrix_from_UPC(folder_name, file_name, num_prosumers, time_periods, prosumer_based_data):
    """
    Loads the UPC CSV results, reshapes the 17-row blocks, and directly extracts 
    Generation, Consumption, and Prices into a [Prosumers, 6, Time] master matrix.
    Tariff type 3 leaves price rows (SP, BP, PS) empty (0.0) for later assignment.
    """
    # 1. Path checking
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, file_name)
    
    # 2. Get columns (hours) from the UPC file
    with open(file_path, 'r') as f:
        first_line = f.readline()
        num_cols = len(first_line.split(',')) 

    # 3. Load and clean the UPC numeric data
    upc_data = np.genfromtxt(file_path, delimiter=",", skip_header=1, usecols=range(1, num_cols))
    upc_data[np.abs(upc_data) < 1e-9] = 0.0
    upc_data = np.nan_to_num(upc_data, nan=0.0)
    
    # Reshape UPC data to: [Prosumers, 17 Variables, Hours]
    upc_data = upc_data.reshape(num_prosumers, 17, -1)
    
    # Initialize the target master matrix: [Prosumers, 6 Parameters, Time]
    # Everything starts as 0.0!
    master_matrix = np.zeros((num_prosumers, 6, time_periods))
    
    # Extract tariff types
    tariff_types = prosumer_based_data[7, :] 
    
    # 4. Pre-calculate Time-of-Use prices for the whole month instantly
    hour_of_day = np.arange(time_periods) % 24
    tou_price = np.full(time_periods, 0.1279) # Default to off-peak
    peak_mask = ((hour_of_day >= 10) & (hour_of_day < 14)) | ((hour_of_day >= 18) & (hour_of_day < 22))
    mid_mask = ((hour_of_day >= 8) & (hour_of_day < 10)) | ((hour_of_day >= 14) & (hour_of_day < 18))
    tou_price[peak_mask] = 0.2186
    tou_price[mid_mask] = 0.1677

    # 5. Populate the master matrix for each prosumer
    for p in range(num_prosumers):
        
        # A. Consumption (C) -> Extracted from UPC Row 11 (Index 10)
        master_matrix[p, 0, :] = -upc_data[p, 10, :time_periods]
        
        # B. Prices (SP, BP, PS) -> Based on Tariff
        t_type = tariff_types[p]
        
        if t_type == 1 or t_type == 2:
            # Selling Price Grid (SP)
            master_matrix[p, 1, :] = 0.15
            
            # Buying Price Grid (BP)
            if t_type == 1:
                master_matrix[p, 2, :] = 0.1699
            elif t_type == 2:
                master_matrix[p, 2, :] = tou_price
                
            # Price Prosumer (PS)
            master_matrix[p, 3, :] = (master_matrix[p, 1, :] + master_matrix[p, 2, :]) / 2
            
        # NOTE: If t_type == 3, the code skips the block above. 
        # Rows 1, 2, and 3 will remain perfectly empty (0.0) for this prosumer!
        
        # C. Energy PV and WT -> Extracted from UPC Row 1 and 2 (Index 0 and 1)
        master_matrix[p, 4, :] = upc_data[p, 0, :time_periods]
        master_matrix[p, 5, :] = upc_data[p, 1, :time_periods]

    # 6. Create Row Names
    row_names = np.array([
        ['Consumption (C)'],
        ['Selling Price Grid (SP)'],
        ['Buying Price Grid (BP)'],
        ['Price Prosumer (PS)'],
        ['Energy PV (E_PV) in KWh'],
        ['Energy Wind (E_WT) in KWh']
    ])
        
    return master_matrix, row_names, upc_data



def build_and_split_yearly_UPC_matrices(folder_name, num_prosumers, prosumer_based_data, BP_yearly, SP_yearly, objective):
    """
    1. Loops through 12 monthly CSVs and extracts exact hour counts dynamically.
    2. Builds the full 8760-hour master matrices and injects dynamic pricing.
    3. Splits the final matrices into meteorological seasons.
    Returns dictionaries of seasonal matrices, ready for DoE simulation.
    """
    months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    
    if objective == 'Economic':
        o = 'cw'
    elif objective == 'Social':
        o = 'dbp'
    elif objective in ['Environmental', 'Enviromental']:  # Acepta ambas ortografías
        o = 'tgc'
    else:
        raise ValueError(f"Error: Objetivo '{objective}' no reconocido.")
    
    
    monthly_master_list = []
    monthly_upc_list = []
    hours_per_month = [] # Tracks the exact length of each CSV

    
    print("Starting data pipeline: Processing 12 months...")
    
    # ==========================================
    # PHASE 1: READ MONTHS & EXTRACT DATA
    # ==========================================
    for m in months:
        file_name = f"results_instance_{m}_dic_1_fo_{o}_p_5.csv"
        file_path = os.path.join(folder_name, file_name)
        
        # Dynamically read the exact hours from the CSV header
        with open(file_path, 'r') as f:
            first_line = f.readline()
            num_cols = len(first_line.split(','))
            time_periods = num_cols - 1  
            
        hours_per_month.append(time_periods)
        
        # Call the inner extraction function
        master_matrix, row_names, upc_data = create_master_matrix_from_UPC(
            folder_name, file_name, num_prosumers, time_periods, prosumer_based_data
        )
        
        monthly_master_list.append(master_matrix)
        monthly_upc_list.append(upc_data)
        
    # ==========================================
    # PHASE 2: GLUE YEAR TOGETHER & INJECT PRICES
    # ==========================================
    time_based_upc = np.concatenate(monthly_master_list, axis=2)
    upc_matrix = np.concatenate(monthly_upc_list, axis=2)
    
    tariff_types = prosumer_based_data[7, :]
    
    for p in range(num_prosumers):
        # A. Inject Selling Price (SP) for the whole year (Row 1)
        time_based_upc[p, 1, :] = SP_yearly
        
        # B. Inject Buying Price (BP) ONLY if Tariff is 3 (Row 2)
        if tariff_types[p] == 3:
            time_based_upc[p, 2, :] = BP_yearly
            
        # C. Recalculate Peer-to-Peer Price (PS) for the whole year (Row 3)
        time_based_upc[p, 3, :] = (time_based_upc[p, 1, :] + time_based_upc[p, 2, :]) / 2

    print(f"Matrices joined and prices injected! Total hours: {time_based_upc.shape[2]}")

    # ==========================================
    # PHASE 3: SPLIT INTO SEASONS DYNAMICALLY
    # ==========================================
    # Create an array [1, 2, 3... 12] and repeat each number based on the exact CSV lengths
    months_1_to_12 = np.arange(1, 13)
    month_array = np.repeat(months_1_to_12, hours_per_month)
    
    # Create meteorological boolean masks
    winter_mask = np.isin(month_array, [12, 1, 2])
    spring_mask = np.isin(month_array, [3, 4, 5])
    summer_mask = np.isin(month_array, [6, 7, 8])
    autumn_mask = np.isin(month_array, [9, 10, 11])
    
    # Slice the matrices using the masks
    seasons_time_based_upc = {
        'winter': time_based_upc[:, :, winter_mask],
        'spring': time_based_upc[:, :, spring_mask],
        'summer': time_based_upc[:, :, summer_mask],
        'autumn': time_based_upc[:, :, autumn_mask]
    }
    
    seasons_upc_matrix = {
        'winter': upc_matrix[:, :, winter_mask],
        'spring': upc_matrix[:, :, spring_mask],
        'summer': upc_matrix[:, :, summer_mask],
        'autumn': upc_matrix[:, :, autumn_mask]
    }
    
    print("--- Seasonal Split Complete ---")
    print(f"Winter hours: {winter_mask.sum()} | Spring hours: {spring_mask.sum()}")
    print(f"Summer hours: {summer_mask.sum()} | Autumn hours: {autumn_mask.sum()}")
    
    # Returns the two dictionaries and the row names!
    return seasons_time_based_upc, seasons_upc_matrix, row_names



##########################################################
### Exporting data to excel format
##########################################################


# Shape => (number_prosumers, atributes, time_periods)


def export_to_excel_non_stacked(df_row_names, numpy_data, folder_name ,file_name):
    '''
    TAKES IN:
    df_row_names => DataFrame of row names
    numpy of shape => (prosumers, atributes, time_periods)

    EXPORTING FORMAT:
    Non Stacked => Each prosumer data in a separate Excel Sheet.
    '''
    #Checking if folder exists
    os.makedirs(folder_name, exist_ok=True)
    file_path = f"{folder_name}/{file_name}"

    #Number of prosumers
    P = numpy_data.shape[0]  # 5 prosumers
    
    # Fix: convert (6,1) → (6,)
    column_headers = df_row_names.flatten()

    
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        for p_idx in range(P):
            data_2d = numpy_data[p_idx, :, :].T  
            
            df = pd.DataFrame(data_2d, columns=column_headers)
            df.index.name = 'Hour'

            sheet_name = f"Member_{p_idx + 1}"
            df.to_excel(writer, sheet_name=sheet_name)
    
    print(f"Non-stacked file saved successfully in folder {folder_name} as {file_name}")



def export_to_excel_stacked(df_row_names, numpy_data, folder_name, file_name):
    """
    TAKES IN:
    df_row_names => DataFrame of row names
    numpy of shape => (prosumers, atributes, time_periods)

    EXPORTING FORMAT:
    Stacked => Ordered by time and prosumer in one same sheet
    """
    #Checking if folder exists
    os.makedirs(folder_name, exist_ok=True)
    file_path = f"{folder_name}/{file_name}"

    #Needed variables
    P, num_attributes, T = numpy_data.shape
    
    # --- THE SAFETY CHECK ---
    if len(df_row_names) != num_attributes:
        raise ValueError(f"CRITICAL MISMATCH: You have {len(df_row_names)} names in 'results_names', "
                         f"but your data matrix has {num_attributes} attributes.")
    
    # 1. Prepare a list of lists (no dictionaries!)
    long_data_list = []
    
    # 2. Iterate through time first, then prosumers
    for t in range(T):
        for p in range(P):
            # Create a single flat list: [Hour, Prosumer_ID, Value1, Value2, ..., ValueN]
            row_data = [t, f"P{p+1}"] + numpy_data[p, :, t].tolist()
            long_data_list.append(row_data)
    
    # 3. Create the DataFrame in one shot
    # We combine your metadata columns with your exact results_names array
    column_headers = ['Hour', 'Prosumer_ID'] + list(df_row_names)
    df_long = pd.DataFrame(long_data_list, columns=column_headers)
    
    # 4. Export to Excel
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df_long.to_excel(writer, sheet_name='All_Data', index=False)
        
        # Formatting for readability
        worksheet = writer.sheets['All_Data']
        worksheet.freeze_panes(1, 2)
        
        # Auto-adjust column width
        for idx, col in enumerate(df_long.columns):
            max_len = max(df_long.iloc[:, idx].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(idx, idx, min(max_len, 50))

    print(f"Stack format file saved successfully in folder {folder_name} as {file_name}")



##########################################################
# 2. Stochastic data iput
##########################################################


@st.cache_data
def process_pvgis_data(file_path):
    """
    Reads, cleans, and formats photovoltaic generation data from the EU PVGIS website.
    Converts W to kWh/kW and returns a NumPy array with ['datetime', 'value'].
    """
    print(f"Loading PV data from: {file_path}")
    
    # Readining the CSV, skipping the 10 metadata lines at the top
    # nrows=8760 ensures we get one year of hourly data
    df_pv = pd.read_csv(file_path, skiprows=10, nrows=8760)
    
    # Data cleaning: Convert to numeric and datetime
    df_pv['P'] = pd.to_numeric(df_pv['P'], errors='coerce')
    df_pv['time'] = pd.to_datetime(df_pv['time'], format='%Y%m%d:%H%M')
    
    # NaN Check and Safety Handling
    nan_count = df_pv['P'].isna().sum()
    if nan_count > 0:
        print(f"Found {nan_count} NaN values in the 'P' column.")
        print("We fill nan values with zero")
        df_pv['P'] = df_pv['P'].fillna(0)
    else:
        print("No NaN Values.")
        
    # Transform units: W/kW to kWh/kW
    df_pv['P'] = df_pv['P'] / 1000.0
    
    # Extract the final NumPy array
    usr_pv_array = df_pv[['time', 'P']].values
    
    # Verification
    max_gen = np.max(usr_pv_array[:, 1])
    print(f"Array Shape: {usr_pv_array.shape}, with (time, value). Max Generation: {max_gen:.3f} kW/kW\n")
    
    return usr_pv_array


@st.cache_data
def process_ninja_wind_data(file_path):
    """
    Reads, cleans, and formats wind generation data from the renewables.ninja database.
    Returns a NumPy array with ['time', 'electricity'] in kWh/kW.
    """
    print(f"Loading Wind data from: {file_path}")
    
    # Reading the CSV, skipping the 3 metadata lines at the top
    # nrows=8760 ensures we get one year of hourly data
    df_wind = pd.read_csv(file_path, skiprows=3, nrows=8760)
    
    # Data cleaning: Convert to numeric and datetime
    df_wind['electricity'] = pd.to_numeric(df_wind['electricity'], errors='coerce')
    df_wind['time'] = pd.to_datetime(df_wind['time'])
    
    # NaN Check and Safety Handling
    nan_count = df_wind['electricity'].isna().sum()
    if nan_count > 0:
        print(f"Found {nan_count} NaN values in the 'electricity' column.")
        print("We fill nan values with zero")
        df_wind['electricity'] = df_wind['electricity'].fillna(0)
    else:
        print("No NaN Values.")
        
    # The Renewables Ninja data is already in kW/kW (or kWh/kW per hour)
    # Extract the final NumPy array
    usr_wt_array = df_wind[['time', 'electricity']].values
    
    # Verification
    max_gen = np.max(usr_wt_array[:, 1])
    print(f"Array Shape: {usr_wt_array.shape}, with (time, value). Max Generation: {max_gen:.3f} kWh/kW\n")
    
    return usr_wt_array


@st.cache_data
def process_esios_price_data(file_path, price_name="Market Price"):
    """
    Reads, cleans, and formats ESIOS grid price data (Buying or Selling).
    Converts €/MWh to €/kWh, aligns timezones, and returns a NumPy array.
    """
    print(f"Loading {price_name} data from: {file_path}")
    
    # Reading the CSV (ESIOS uses semicolons)
    df_price = pd.read_csv(file_path, sep=';', nrows=8760)
    
    # Data cleaning: Convert to numeric and change units (€/MWh to €/kWh)
    df_price['value'] = pd.to_numeric(df_price['value'], errors='coerce') / 1000.0
    
    # Keep ESIOS local wall time so calendar months align with PV/Wind data.
    df_price['datetime'] = pd.to_datetime(df_price['datetime'].str.slice(stop=19))
    
    # NaN Check and Safety Handling
    nan_count = df_price['value'].isna().sum()
    if nan_count > 0:
        print(f"Found {nan_count} NaN values in the 'value' column.")
        print("We fill nan values with previous value")
        # ffill() takes the previous valid hour's price and copies it forward
        df_price['value'] = df_price['value'].ffill() 
    else:
        print("No NaN Values.")

    # DST fall-back repeats a local hour; collapse it for the daily hour pivot.
    df_price = df_price.groupby('datetime', as_index=False, sort=False)['value'].mean()
        
    # Extract the final NumPy array
    price_array = df_price[['datetime', 'value']].values
    
    # Verification
    avg_price = np.mean(price_array[:, 1])
    print(f"Array Shape: {price_array.shape}, with (time, value). Average {price_name}: {avg_price:.4f} €/kWh\n")
    
    return price_array


@st.cache_data
def process_esios_load_profile(file_path):
    """
    Reads, cleans, and formats ESIOS load profile data (hourly consumption proportion).
    Aligns timezones, handles missing data, and returns a NumPy array.
    """
    print(f"Loading ESIOS Load Profile data from: {file_path}")
    
    # Reading the CSV (ESIOS uses semicolons)
    df_load = pd.read_csv(file_path, sep=';', nrows=8760)
    
    # Data cleaning: Convert to numeric
    df_load['value'] = pd.to_numeric(df_load['value'], errors='coerce') 
    
    # Handle datetime and strip timezones to perfectly match PV/Wind data
    df_load['datetime'] = pd.to_datetime(df_load['datetime'], utc=True)
    df_load['datetime'] = df_load['datetime'].dt.tz_localize(None)
    
    # NaN Check and Safety Handling
    nan_count = df_load['value'].isna().sum()
    if nan_count > 0:
        print(f"Found {nan_count} NaN values in the 'value' column.")
        print("We fill nan values with previous value")
        df_load['value'] = df_load['value'].ffill()
    else:
        print("No NaN Values.")
        
    # Extract the final NumPy array
    load_profiles = df_load[['datetime', 'value']].values
    
    # Verification
    avg_load = np.mean(load_profiles[:, 1])
    print(f"Array Shape: {load_profiles.shape} with (time, value). Avg consumption proportion/hour: {avg_load:.6f}\n")
    
    return load_profiles


@st.cache_data
def process_consumption_one_prosumer(file_path):
    """
    Reads minute-level consumption data (kWh), aggregates it to hourly sums,
    cleans missing data, and clips it strictly to the year 2023 (8760 hours).
    """
    print(f"Loading consumption data from: {file_path}")
    
    # Reading the CSV (ESIOS uses semicolons)
    df_load = pd.read_csv(file_path, sep=';')
    
    # Data cleaning: Convert to numeric
    df_load['Sum [kWh]'] = pd.to_numeric(df_load['Sum [kWh]'], errors='coerce') 
    
    # Handle datetime and strip timezones to perfectly match PV/Wind data
    df_load['Time'] = pd.to_datetime(df_load['Time'], dayfirst=True, utc=True)
    df_load['Time'] = df_load['Time'].dt.tz_localize(None)
    
    # NaN Check and Safety Handling
    nan_count = df_load['Sum [kWh]'].isna().sum()
    if nan_count > 0:
        print(f"Found {nan_count} NaN values in the 'value' column.")
        print("We fill nan values with previous value")
        df_load['Sum [kWh]'] = df_load['Sum [kWh]'].ffill()
    else:
        print("No NaN Values.")

    # Grouping by hour
    df_load.set_index('Time', inplace=True)
    df_hourly = df_load.resample('1h').sum()
    df_hourly['Sum [kWh]'] = df_hourly['Sum [kWh]'].ffill() # Savety check

    # We slice to year 2023
    df_hourly = df_hourly.loc['2023-01-01':'2023-12-31']
    
    # Extract the final NumPy array
    df_hourly.reset_index(inplace=True)
    load_profiles = df_hourly[['Time', 'Sum [kWh]']].values
    
    return load_profiles


@st.cache_data
def loading_all_consumptions(standard_file_path, number_prosumers):
    '''
    Takes a standard file path "Datasets/ConsumptionProsumer".
    All consumption datasets for prosumers will be named ConsumptionProsumer1, ConsumptionProsumer2...

    For every consumption file:
    Reads minute-level consumption data (kWh), aggregates it to hourly sums,
    cleans missing data, and clips it strictly to the year 2023 (8760 hours).
    '''
    consumption = np.zeros((number_prosumers, 8760, 2), dtype=object)
    for P in range(1, number_prosumers+1):
        file_path = f"{standard_file_path}{P}.csv"
        C = process_consumption_one_prosumer(file_path)
        consumption[P-1, :, :] = C.copy()
        print(f"Consumption for prosumer {P} has been saved")
    return consumption




def split_into_seasons(data_array):
    """
    Takes an (8760, 2) NumPy array where column 0 is a datetime object 
    and column 1 is the value, and splits it into meteorological seasons.
    """
    #We xtract the month from each datetime object in column 0
    # (We use a list comprehension to get the .month attribute of each timestamp)
    months = np.array([dt.month for dt in data_array[:, 0]])
    
    #We create boolean masks for each season 
    winter_mask = np.isin(months, [12, 1, 2])
    spring_mask = np.isin(months, [3, 4, 5])
    summer_mask = np.isin(months, [6, 7, 8])
    autumn_mask = np.isin(months, [9, 10, 11])
    
    #We apply the masks to create the 4 seasonal arrays
    seasons_dict = {
        'winter': data_array[winter_mask],
        'spring': data_array[spring_mask],
        'summer': data_array[summer_mask],
        'autumn': data_array[autumn_mask]
    }
    
    return seasons_dict


def split_into_months(data_array):
    """Split datetime/value rows into calendar months, preserving their order."""
    month_names = (
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december'
    )
    dates = pd.to_datetime(data_array[:, 0])
    months = dates.month.to_numpy()

    return {
        month_name: data_array[months == month_number]
        for month_number, month_name in enumerate(month_names, start=1)
    }




def save_plot(fig, folder, filename):
    os.makedirs(folder, exist_ok=True)
    fig.savefig(os.path.join(folder, filename), dpi=300, bbox_inches='tight')
    plt.close(fig)



