#!/usr/bin/env python
# coding: utf-8

# In[1]:


##########################################################
##########################################################
########### Stochastic randomization #####################
##########################################################
##########################################################


# In[2]:


# Stochastic_simulator.py


# In[3]:


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import skew
import scipy.stats as stats
from scipy.stats import norm, beta
import os


# In[4]:


##########################################################
## Exploratory Data Analysis Functions
##########################################################


# In[5]:


def analyze_seasonal_hours(seasons_dict, variable_name="Variable", save_images=False):
    """
    Takes a dictionary of 4 seasons, calculates summary stats per hour,
    and plots histograms (one 4x6 image per season) and boxplots.
    """
    seasons = ['winter', 'spring', 'summer', 'autumn']
    stats_tables = {}
    
    folder_name = 'Results/Results_Stochastic_Analysis/Stadistics images/BoxPlotsANDHistograms'
    if save_images:
        os.makedirs(folder_name, exist_ok=True)
    
    # Calculates the summary of stadistics
    for season in seasons:
        data = seasons_dict[season]
        df = pd.DataFrame(data, columns=['datetime', 'value'])
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        
        season_stats = []
        for h in range(24):
            hour_values = df[df['hour'] == h]['value'].astype(float).values
            
            if len(hour_values) == 0 or np.all(hour_values == 0):
                season_stats.append({'mean': 0, 'median': 0, 'skewness': 0, 'cv': 0})
                continue
                
            h_mean = np.mean(hour_values)
            h_median = np.median(hour_values)
            h_skew = skew(hour_values)
            h_std = np.std(hour_values, ddof=1)
            h_cv = (h_std / h_mean) if h_mean != 0 else 0
            
            season_stats.append({
                'mean': h_mean,
                'median': h_median,
                'skewness': h_skew,
                'cv': h_cv
            })
            
        stats_tables[season] = pd.DataFrame(season_stats)

    # Ploting histogram
    if save_images:
        print("Generating the 4x6 Histogram Grids (one per season)...")
        fixed_bins = np.linspace(0, 1.0, 25)
        
        for season in seasons:
            # Create a new 4x6 grid for EACH season
            fig, axes = plt.subplots(nrows=4, ncols=6, figsize=(32, 16))
            fig.subplots_adjust(top=0.92, hspace=0.4, wspace=0.3)
            fig.suptitle(f'Hourly Histograms: {variable_name} ({season.capitalize()})', fontsize=28, weight='bold')
            
            df = pd.DataFrame(seasons_dict[season], columns=['datetime', 'value'])
            df['hour'] = pd.to_datetime(df['datetime']).dt.hour
            
            # Flatten the 4x6 grid into a 1D list of 24 plots
            axes = axes.flatten()
            
            for h in range(24):
                ax = axes[h]
                hour_data = df[df['hour'] == h]['value'].astype(float)
                
                ax.hist(hour_data, bins=fixed_bins, color='teal', edgecolor='black', alpha=0.8)
                ax.set_xlim(-0.05, 1.05)
                ax.set_title(f'Hour {h}', fontsize=16)
                ax.tick_params(axis='x', labelsize=10)
                
                # Add labels only to the edges to keep it clean
                if h >= 18: # Bottom row
                    ax.set_xlabel('kWh/kW', fontsize=12)
                if h % 6 == 0: # Leftmost column
                    ax.set_ylabel('Frequency', fontsize=12)
                    
            # Save the specific season's image
            file_path = f"{folder_name}/Histograms_{variable_name}_{season.capitalize()}.png"
            plt.savefig(file_path, bbox_inches='tight', dpi=150)
            plt.close()
            print(f"Saved {file_path}")

    #We plot the boxplots
    if save_images:
        print("Generating the Daily Profile Boxplots...")
        fig_box, axes_box = plt.subplots(nrows=2, ncols=2, figsize=(18, 12), sharey=True)
        fig_box.suptitle(f'Daily Profile Boxplots by Season: {variable_name}', fontsize=20, weight='bold')
        
        axes_box = axes_box.flatten()

        for idx, season in enumerate(seasons):
            df = pd.DataFrame(seasons_dict[season], columns=['datetime', 'value'])
            df['hour'] = pd.to_datetime(df['datetime']).dt.hour
            
            data_to_plot = [df[df['hour'] == h]['value'].astype(float).values for h in range(24)]
            
            ax = axes_box[idx]
            ax.boxplot(data_to_plot, positions=range(24), flierprops=dict(marker='.', color='gray', alpha=0.5))
            ax.set_title(season.capitalize(), fontsize=16)
            ax.set_xlabel('Hour of the Day')
            ax.set_ylabel(variable_name)
            ax.set_xticks(range(0, 24, 2))
            ax.grid(axis='y', linestyle='--', alpha=0.7)
            
        plt.tight_layout()
        file_path = f"{folder_name}/Boxplots_{variable_name}.png"
        plt.savefig(file_path, bbox_inches='tight', dpi=150)
        plt.show() 
        plt.close()
        print(f"Saved Boxplots_{variable_name}.png")
    
    return stats_tables


