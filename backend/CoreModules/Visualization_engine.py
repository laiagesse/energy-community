#######################################################################################
#######################################################################################
############################Visualisation_engine########################################
#######################################################################################


#######################################################################################
# Importing files
#######################################################################################


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from matplotlib.colors import LinearSegmentedColormap



def save_plot(fig, folder, filename):
    os.makedirs(folder, exist_ok=True)
    fig.savefig(os.path.join(folder, filename), dpi=300, bbox_inches='tight')
    plt.close(fig)
    
def save_plotty(fig, folder, filename):
    os.makedirs(folder, exist_ok=True)
    fig.write_html(os.path.join(folder, filename + ".html"))


#######################################################################################
# 1. KPI Visualisation
#######################################################################################


#######################################################################################
# 1.1 Prosumer Level
#######################################################################################


def plot_prosumer_kpi_heatmap(df, title="Prosumer KPI Analysis", 
                              lifetime_pv=25, lifetime_wt=30, lifetime_bat=10, lifetime_total=21.67, save_folder=None):
    

    custom_colors = ["#C0392B", "#FFFFFF", "#27AE60"] # Red, White, Green
    my_cmap = LinearSegmentedColormap.from_list("custom_RdGn", custom_colors)
    num_prosumers = len(df)

    ### CATEGORY LISTS (matched to your KPI names)
    fixed_ratios = [
        'Self-Consumption Ratio', 'Self-Sufficiency Ratio', 
        'P2P trading index in deficit', 'P2P trading index in surplus'
    ]
    
    inverse_ratios = ['Grid Dependency', 'Enviromental impact']

    one_to_minus_one = ['EC gain appropiation', 'EC savings appropiation']
    
    # These use a 0-100 scale normalization
    fixed_100_to_minus_100 = [
        "Net P2P Balance in KWh per simulated period", 
        "P2P Participation in KWh per simulated period", 
        'Total final bill in € per month', 
        'Saved by entering community € per month',
        'Coverage original bill (before EC) in %',
        'Bill reduction in %',
        'Avoided anual emissions (Kg CO2 eq)'
    ]

    fixed_minus_100_to_100 = ["Shared energy in KWH (G2P-P2G) per simulated period"]

    # Match spelling:
    profits = [
        "Anual profit in %", "Anual profit PV in %", 
        "Anual profit WT in %", "Anual profit bateries in %"
    ]

    payback_PV = ['Payback time PV', 'PV carbon payback time in years']
    payback_WT = ['Payback time WT', 'WT carbon payback time in years']
    payback_batt = ['Payback time BATT', 'BATT carbon payback time in years']
    payback_total = ['TOTAL carbon payback time in years']
    
    contribution = ['Contribution into EC investment']
    upfront = ['Upfront carbon debt (Kg CO2 eq)']
    
    norm_df = df.copy()
    white_mask = pd.DataFrame(False, index=df.index, columns=df.columns)
    
    for col in df.columns:
        # Check if the asset exists at all for the community
        if (df[col].abs() < 1e-5).all():
            norm_df[col] = 0.5
            white_mask[col] = True
            continue

        # 1. Payback Logic (Red if > Lifetime, Green if <= Lifetime)
        if any(col in group for group in [payback_PV, payback_WT, payback_batt, payback_total]):
            if col in payback_PV: lt = lifetime_pv
            elif col in payback_WT: lt = lifetime_wt
            elif col in payback_batt: lt = lifetime_bat
            else: lt = lifetime_total
            
            # 1.0 = Green, 0.0 = Red. Use 0.9 and 0.1 to avoid pure white center
            norm_df[col] = np.where(df[col] <= lt, 0.9, 0.1)
            white_mask[col] = (df[col] < 1e-5)

        # 2. Profits (0% to 10% scale)
        elif col in profits:
            norm_df[col] = df[col].clip(0, 10) / 10.0
            white_mask[col] = (df[col] < 1e-5)

        # 3. Upfront Debt (Always Yellow/Neutral)
        elif col in upfront:
            norm_df[col] = 0.45 
            white_mask[col] = (df[col] < 1e-5)

        # 4. Ratios
        elif col in fixed_ratios:
            norm_df[col] = df[col].clip(0, 1)

        elif col in inverse_ratios:
            norm_df[col] = 1 - df[col].clip(0, 1)

        # 5. Financial/Flows (Scaling 0 to 100 or -100 to 100)
        elif col in fixed_100_to_minus_100:
            # Map -100 to 100 -> 0.0 to 1.0
            norm_df[col] = (df[col].clip(-100, 100) + 100) / 200
            
        elif col in fixed_minus_100_to_100:
            norm_df[col] = 1 - ((df[col].clip(-100, 100) + 100) / 200)

        # 6. Social Share
        elif col in one_to_minus_one:
            norm_df[col] = (df[col].clip(-1, 1) + 1) / 2

        elif col in contribution:
            c_max = df[col].max()
            norm_df[col] = df[col] / c_max if c_max > 0 else 0.5

        # 7. Default
        else:
            c_min, c_max = df[col].min(), df[col].max()
            norm_df[col] = (df[col] - c_min) / (c_max - c_min) if c_max != c_min else 0.5

    ### Plotting
    plt.figure(figsize=(16, 8))
    sns.heatmap(norm_df, mask=white_mask, cmap=my_cmap, center=0.5, linewidths=1, cbar=False)
    sns.heatmap(norm_df, annot=df, fmt=".2f", cmap=my_cmap, center=0.5, alpha=0, cbar=False)
    
    plt.title(title, fontsize=18, pad=20)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    if save_folder:
        os.makedirs(save_folder, exist_ok=True)
        
        clean_title = title.replace(" ", "_").replace("/", "_").replace(":", "")
        file_path = os.path.join(save_folder, f"{clean_title}.png")
        
        plt.savefig(file_path, bbox_inches='tight', dpi=300) 
        print(f"--> Heatmap saved successfully to: {file_path}")
        
    plt.show()


