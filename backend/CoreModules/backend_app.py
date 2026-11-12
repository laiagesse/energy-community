import os
import streamlit as st
import pandas as pd
import itertools


def get_available_result_folders(base_dir="Results"):
    """
    Scans the base directory and returns a list of all subfolders.
    """
    # Check if the base directory actually exists
    if not os.path.exists(base_dir):
        st.error(f"The base directory '{base_dir}' was not found. Please check your folder structure.")
        return []
    
    # List all items in the directory, but filter ONLY for folders (ignore loose files)
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    
    # Sort them alphabetically so they look nice in the menu
    return sorted(folders)


def get_dynamic_baseline_matrix(df, selected_p2p):
    """
    Filters the master DataFrame for the baseline conditions, ensuring 
    the Run Order / Experiment_ID is preserved so build_kpi_table_with_ci
    can rebuild the checkpoint file names. Works with both the old CLI
    schema (string 'Baseline' levels) and the new app schema (numeric
    baseline levels).
    """
    p2p_col = 'P2P Method' if 'P2P Method' in df.columns else ('P2P method' if 'P2P method' in df.columns else None)
    if p2p_col is None:
        st.error("Could not find a P2P method column in the results file.")
        return pd.DataFrame()

    mask = (df[p2p_col] == selected_p2p)

    # New app-style numeric baseline factors (only applied if the column exists and is numeric)
    numeric_baseline = {'Tariff': 2, 'Consumption': 2, 'Battery': 0, 'PV Installed': 0, 'WT Installed': 0}
    for col, baseline_val in numeric_baseline.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            mask &= (df[col] == baseline_val)

    # Legacy CLI-style string baseline factors
    legacy_baseline = {'BP tariff': 'Baseline', 'Batteries': 'Baseline', 'Consumption': 'Baseline'}
    for col, baseline_val in legacy_baseline.items():
        if col in df.columns and df[col].dtype == object:
            mask &= (df[col] == baseline_val)

    baseline_rows = df[mask].copy()

    # Preserve whichever index/ID column is present, so exp_num downstream
    # matches the checkpoint file names (Exp_<id>_<season>_<p2p>.xlsx)
    index_col_candidates = ['Run Order', 'Experiment_ID']
    index_col = next((c for c in index_col_candidates if c in baseline_rows.columns), None)

    factor_cols = [c for c in ['Season', p2p_col, 'BP tariff', 'Batteries', 'Consumption',
                                'Tariff', 'Battery', 'PV Installed', 'WT Installed']
                   if c in baseline_rows.columns]

    if index_col is not None:
        matrix = baseline_rows[[index_col] + factor_cols].set_index(index_col)
    else:
        matrix = baseline_rows[factor_cols]

    return matrix

def generate_dynamic_doe(active_factors_dict):
    """
    Generates a Full Factorial DoE matrix dynamically based on selected factors.
    Input: Dictionary like {'Season': ['Winter', 'Summer'], 'Tariff': ['Low', 'High']}
    Output: Pandas DataFrame with all combinations.
    """
    keys = active_factors_dict.keys()
    values = active_factors_dict.values()
    
    # itertools.product creates every possible combination
    combinations = list(itertools.product(*values))
    
    # Convert to DataFrame
    doe_matrix = pd.DataFrame(combinations, columns=keys)
    doe_matrix.index.name = "Experiment_ID"
    
    return doe_matrix