# In[6]:


def save_seasonal_stats_to_excel(stats_dict, variable_name, folder_name='Results/Results_Stochastic_Analysis/Statistical data'):
    """
    Saves a dictionary of seasonal DataFrames into a single Excel file,
    with each season on a separate worksheet.
    """
    # Create the directory if it doesn't exist
    os.makedirs(folder_name, exist_ok=True)
    
    # Define the exact file path
    file_path = f"{folder_name}/{variable_name}_Seasonal_Statistics.xlsx"
    
    # We use ExcelWriter to write multiple sheets into the same file
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        for season, df in stats_dict.items():
            df.to_excel(writer, sheet_name=season.capitalize(), index=True)
            
    print(f"Successfully saved {variable_name} statistics to a single Excel file: {file_path}")


# In[7]:


##########################################################
## Correlation matrixes for each variable
##########################################################


# In[8]:


def get_and_save_correlation_matrices(seasons_dict, variable_name, save_as_excel=False):
    """
    Calculates the 24x24 Spearman correlation matrix for each season
    and saves them to Excel.
    """
    folder_name = 'Results/Results_Stochastic_Analysis/Statistical data/Correlation_Matrixes'
    os.makedirs(folder_name, exist_ok=True)
    
    seasons = ['winter', 'spring', 'summer', 'autumn']
    correlation_matrices = {}
    
    for season in seasons:
        #We prepare the data: Pivot into Days x Hours
        df = pd.DataFrame(seasons_dict[season], columns=['datetime', 'value'])
        df['value'] = df['value'].astype(float)
        df['date'] = pd.to_datetime(df['datetime']).dt.date
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        
        daily_profiles = df.pivot(index='date', columns='hour', values='value').fillna(0)
        
        #Calculating the Spearman Correlation Matrix
        corr_matrix = daily_profiles.corr(method='spearman')
        
        # When some of the variables have zero variance (like night time solar), the last function will output NaN.
        # We fill those with 0 correlation.
        corr_matrix = corr_matrix.fillna(0)
        
        # We save it into our Python dictionary
        correlation_matrices[season] = corr_matrix

    print(f"All 24x24 Correlation Matrices for {variable_name} generated successfully!")
    
    if save_as_excel == True:
            
        file_path = f"{folder_name}/{variable_name}_Correlation_Matrices.xlsx"
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for season, matrix in correlation_matrices.items():
                matrix.to_excel(writer, sheet_name=season.capitalize())
            
        print(f"All 24x24 Correlation Matrices for {variable_name} saved successfully!")
        
    return correlation_matrices


# In[9]:


##########################################################
## Beta distribution
##########################################################


# In[10]:


def get_mle_beta_parameters(seasons_dict, is_normalized=True):
    """
    Uses Maximum Likelihood Estimation (MLE) to fit a Beta distribution 
    to each hour of each season.
    If is_normalized=True: Locks boundaries to strictly [0, 1] (for PV/Wind).
    If is_normalized=False: Dynamically fits the min (loc) and range (scale) (for Prices/Load).
    """
    seasons = ['winter', 'spring', 'summer', 'autumn']
    beta_parameters = {}
    
    for season in seasons:
        # Organizing data by hour
        df = pd.DataFrame(seasons_dict[season], columns=['datetime', 'value'])
        df['value'] = df['value'].astype(float)
        df['date'] = pd.to_datetime(df['datetime']).dt.date
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        daily_profiles = df.pivot(index='date', columns='hour', values='value').fillna(0) ## We organize the table in a 2D pandas, row=date and column=hour
        
        hourly_params = {}
        for h in range(24):
            hour_data = daily_profiles[h].values
            
            # We check if there is variation in data (for example, night time in solar)
            min_val = np.min(hour_data)
            max_val = np.max(hour_data)
            
            if min_val == max_val:
                # If there's no variation (e.g., night time solar, or fixed price hour)
                hourly_params[h] = {'alpha': 0, 'beta': 0, 'loc': min_val, 'scale': 0, 'is_constant': True}
                continue
                
            # --- THE MLE OPTIMIZATION ---
            if is_normalized:
                # Squeeze the data inside [0, 1] for Solar and Wind.
                # MLE uses logarithms, so we need to avoid 0 and 1.
                safe_data = np.clip(hour_data, 0.0001, 0.9999)
                alpha_mle, beta_mle, loc_mle, scale_mle = stats.beta.fit(safe_data, floc=0, fscale=1)
            else:
                # Method 2: Expand the boundaries for Prices and Load
                # For values that are not Solar and Wind, values are not limited between 0 and 1. 
                buffer = (max_val - min_val) * 0.01
                forced_loc = min_val - buffer
                forced_scale = (max_val - min_val) + (2 * buffer)
                
                # Fit alpha and beta while forcing the empirical min and range
                alpha_mle, beta_mle, loc_mle, scale_mle = stats.beta.fit(
                    hour_data, floc=forced_loc, fscale=forced_scale
                )
            
            # Saving everything needed for the Monte Carlo simulation!
            hourly_params[h] = {
                'alpha': alpha_mle,
                'beta': beta_mle,
                'loc': loc_mle,
                'scale': scale_mle,
                'is_constant': False
            }
            
        beta_parameters[season] = hourly_params
    
        
    return beta_parameters


# In[11]:


def combine_stat_and_param_dicts(stats_dict, params_dict):
    """
    Takes two dictionaries containing Pandas DataFrames with the same keys (seasons)
    and merges the columns of the DataFrames together.
    """
    combined_dict = {}
    seasons = ['winter', 'spring', 'summer', 'autumn']
    
    for season in seasons:
        # 1. Extract the stats table
        df_stats = stats_dict[season].copy()
        
        # FIX: Check if 'hour' is missing. If so, turn the index into the 'hour' column!
        if 'hour' not in df_stats.columns:
            df_stats.index.name = 'hour'
            df_stats = df_stats.reset_index()
            
        # 2. Extract the params table
        df_params = pd.DataFrame.from_dict(params_dict[season], orient='index')
        df_params.index.name = 'hour'
        df_params = df_params.reset_index()
        
        # 3. Merging them side-by-side based on the 'hour' column
        combined_df = pd.merge(df_stats, df_params, on='hour', how='left')
        
        # (Optional) Drop the 'is_constant' column so it doesn't clutter your table
        if 'is_constant' in combined_df.columns:
            combined_df = combined_df.drop(columns=['is_constant'])
        
        # Saving the master table back into the new dictionary
        combined_dict[season] = combined_df
        
    return combined_dict


# In[12]:


def generate_artificial_days(n_days, master_df, corr_matrix):
    """
    Generates n_days of artificial data using a Gaussian Copula (NORTA method).
    """
    # Step 1: Generate correlated Normal variables using the 24x24 matrix
    # mean=np.zeros(24) ensures the Gaussian is centered at 0.
    Z = np.random.multivariate_normal(mean=np.zeros(24), cov=corr_matrix, size=n_days)
    
    # Step 2: Transform the Normal variables into Uniform percentiles [0, 1]
    U = norm.cdf(Z)
    
    # Create an empty matrix to hold our final real-world numbers
    simulated_data = np.zeros((n_days, 24))
    
    # Step 3: Transform Uniform percentiles into the Beta distribution per hour
    for h in range(24):
        # Extract the parameters for this specific hour from your master table
        # (Assuming 'hour' is the index or a column in your master_df)
        if 'hour' in master_df.columns:
            row = master_df[master_df['hour'] == h].iloc[0]
        else:
            row = master_df.loc[h]
            
        a = row['alpha']
        b = row['beta']
        loc_val = row['loc']
        scale_val = row['scale']
        
        # Check for our constant/nighttime edge cases (where scale is 0 or alpha/beta are 0)
        if scale_val == 0 or a == 0 or b == 0:
            simulated_data[:, h] = loc_val  # Just fill the whole hour with the constant value (e.g., 0)
        else:
            # The Inverse CDF (PPF) transformation!
            simulated_data[:, h] = beta.ppf(U[:, h], a=a, b=b, loc=loc_val, scale=scale_val)
            
    # Convert the raw array into a nice Pandas DataFrame
    simulated_df = pd.DataFrame(simulated_data, columns=[f"Hour_{h}" for h in range(24)])
    simulated_df.index.name = "Simulated_Day"
    
    return simulated_df