#######################################################################################
# 1.2 Energy Community Level
#######################################################################################


def compare_community_p2p(list_of_dfs, method_names, save_folder=None):
    """
    list_of_dfs: [df1, df2, df3...] Each should have the same index (the KPIs)
    method_names: ['Technique A', 'Technique B'...] labels for the columns
    """
    custom_colors = ["#C0392B", "#FFFFFF", "#27AE60"] # Red, White, Green
    my_cmap = LinearSegmentedColormap.from_list("custom_RdGn", custom_colors)
    
    # 1. Combine all dataframes side-by-side (axis=1)
    comparison_df = pd.concat(list_of_dfs, axis=1)
    comparison_df.columns = method_names
    
    # 2. Create a normalized dataframe for coloring
    norm_df = comparison_df.copy()
    
    ### Define KPI categories based on your specific rules
    direct_ratios = [
        'Community Self-Sufficiency', 
        'Community Self-Consumption', 
        'Fairness index'
    ]
    
    inverse_ratios = [
        'Self-sufficiency difference between prosumers', 
        'Community Grid Dependency', 
        'Enviromental impact'
    ]
    
    money_scale = [
        'Community total final bill in €', 
        'Community total saved in €',
        'community total final bill in €' 
    ]
    
    yellow_fixed = ['Avoided anual emissions (Kg CO2 eq)']
    poverty_scale = ['Baseline poverty help']
    
    # Iterate through each ROW (KPI) to apply specific color scaling rules
    for idx in comparison_df.index:
        row_data = comparison_df.loc[idx]
        idx_str = str(idx)
        
        # RULE 1: 0 = Red, 1 = Green
        if any(kpi in idx_str for kpi in direct_ratios):
            norm_df.loc[idx] = row_data.clip(0, 1)
            
        # RULE 2: 1 = Red, 0 = Green (Inverted)
        elif any(kpi in idx_str for kpi in inverse_ratios):
            norm_df.loc[idx] = 1 - row_data.clip(0, 1)
            
        # RULE 3: -100 = Red, +100 = Green
        elif any(kpi in idx_str for kpi in money_scale):
            # Map -100 to 0.0 and +100 to 1.0
            norm_df.loc[idx] = (row_data.clip(-100, 100) + 100) / 200
            
        # RULE 4: Always Yellow/Neutral (Center of the colormap -> 0.5)
        elif any(kpi in idx_str for kpi in yellow_fixed):
            norm_df.loc[idx] = 0.5
            
        # RULE 5: 0 = Red, 10 = Green
        elif any(kpi in idx_str for kpi in poverty_scale):
            # Map 0 to 0.0 and 10 to 1.0
            norm_df.loc[idx] = row_data.clip(0, 10) / 10.0
            
        # RULE 6: Fallback for any unexpected KPIs
        else:
            if row_data.max() == row_data.min():
                norm_df.loc[idx] = 0.5
            else:
                # Best technique in row = Green, Worst = Red
                norm_df.loc[idx] = (row_data - row_data.min()) / (row_data.max() - row_data.min())

    # 3. Visualization Setup
    plt.figure(figsize=(12, 8))
    
    sns.heatmap(
        norm_df, 
        annot=comparison_df,   
        fmt=".4f", 
        cmap=my_cmap, 
        center=0.5,            
        linewidths=1,
        cbar=False             
    )
    
    plt.title("Comparative Analysis of P2P Community Techniques", fontsize=15, pad=20)
    plt.ylabel("Key Performance Indicators (KPIs)")
    plt.xlabel("Simulation Scenarios / P2P Techniques")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    if save_folder:
        os.makedirs(save_folder, exist_ok=True)
        
        file_path = os.path.join(save_folder, f"{'Comparative Analysis of P2P Community Techniques'}.png")
        
        plt.savefig(file_path, bbox_inches='tight', dpi=300) 
        print(f"--> Heatmap saved successfully to: {file_path}")
        
    plt.show()