# In[13]:


def plot_goodness_of_fit(seasons_dict, master_df, variable_name, unit, season='summer'):
    """
    Plots the original historical histogram and overlays the fitted Beta distribution
    to visually prove the accuracy of our parameters.
    """
    # Extracting the original historical data
    df = pd.DataFrame(seasons_dict[season], columns=['datetime', 'value'])
    df['value'] = df['value'].astype(float)
    df['hour'] = pd.to_datetime(df['datetime']).dt.hour
    
    # Setting up the plot grid (4 rows x 6 columns = 24 hours)
    fig, axes = plt.subplots(nrows=4, ncols=6, figsize=(24, 16))
    fig.suptitle(
        f'Goodness-of-Fit: {variable_name} - {season.capitalize()}\n'
        f'(X-axis: {variable_name} in {unit} | Y-axis: Probability Density)', 
        fontsize=24, weight='bold')
   
    
    # Flatten the 4x6 grid into a simple 1D list of 24 plots so we can loop easily
    axes = axes.flatten()
    
    for h in range(24):
        ax = axes[h]
        hour_data = df[df['hour'] == h]['value'].values
        
        # --- PLOT 1: THE ORIGINAL HISTOGRAM ---
        ax.hist(hour_data, bins=20, density=True, alpha=0.6, color='skyblue', edgecolor='black')
        
        # --- PLOT 2: THE FITTED BETA CURVE ---
        # Get the parameters for this exact hour from our master table
        # We handle whether 'hour' is the index or a column
        if 'hour' in master_df.columns:
            row = master_df[master_df['hour'] == h].iloc[0]
        else:
            row = master_df.loc[h]
            
        a, b = row['alpha'], row['beta']
        loc_val, scale_val = row['loc'], row['scale']
        
        # Only draw the math curve if it's not a nighttime/constant hour
        if scale_val > 0 and a > 0 and b > 0:
            # Create a smooth X-axis line spanning from the minimum to the maximum
            x_line = np.linspace(loc_val, loc_val + scale_val, 200)
            
            # Calculate the mathematical Y values using the Beta Probability Density Function (PDF)
            y_curve = stats.beta.pdf(x_line, a, b, loc=loc_val, scale=scale_val)
            
            # Draw the thick red line
            ax.plot(x_line, y_curve, 'r-', lw=3, label='Theoretical Beta')
        
        # Clean up the visuals
        ax.set_title(f'Hour {h}', fontsize=14)
        ax.tick_params(axis='x', labelsize=10, rotation=45)
        ax.tick_params(axis='y', labelsize=10)
    
        # Only put the legend on the very first plot so it's not cluttered
        if h == 0:
            ax.legend(loc='upper right')

    plt.tight_layout(rect=[0, 0, 1, 0.96]) # Leave room for the main title
    
    # Saving the image
    folder_name = 'Results/Results_Stochastic_Analysis/Stadistics images/Beta_goodness_of_fit'
    os.makedirs(folder_name, exist_ok=True)
    
    filename = f"{folder_name}/GoodnessOfFit_{variable_name}_{season.capitalize()}.png"
    plt.savefig(filename, dpi=150)
    plt.show()
    print(f"Saved visual validation to {filename}")


# In[14]:


##########################################################
## ECDF distribution
##########################################################


# In[15]:


def generate_ecdf_artificial_days(n_days, historical_seasons_dict, season, corr_matrix):
    df = pd.DataFrame(historical_seasons_dict[season], columns=['datetime', 'value'])
    df['value'] = df['value'].astype(float)
    df['date'] = pd.to_datetime(df['datetime']).dt.date
    df['hour'] = pd.to_datetime(df['datetime']).dt.hour
    daily_profiles = df.pivot(index='date', columns='hour', values='value').fillna(0)
    
    Z = np.random.multivariate_normal(mean=np.zeros(24), cov=corr_matrix, size=n_days)
    U = norm.cdf(Z)
    
    simulated_data = np.zeros((n_days, 24))
    for h in range(24):
        hist_hour_data = daily_profiles[h].values ## Array with all the real values of hour h.
        if np.min(hist_hour_data) == np.max(hist_hour_data): ## Check needed for solar production in nighttime. 
            simulated_data[:, h] = np.min(hist_hour_data)
        else:
            simulated_data[:, h] = np.quantile(hist_hour_data, U[:, h]) 
            
    simulated_df = pd.DataFrame(simulated_data, columns=[f"Hour_{h}" for h in range(24)])
    return simulated_df, df # Returning historical df too for easy plotting


# In[16]:


def plot_ecdf_goodness_of_fit(simulated_df, historical_df, variable_name, unit, season):
    """
    Overlays the simulated ECDF data on top of the historical data 
    to visually prove the model perfectly captures the true distribution.
    """
    fig, axes = plt.subplots(nrows=4, ncols=6, figsize=(24, 16))
    fig.subplots_adjust(top=0.92, hspace=0.4, wspace=0.3)
    fig.suptitle(
        f'Goodness-of-Fit: {variable_name} - {season.capitalize()}\n'
        f'(X-axis: {variable_name} in {unit} | Y-axis: Probability Density)', 
        fontsize=24, weight='bold')

    axes = axes.flatten()
    fixed_bins = np.linspace(historical_df['value'].min(), historical_df['value'].max(), 26)
    
    for h in range(24):
        ax = axes[h]
        # Getting the historical and simulated data for this specific hour
        hist_data = historical_df[historical_df['hour'] == h]['value'].values
        sim_data = simulated_df[f"Hour_{h}"].values
        
        # Plotting Historical (Blue, slightly transparent)
        ax.hist(hist_data, bins=fixed_bins, density=True, alpha=0.5, color='royalblue', label='Historical')
        
        # Plot Simulated (Orange, slightly transparent)
        ax.hist(sim_data, bins=fixed_bins, density=True, alpha=0.5, color='darkorange', label='Simulated (ECDF)')
        
        ax.set_title(f'Hour {h}', fontsize=14)
        ax.tick_params(axis='x', labelsize=10, rotation=45)
        ax.tick_params(axis='y', labelsize=10)
        
        if h == 0:
            ax.legend(loc='upper right')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    folder_name = 'Results/Results_Stochastic_Analysis/Stadistics images/ECDF_goodness_of_fit'
    os.makedirs(folder_name, exist_ok=True)
    file_path = f"{folder_name}/ECDF_Validation_{variable_name}_{season.capitalize()}.png"
    plt.savefig(file_path, dpi=150)
    plt.show()
    print(f"Saved visual validation to {file_path}")


# In[17]:


def run_all_ecdf_validations(variables_to_process, n_days=1000):
    """
    Loops through all variables and all seasons, generates the ECDF artificial data,
    and plots/saves the Goodness-of-Fit graphs automatically.
    """
    
    seasons = ['winter', 'spring', 'summer', 'autumn']
    
    #Looping through every variable:
    for var_name, hist_dict, corr_dict, unit in variables_to_process:
        print(f" STARTING VALIDATION FOR: {var_name}")

        
        # Looping over every season for that variable
        for season in seasons:
            print(f"   -> Processing {season.capitalize()}...")

            clean_corr_matrix = corr_dict[season].values
            
            # Generating the 1,000 artificial days
            sim_df, hist_df = generate_ecdf_artificial_days(
                n_days=n_days, 
                historical_seasons_dict=hist_dict, 
                season=season, 
                corr_matrix=clean_corr_matrix
            )
            
            # Ploting the results and saving the images
            plot_ecdf_goodness_of_fit(sim_df, hist_df, var_name, unit, season)
            
    print("\n ALL 36 VALIDATION GRAPHS GENERATED AND SAVED SUCCESSFULLY!")



# In[18]:


##########################################################
## Stochastic engine. Generating random days.
##########################################################


# In[19]:


def build_grand_correlation_matrices(var_dict_map, save_as_excel=False):
    """
    Aligns 9 variables chronologically, creates a 216-column daily profile, 
    and calculates the 216x216 Spearman correlation matrix for each season.
    """
    seasons = ['winter', 'spring', 'summer', 'autumn']
    grand_matrices = {}
    
    folder_name = 'Results/Results_Stochastic_Analysis/Statistical data'
    os.makedirs(folder_name, exist_ok=True)
    
    for season in seasons: ## First the seasons loop because we create a correlation matrix for each season for all variables
        merged_daily_data = [] ## List to save dataframes [df_variable1, df_variable2, df_variable3, df_variable4...]

        for var_name, data_dict in var_dict_map.items():
            df = pd.DataFrame(data_dict[season], columns=['datetime', 'value'])
            df['value'] = df['value'].astype(float)
            df['date'] = pd.to_datetime(df['datetime']).dt.date
            df['hour'] = pd.to_datetime(df['datetime']).dt.hour
            
            # Pivoting into Days (rows) x Hours (columns)
            daily_df = df.pivot(index='date', columns='hour', values='value').fillna(0) 
            
            # We rename the 0-23 columns to include the variable name (e.g., 'Solar_H12')
            daily_df.columns = [f"{var_name}_H{h}" for h in range(24)]
            
            merged_daily_data.append(daily_df) ##We save the dataframe in the list
            
        # Creating the matrix
        # join='inner' is an extra saveguard in case we are missing data in some of the inputs.
        # Before we had Days x Hours. We save in axis 1 (so adding more columns) so we still have Days x Hours
        grand_df = pd.concat(merged_daily_data, axis=1, join='inner')
        
        # Calculating the 216x216 Spearman Matrix
        # .fillna(0) handles night-time solar hours that have 0 variance
        grand_corr = grand_df.corr(method='spearman').fillna(0)
        
        grand_matrices[season] = grand_corr
    
    print("\n All 216x216 Grand Correlation Matrices built successfully!")

    if save_as_excel == True:
        
        file_path = f"{folder_name}/Correlation_Matrix.xlsx"
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for season, matrix in grand_matrices.items():
                matrix.to_excel(writer, sheet_name=season.capitalize())
            
        print(f"\n All 216x216 Grand Correlation Matrices saved as {file_path}")
        
    return grand_matrices



# In[20]:


def generate_3D_simulation_tensors(n_days, master_data_map, grand_corr_matrices_dict):
    """
    Generates fully integrated artificial days across ALL variables simultaneously
    using the 216x216 Grand Correlation Matrix. Returns a 3D tensor per season.
    """
    seasons = ['winter', 'spring', 'summer', 'autumn']
    final_dict = {}
    num_variables = len(master_data_map) # This is 5
    
    
    for season in seasons:
        print(f"\nGenerating {n_days} fully integrated artificial days for {season.capitalize()}...")
        
        # Extract the correct 120x120 matrix for this season
        grand_corr_matrix = grand_corr_matrices_dict[season].values
        
        # Generate Z and U for THIS season
        Z = np.random.multivariate_normal(mean=np.zeros(grand_corr_matrix.shape[0]), cov=grand_corr_matrix, size=n_days)
        U = norm.cdf(Z) # Shape: (n_days, 216)
        
        # 2. THE FIX: Initialize the 3D tensor correctly (Variables, Days, Hours)
        simulated_tensor = np.zeros((num_variables, n_days, 24))
        master_col_idx = 0 
        
        # 3. Loop through the 5 variables
        for var_idx, (var_name, data_dict) in enumerate(master_data_map.items()):
            
            df = pd.DataFrame(data_dict[season], columns=['datetime', 'value'])
            df['value'] = df['value'].astype(float)
            df['date'] = pd.to_datetime(df['datetime']).dt.date
            df['hour'] = pd.to_datetime(df['datetime']).dt.hour
            daily_profiles = df.pivot(index='date', columns='hour', values='value').fillna(0)
            
            # Looping through the 24 hours for this variable
            for h in range(24):
                hist_hour_data = daily_profiles[h].values
                
                # The ECDF Quantile Mapping
                if np.min(hist_hour_data) == np.max(hist_hour_data): 
                    simulated_tensor[var_idx, :, h] = np.min(hist_hour_data)
                else:
                    simulated_tensor[var_idx, :, h] = np.quantile(hist_hour_data, U[:, master_col_idx])
                
                master_col_idx += 1 
        
        #Saving the completed tensor for this season outside the variable loop
        final_dict[season] = simulated_tensor
        print(f"Saved {season.capitalize()} tensor with shape: {simulated_tensor.shape} -> (Variables, Days, Hours)")

    print(f"\nSaved all seasons in a dictionary with keys: {seasons}")
    return final_dict