#######################################################################################
# 2. Digital Twin Validation Visualisation
#######################################################################################


#######################################################################################
# 2.1 Digital Twin vs UPC Model Validation
#######################################################################################


###Bar chart: compares Digital Twins vs UPC consumption and sharing results 
def plot_models_matrix(sum_market, sum_upc,):

    models = ["Market", "UPC"]
    data_list = [sum_market, sum_upc]

    P = sum_market.shape[0]
    prosumers = [f"P{i+1}" for i in range(P)]
    x = np.arange(P)

    fig, axes = plt.subplots(2, 2, figsize=(20, 10))
    plt.subplots_adjust(wspace=0.25, hspace=0.25)

    # LOOP THROUGH MODELS
    for col, (model_name, data) in enumerate(zip(models, data_list)):

        # CONSUMPTION COMPONENTS
        own_gen_consum   = data[:, 1]
        own_batt_consum  = data[:, 15]
        G2P_direct       = data[:, 5] 
        P2P_received     = data[:, 6]
        batt_charge_grid = data[:, 18]

        # SHARING COMPONENTS
        P2P_given_clean  = data[:, 7] - data[:, 16]  
        P2G              = data[:, 4]
        batt_charge_gen  = data[:, 17]
        batt_shared      = data[:, 16]              

        # CONSUMPTION PLOT
        ax = axes[0, col]

        ax.bar(x, own_gen_consum, label="Own generation", color="skyblue")
        ax.bar(x, own_batt_consum, bottom=own_gen_consum,
               label="Own battery consumption", color="orange")
        ax.bar(x, P2P_received, bottom=own_gen_consum + own_batt_consum,
               label="P2P received", color="green")
        ax.bar(x, G2P_direct, bottom=own_gen_consum + own_batt_consum + P2P_received,
               label="G2P (Grid bought)", color="purple")
        ax.bar(x, batt_charge_grid,
               bottom=own_gen_consum + own_batt_consum + P2P_received + G2P_direct,
               label="Battery charged from grid", color="red")

        ax.set_title(f"{model_name} – Consumption")
        ax.set_xticks(x)
        ax.set_xticklabels(prosumers)
        ax.grid(axis="y", linestyle="--", alpha=0.5)

        # SHARING PLOT 
        ax = axes[1, col]

        ax.bar(x, P2P_given_clean, label="P2P sold", color="teal")
        ax.bar(x, batt_shared, bottom=P2P_given_clean,
               label="Battery shared (to P2P)", color="gold")
        ax.bar(x, P2G, bottom=P2P_given_clean + batt_shared,
               label="P2G (Grid sold)", color="pink")
        ax.bar(x, batt_charge_gen, bottom=P2P_given_clean + batt_shared + P2G,
               label="Battery charged (own gen)", color="red")

        ax.set_title(f"{model_name} – Sharing")
        ax.set_xticks(x)
        ax.set_xticklabels(prosumers)
        ax.grid(axis="y", linestyle="--", alpha=0.5)

    # LEGENDS
    # Consumption legend 
    handles_c, labels_c = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles_c, labels_c, loc="upper center", ncol=5, fontsize=10, title="Consumption")
    # Sharing legend 
    handles_s, labels_s = axes[1, 0].get_legend_handles_labels()
    fig.legend(handles_s, labels_s, loc="lower center", ncol=4, fontsize=10, title="Sharing")

    plt.show()

    folder = 'Results/Results_DOE/Original_Experiment/Validation/Bar_charts'
    filename = 'Bar_chart_consumption_sharing' 
    save_plot(fig, folder, filename)