# In[21]:


def generate_data_per_season(n_days, season, master_data_map, grand_corr_matrices_dict):
    """
    Generates fully integrated artificial days across ALL variables simultaneously
    using the 216x216 Grand Correlation Matrix. Returns a 3D tensor per season.
    """

    final_dict = {}
    num_variables = len(master_data_map) # This is 5
    
    print(f"\nGenerating {n_days} fully integrated artificial days for {season.capitalize()}...")
        
    # Extract the correct 120x120 matrix for this season
    grand_corr_matrix = grand_corr_matrices_dict[season].values
        
    # Generate Z and U for THIS season
    Z = np.random.multivariate_normal(mean=np.zeros(grand_corr_matrix.shape[0]), cov=grand_corr_matrix, size=n_days)
    U = norm.cdf(Z) # Shape: (n_days, 216)
    
    # We create a matrix for the data
    simulated_tensor = np.zeros((num_variables, n_days, 24))
    master_col_idx = 0 
        
    # Loop through the 5 variables
    for var_idx, (var_name, data_dict) in enumerate(master_data_map.items()):
            
        df = pd.DataFrame(data_dict[season], columns=['datetime', 'value'])
        df['value'] = df['value'].astype(float)
        df['date'] = pd.to_datetime(df['datetime']).dt.date
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        daily_profiles = df.pivot(index='date', columns='hour', values='value').fillna(0)
            
        # Looping through the 24 hours for this variable
        for h in range(24):
            hist_hour_data = daily_profiles[h].values
                
            # The ECDF Quantile Mapping
            if np.min(hist_hour_data) == np.max(hist_hour_data): 
                simulated_tensor[var_idx, :, h] = np.min(hist_hour_data)
            else:
                simulated_tensor[var_idx, :, h] = np.quantile(hist_hour_data, U[:, master_col_idx])
                
            master_col_idx += 1 
        
    print(f"Generated randomized data for {season.capitalize()} with shape: {simulated_tensor.shape} -> (Variables, Days, Hours)")
    return simulated_tensor


# In[ ]:


##########################################################
## Creating the stochastic time matrix
##########################################################


# In[22]:


get_ipython().system('jupyter nbconvert --to script Stochastic_simulator.ipynb')


# In[ ]:


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


# In[ ]:


def create_prosumer_time_matrix_stochastic(num_prosumers, time_periods, prosumer_based_data, load_matrix, solar_m, wind_m, BP_m, SP_m):

    master_matrix = np.zeros((num_prosumers, 6, time_periods))
    
    for p in range(num_prosumers):

        # 0. Consumption (C)
        master_matrix[p, 0, :] = load_matrix[p,:] 
        
        # 1. Selling Price Grid (SP)
        master_matrix[p, 1, :] = SP_m

        # 2. Buying Price Grid (BP)
        tariff_types = np.array([[3], [3], [3], [3], [3]])
        BP_prosumer = np.array([ tariff_per_member(p + 1, t, tariff_types, BP_m) for t in range(time_periods) ])
        master_matrix[p, 2, :] = BP_prosumer

        # 3. Price Prosumer (PS)
        master_matrix[p, 3, :] = (BP_prosumer + SP_m) / 2

        # 4. PV generation
        pw_pv = prosumer_based_data[4, p]
        master_matrix[p, 4, :] = solar_m * pw_pv

        # 5. Wind generation
        pw_wt = prosumer_based_data[5, p]
        master_matrix[p, 5, :] = wind_m * pw_wt

    row_names = np.array([
        ['Consumption (C)'],
        ['Selling Price Grid (SP)'],
        ['Buying Price Grid (BP)'],
        ['Price Prosumer (PS)'],
        ['Energy PV (E_PV) in KWh'],
        ['Energy Wind (E_WT) in KWh']
    ])

    return master_matrix, row_names