###Sankey plot: compares Digital Twin vs UPC results of P2P flow distribution
def plot_sankey_models(sum_market, sum_upc):
    models = {"Market": sum_market, "UPC": sum_upc}

    num_prosumers = sum_market.shape[0]
    prosumer_nodes = [f"P{i+1}" for i in range(num_prosumers)]
    grid_index = num_prosumers
    node_labels = prosumer_nodes + ["Grid"]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=list(models.keys()),
        specs=[[{"type": "sankey"}, {"type": "sankey"}]])

    # LOOP THROUGH MODELS

    for col, (model_name, data) in enumerate(models.items(), start=1):

        #FLOW COMPONENTS
        P2G = data[:, 4]
        G2P = data[:, 5]
        P2P_received = data[:, 6]
        P2P_given = data[:, 7]

        
        total_received = P2P_received.sum()
        P2P_matrix = np.zeros((num_prosumers, num_prosumers))

        if total_received > 0:
            proportions = P2P_received / total_received
            for i in range(num_prosumers):
                P2P_matrix[i, :] = P2P_given[i] * proportions
                P2P_matrix[i, i] = 0

        sources = []
        targets = []
        values = []
        colors = []

        # P2P flows
        for i in range(num_prosumers):
            for j in range(num_prosumers):
                if i != j and P2P_matrix[i, j] > 0:
                    sources.append(i)
                    targets.append(j)
                    values.append(P2P_matrix[i, j])
                    colors.append("blue")

        # Prosumer → Grid
        for i in range(num_prosumers):
            if P2G[i] > 0:
                sources.append(i)
                targets.append(grid_index)
                values.append(P2G[i])
                colors.append("red")

        # Grid → Prosumer
        for i in range(num_prosumers):
            if G2P[i] > 0:
                sources.append(grid_index)
                targets.append(i)
                values.append(G2P[i])
                colors.append("green")

        # PLOTS
        fig.add_trace(
            go.Sankey(
                node=dict(
                    pad=40,
                    thickness=20,
                    label=node_labels,
                    color="lightgray"
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=colors
                )
            ),
            row=1, col=col
        )

    fig.update_layout(
        title_text="Energy Flow Comparison Across Models",
        font_size=14,
        width=1800,
        height=600,
        paper_bgcolor="white",
        plot_bgcolor="white"
    )

    fig.show()
    
    folder = 'Results/Results_DOE/Original_Experiment/Validation/Sankey_plots'
    filename = 'Sankey_P2P_flows' 
    save_plotty(fig, folder, filename)


#######################################################################################
# 2.1 Stochastic Data Validation
#######################################################################################



def check_plot(data_dictionary, seasonal_upc, seasonal_time_based, attribute_name, save_image=False):
    """
    Creates a 5x1 vertical stacked subplot for a chosen attribute per prosumer
    as a line graph, comparing Stochastic (DT) seasonal data against Deterministic (UPC) seasonal data.
    Scales 1-month DT totals by 3 to match the 3-month seasonal baseline.
    """

    attribute_data = {
        'Consumption': {'index_DT': 0, 'index_UPC': 10},
        'Selling Price Grid': {'index_DT': 1, 'index_UPC': 1},
        'Buying Price Grid': {'index_DT': 2, 'index_UPC': 2},
        'Energy PV': {'index_DT': 4, 'index_UPC': 0},
        'Energy Wind': {'index_DT': 5, 'index_UPC': 1}
    }

    attr_idx_DT = attribute_data[attribute_name]['index_DT']
    attr_idx_UPC = attribute_data[attribute_name]['index_UPC']
    
    seasons = ['Winter', 'Spring', 'Summer', 'Autumn']
    num_prosumers = 5

    # Smart Aggregation Logic
    is_price = 'Selling Price Grid' in attribute_name or 'Buying Price Grid' in attribute_name
    is_consumption = 'Consumption' in attribute_name
    ylabel_unit = "(€/kWh)" if is_price else "(kWh)"
    agg_method = np.mean if is_price else np.sum
    agg_title = "Average" if is_price else "Total Seasonal"

    # Vertical Portrait layout with sharey=False
    fig, axes = plt.subplots(num_prosumers, 1, figsize=(8, 12), sharey=False, sharex=True)

    # Extraction and Plotting
    for p in range(num_prosumers):
        
        season_values_stochastic = []
        season_values_upc = []
        
        # Extract both Stochastic and UPC data season by season
        for season_raw in seasons:
            season = season_raw.lower() 
            
            # --- 1. Extract Stochastic Data ---
            if season in data_dictionary:
                value_stoch = data_dictionary[season][p, attr_idx_DT, :]                
                agg_val_stoch = agg_method(value_stoch)
                
                # Multiply by 3 for energy/consumption totals to scale 1 month to a 3-month season
                if not is_price:
                    agg_val_stoch *= 3
                    
                season_values_stochastic.append(agg_val_stoch)
            else:
                season_values_stochastic.append(0)
                
            # --- 2. Extract Deterministic (UPC) Data ---
            if season in seasonal_time_based and season in seasonal_upc:
                # Prices come from time_based matrix, Generation/Consumption from upc matrix
                if is_price:
                    value_det = seasonal_time_based[season][p, attr_idx_UPC, :]
                else:
                    value_det = seasonal_upc[season][p, attr_idx_UPC, :]
                    
                agg_val_det = agg_method(value_det)
                
                # Invert consumption if necessary
                if is_consumption:
                    agg_val_det = -agg_val_det
                    
                season_values_upc.append(agg_val_det)
            else:
                season_values_upc.append(0)

        # Rounding
        season_values_stochastic = np.round(season_values_stochastic, decimals=5)
        season_values_upc = np.round(season_values_upc, decimals=5)

        # Plotting (Both are now lines!)
        axes[p].plot(seasons, season_values_stochastic, marker='o', color='#1f77b4', linewidth=1.5, markersize=10, label='Stochastic (DT)')
        axes[p].plot(seasons, season_values_upc, marker='x', color='#d62728', linestyle='--', linewidth=1.5, markersize=8, label='Deterministic (UPC)')

        axes[p].margins(y=0.2)

        # Force perfectly centered zero lines for empty data
        if (np.max(season_values_stochastic) == 0 and np.min(season_values_stochastic) == 0 and 
            np.max(season_values_upc) == 0 and np.min(season_values_upc) == 0):
            axes[p].set_ylim(-10, 10)

        # Subplot Formatting 
        axes[p].set_title(f"Prosumer {p+1}", fontsize=12)
        axes[p].set_ylabel(ylabel_unit, fontsize=10) 
        axes[p].grid(axis='both', linestyle=':', alpha=0.5) 
        axes[p].tick_params(axis='y', which='major', length=6, color='grey')
        
        if p == num_prosumers - 1:
            axes[p].tick_params(axis='x', labelrotation=0) 
        
        if p == 0:
            # Legend anchored to the middle of the first plot
            axes[p].legend(loc='lower center', bbox_to_anchor=(0.5, 1.25), ncol=2, framealpha=1, facecolor='white', edgecolor='lightgrey', fontsize=9)
            
            axes[p].text(0.5, 1.85, f"{agg_title} {attribute_name} per Season", 
                         transform=axes[p].transAxes, ha='center', va='bottom', fontsize=16, fontweight='bold')
            
            axes[p].text(0.5, 1.65, "Verification of Stochastic Data vs Baseline", 
                         transform=axes[p].transAxes, ha='center', va='bottom', fontsize=14, color='dimgrey')

    plt.tight_layout()
    fig.subplots_adjust(top=0.80)
    
    # Save Image Logic
    if save_image:
        save_folder = "Results/Results_DOE/Original_Experiment/Validation/Line_plots_stochastic_values"
        os.makedirs(save_folder, exist_ok=True) 
        
        clean_name = attribute_name.replace(" ", "_")
        file_path = os.path.join(save_folder, f"Stochastic_vs_UPC_{clean_name}.png")
        
        plt.savefig(file_path, bbox_inches='tight', dpi=300) 
        print(f"--> Plot saved successfully to: {file_path}")
        
    plt.show()



