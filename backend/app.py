import os
import streamlit as st
from CoreModules.backend_app import *
from CoreModules.Data_processing import *
from CoreModules.Visualization_engine import *
from CoreModules.Stochastic_simulator import *
from CoreModules.Digital_Twin_engine import *
from CoreModules.doe_engine import *
import threading
import json


# Configure the main settings of the web page
st.set_page_config(page_title="Digital Twin UPC", layout="wide")

st.title("Stochastic Digital Twin Verification Tool for Renewable Energy Communities.")
st.markdown("Developed by KU Leuven University for the Polytechnic University of Catalunya (UPC). Both the frontend and backend code was developed by Clara Pons Barber and Paula Mate Pulido. You can contact us at claraponsbarber@gmail.com and pamates012@gmail.com")

# Create the two main tabs
tab1, tab2 = st.tabs(["Instant Analytics Explorer", "Launch Simulation (14h)"])

# ---------------------------------------------------------
# TAB 1: THE ANALYTICS EXPLORER
# ---------------------------------------------------------
with tab1:
    st.header("Analysis of Results")
    st.write("Compare different pre-calculated stochastic simulation baselines side-by-side.")
    
    # 1. GLOBAL CONTROL
    st.markdown("### 1. Comparison Setup")
    num_comparisons = st.radio(
        "How many scenarios do you want to compare?", 
        options=[1, 2, 3], 
        horizontal=True
    )
    
    # We will store the user's configurations in a list so we can process them later
    user_configs = []
    
# 2. THE CONTROL BOARD (Dynamic Input Columns)
    st.markdown("### 2. Configure Scenarios")
    input_columns = st.columns(num_comparisons)
    
    folder = "Results/Results_DOE"
    available_folders = get_available_result_folders(folder)
    
    if available_folders:
        for i in range(num_comparisons):
            with input_columns[i]:
                # We use a distinct background color/box for each scenario to make it visually pop
                with st.container(border=True): 
                    st.subheader(f"Scenario {i + 1}")
                    
                    sel_folder = st.selectbox(
                        "Data Source", 
                        available_folders, 
                        key=f"folder_{i}"
                    )
                    
                    user_configs.append({
                        "scenario_num": i + 1,
                        "folder": sel_folder
                    })
                    
        # 3. THE TRIGGER BUTTON
        st.divider() 
        
        # When clicked, we save a permanent "True" flag into the session state
        if st.button("📊 Compare Scenarios", type="primary", use_container_width=True):
            st.session_state.run_comparison = True
            
        # Now, we check the memory flag, NOT the button!
        if st.session_state.get("run_comparison", False):
            
            st.markdown("### 3. Comparison Results")
            tab_names = [f"Scenario {cfg['scenario_num']}" for cfg in user_configs]
            result_tabs = st.tabs(tab_names)
            
            # Loop through the configs and calculate the results for each one
            for i, config in enumerate(user_configs):
                with result_tabs[i]:
                    full_folder_path = os.path.join(folder, config["folder"])
                    baseline_path = os.path.join(full_folder_path, "KPI_results_baseline", "Baseline_KPI_results.xlsx")
                    
                    if os.path.exists(baseline_path):
                        with st.spinner(f"Loading Baseline KPIs for Scenario {config['scenario_num']}..."):
                            # Leer directamente del archivo Excel pre-calculado
                            df_comm_baseline = pd.read_excel(baseline_path, sheet_name="Community KPIs")
                            df_pros_baseline = pd.read_excel(baseline_path, sheet_name="Prosumer KPIs")
                            
                            # Renombrar columnas de índice y rellenar celdas combinadas de Excel
                            if "Unnamed: 0" in df_comm_baseline.columns:
                                df_comm_baseline = df_comm_baseline.rename(columns={"Unnamed: 0": "KPI"})
                                
                            if "Unnamed: 0" in df_pros_baseline.columns:
                                if "Unnamed: 1" in df_pros_baseline.columns:
                                    df_pros_baseline = df_pros_baseline.rename(columns={"Unnamed: 0": "KPI", "Unnamed: 1": "Prosumer"})
                                else:
                                    df_pros_baseline = df_pros_baseline.rename(columns={"Unnamed: 0": "KPI"})
                                    
                            # Llenar los vacíos (NaN) causados por las celdas combinadas en Excel
                            if "KPI" in df_pros_baseline.columns:
                                df_pros_baseline["KPI"] = df_pros_baseline["KPI"].ffill()
                                
                            # Limpiar la columna 'Source' para que no aparezca en la web
                            if "Source" in df_comm_baseline.columns:
                                df_comm_baseline = df_comm_baseline.drop(columns=["Source"])
                            if "Source" in df_pros_baseline.columns:
                                df_pros_baseline = df_pros_baseline.drop(columns=["Source"])

                            st.markdown("#### Community Results")
                            st.dataframe(df_comm_baseline, use_container_width=True)

                            st.markdown("#### Prosumer KPIs")
                            st.dataframe(df_pros_baseline, use_container_width=True)
                    else:
                        st.error(f"Could not find Baseline_KPI_results.xlsx in {full_folder_path}/KPI_results_baseline")


            ##########################################################
            # PLOT EXPLORER (Standalone)
            ##########################################################
            
            st.divider()
            st.markdown("### Plot Explorer")
            st.write("Browse all generated plots freely across any experiment.")

            results_base_dir = "Results/Results_DOE"
            if os.path.exists(results_base_dir):
                all_experiments = [d for d in os.listdir(results_base_dir) if os.path.isdir(os.path.join(results_base_dir, d))]
                all_experiments.sort()
            else:
                all_experiments = []

            if all_experiments:
                category_mapping = {
                    "CI Plots": "CI_plots/Prosumer_KPIs/Grouped_CI_plots",
                    "Pareto Plots": "Pareto_plots",
                    "Sobol Plots": "Sobol_plots"
                }

                if "global_plot_idx" not in st.session_state:
                    st.session_state.global_plot_idx = 0

                def reset_global_idx():
                    st.session_state.global_plot_idx = 0

                col_exp, col_cat = st.columns(2)
                
                with col_exp:
                    selected_exp = st.selectbox(
                        "1. Select Experiment Folder:",
                        options=all_experiments,
                        key="global_exp_select",
                        on_change=reset_global_idx
                    )
                    
                with col_cat:
                    selected_cat_name = st.radio(
                        "2. Select Plot Category:",
                        options=list(category_mapping.keys()),
                        horizontal=True,
                        key="global_cat_select",
                        on_change=reset_global_idx
                    )

                actual_subfolder = category_mapping[selected_cat_name]
                plot_folder = os.path.join(results_base_dir, selected_exp, "Plots", actual_subfolder)

                if os.path.exists(plot_folder):
                    imgs = [f for f in os.listdir(plot_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
                    
                    if imgs:
                        imgs.sort()
                        safe_idx = st.session_state.global_plot_idx % len(imgs)

                        def sync_global_drop():
                            st.session_state.global_plot_idx = imgs.index(st.session_state.global_plot_drop)

                        def move_global_idx(step, total):
                            st.session_state.global_plot_idx = (st.session_state.global_plot_idx + step) % total

                        st.write("")
                        c1, c2, c3 = st.columns([1, 4, 1])

                        with c1:
                            st.write("") 
                            st.write("")
                            st.button("⬅️ Prev", key="global_prev", on_click=move_global_idx, args=(-1, len(imgs)), use_container_width=True)

                        with c2:
                            st.selectbox(
                                "3. Select Plot:",
                                options=imgs,
                                format_func=lambda x: x.replace('.png', '').replace('.jpg', '').replace('_', ' '),
                                index=safe_idx,
                                key="global_plot_drop",
                                on_change=sync_global_drop
                            )

                        with c3:
                            st.write("") 
                            st.write("")
                            st.button("Next ➡️", key="global_next", on_click=move_global_idx, args=(1, len(imgs)), use_container_width=True)

                        current_img_file = imgs[st.session_state.global_plot_idx % len(imgs)]
                        st.image(os.path.join(plot_folder, current_img_file), use_column_width=True)
                    
                    else:
                        st.info(f"No images found inside: {actual_subfolder} for experiment {selected_exp}")
                else:
                    st.warning(f"Could not find the folder: {plot_folder}")
            else:
                st.error("No experiment folders found in Results/Results_DOE.")


            ##########################################################
            # COMPARISON 3 PLOTS
            ##########################################################
            st.divider()
            st.markdown("### Multi comparison of plots")
            st.write("Independently select any experiment and plot for each column to build your own custom comparison.")

            if all_experiments:
                free_cols = st.columns(3)

                for col_idx in range(3):
                    with free_cols[col_idx]:
                        with st.container(border=True):
                            st.markdown(f"<h5 style='text-align: center;'>Panel {col_idx + 1}</h5>", unsafe_allow_html=True)
                            
                            chosen_exp = st.selectbox(
                                "Experiment:", 
                                options=all_experiments, 
                                key=f"free_exp_{col_idx}"
                            )
                            
                            chosen_cat = st.selectbox(
                                "Plot Category:", 
                                options=list(category_mapping.keys()), 
                                key=f"free_cat_{col_idx}"
                            )
                            
                            actual_free_folder = category_mapping[chosen_cat]
                            free_plot_dir = os.path.join(results_base_dir, chosen_exp, "Plots", actual_free_folder)
                            
                            if os.path.exists(free_plot_dir):
                                free_imgs = [f for f in os.listdir(free_plot_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
                                
                                if free_imgs:
                                    free_imgs.sort()
                                    chosen_img = st.selectbox(
                                        "Select Plot:", 
                                        options=free_imgs, 
                                        format_func=lambda x: x.replace('.png', '').replace('.jpg', '').replace('_', ' '),
                                        key=f"free_img_{col_idx}"
                                    )
                                    
                                    st.write("") 
                                    st.image(os.path.join(free_plot_dir, chosen_img), use_column_width=True)
                                else:
                                    st.info("No images inside this category.")
                            else:
                                st.warning("Folder not found.")
            else:
                st.error("No experiment folders found in Results/Results_DOE.")
    else:
        st.warning("No result folders found in Results/Results_DOE.")

# ---------------------------------------------------------
# TAB 2: THE ASYNCHRONOUS LAUNCHER
# ---------------------------------------------------------
with tab2:
    st.header("Configure New Simulation")
    st.write("Set up your input data and parameters before launching the Monte Carlo simulation.")
    
    # 1. DATA SOURCE SELECTION
    st.markdown("### 1. Input Data Source")
    data_source = st.radio(
        "Choose your data configuration:", 
        ["Use Default Dataset", "Upload Custom Dataset"], 
        horizontal=True
    )
    
    simulation_files = {}

    if data_source == "Use Default Dataset":
        st.success("Default dataset selected. The standard 5-user baseline is being loaded.")
        
        # --- 1. LOAD DEFAULT DATA USING BACKEND FUNCTIONS ---
        with st.spinner("⏳ Loading and processing default datasets... This may take a moment."):
            folder_name = 'Datasets/Default'

            # Weather Data
            file_pv = 'Photovoltaic_generation_data_EU_PVGIS.csv'
            file_wt = 'Wind_generation_data_Ninja_database.csv'
            USR_PV = process_pvgis_data(f"{folder_name}/{file_pv}")
            USR_WT = process_ninja_wind_data(f"{folder_name}/{file_wt}")

            # Market Prices
            file_BP = 'Spanish_Buying_price_ESIOS.csv'
            file_SP = 'Spanish_Selling_price_ESIOS.csv'
            BP_array = process_esios_price_data(f"{folder_name}/{file_BP}", price_name="Buying Price")
            SP_array = process_esios_price_data(f"{folder_name}/{file_SP}", price_name="Selling Price")

            # Load Profile (5 default users)
            # Note: Ensure the path matches exactly where your consumption folders are
            C = loading_all_consumptions("Datasets/Default/ConsumptionProsumer", 5)
            
        # Display a clean mathematical summary to reassure the user
        with st.expander("📊 View Loaded Data Summary", expanded=False):
            st.write(f"**Consumption Array Shape:** `{C.shape}` *(Prosumers, Time, Value)*")
            st.info("Value=0 is timestamp datatype object and Value=1 is the kWh datatype object.")
            st.success("All data loaded successfully into memory. Ready for Stochastic Simulation.")
            
    else:
        st.markdown("#### Custom Data Mapping")
        
        # --- FORMATTING INSTRUCTIONS (Hidden in an expander to save space) ---
        with st.expander("⚠️ Read Formatting Instructions for Custom Data", expanded=True):
            st.markdown("""
            **General Generation & Price Files (PV, Wind, Buy, Sell):**
            * Must contain exactly two columns.
            * Column 1 name: `Datetime` (Format: `YYYY-MM-DD HH:MM:SS`).
            * Column 2 name: `Value`.

            **Master Consumption File (Scalable for N-Users):**
            * To add multiple users, use a **single file**.
            * Column 1 name: `Datetime`.
            * All remaining columns will be automatically treated as individual users. 
            * Name the headers exactly as you want the users named (e.g., `User_1`, `User_2`, `Factory_A`).
                        
            **IMPORTANT: Avoiding Garbage-In --> Garbage-Out**
            * If one uploads customed input data, first one has to verify it with the Stochastic Analysis Tab.
            * One needs to visualy verify that Empirical Cummulative Function Distribution (ECFD) is adequate for the costum data.
            * !!! The costum data must be of at least one year.
            """)
            
        # Scan the Datasets directory for custom folders
        dataset_base_dir = "Datasets"
        if not os.path.exists(dataset_base_dir):
            os.makedirs(dataset_base_dir)
            
        available_dataset_folders = [d for d in os.listdir(dataset_base_dir) if os.path.isdir(os.path.join(dataset_base_dir, d))]
        
        if available_dataset_folders:
            selected_custom_folder = st.selectbox("Select your custom dataset folder:", available_dataset_folders)
            custom_folder_path = os.path.join(dataset_base_dir, selected_custom_folder)
            available_files = [f for f in os.listdir(custom_folder_path) if f.endswith(('.csv', '.xlsx', '.xls'))]
            
            if available_files:
                st.write("Map your files to the corresponding variables:")
                col1, col2 = st.columns(2)
                
                with col1:
                    simulation_files["PV"] = st.selectbox("PV Generation File:", available_files, key="map_pv")
                    simulation_files["Wind"] = st.selectbox("Wind Generation File:", available_files, key="map_wind")
                    
                with col2:
                    simulation_files["Buy"] = st.selectbox("Buying Price File:", available_files, key="map_buy")
                    simulation_files["Sell"] = st.selectbox("Selling Price File:", available_files, key="map_sell")
                    
                st.divider()
                
                simulation_files["Consumptions"] = st.selectbox(
                    "Master Consumption File (Contains all user columns):", 
                    available_files, 
                    key="map_cons"
                )
            else:
                st.error(f"No valid data files (.csv, .xlsx) found inside {custom_folder_path}.")
        else:
            st.warning(f"No custom folders found. Please create a folder inside the '{dataset_base_dir}' directory and add your files.")

   # 2. SIMULATION PARAMETERS
    st.divider()
    st.markdown("### 2. Simulation Parameters")
    
    # ---> AQUÍ ESTÁ LA LÍNEA MÁGICA QUE FALTABA <---
    param_tab_comm, param_tab_pros = st.tabs(["🏙️ Community Data", "🏠 Prosumers Data"])
    
    with param_tab_comm:
        st.markdown("#### Editable Community Parameters")
        st.write("Adjust the investment costs, asset lifespans, reference capacities, and grid strategy. Fixed economic and emission parameters are protected.")
        
        # Organizamos los inputs en 4 columnas limpias
        col_cost, col_life, col_cap, col_grid = st.columns(4)
        
        with col_cost:
            st.markdown("**Investment Costs (€)**")
            uic_pv = st.number_input("PV Cost (UIC_PV)", value=1000.0, step=50.0)
            uic_wt = st.number_input("Wind Cost (UIC_WT)", value=2000.0, step=50.0)
            uic_b = st.number_input("Battery Cost (UIC_B)", value=800.0, step=50.0)

        with col_life:
            st.markdown("**Lifetimes (Years)**")
            ul_pv = st.number_input("PV Panels (UL_PV)", value=25.0, step=1.0)
            ul_wt = st.number_input("Wind Turbines (UL_WT)", value=30.0, step=1.0)
            ul_b = st.number_input("Batteries (UL_B)", value=10.0, step=1.0)
            
        with col_cap:
            st.markdown("**Capacities (kW/kWh)**")
            pw_pv_pr = st.number_input("PV (pw_pv_pr)", value=0.0, step=0.1)
            pw_wt_pr = st.number_input("Wind (pw_wt_pr)", value=1.5762, step=0.1, format="%.4f")
            ic_pr = st.number_input("Battery (ic_pr)", value=0.0, step=0.1)
            
        with col_grid:
            st.markdown("**Grid Strategy**")
            bp_charging = st.number_input("Charge Threshold (€)", value=0.1677, step=0.01, format="%.4f", help="Threshold buying price from the grid to allow charging")

        # Reconstruimos los arrays dinámicamente conectando TUS variables a las elecciones del usuario
        parameters_values = [
            uic_pv, ul_pv, uic_wt, ul_wt, uic_b, ul_b, 0.15, 0.15, 1, 
            pw_pv_pr, pw_wt_pr, ic_pr, bp_charging, 1887, 1235, 55, 0.308
        ]

        param_names = [
            "UIC_PV", "UL_PV", "UIC_WT", "UL_WT", "UIC_B", "UL_B", 
            "MCH", "MDCH", "PR", "pw_pv_pr", "pw_wt_pr", "ic_pr", "BP_charging_allowed", 
            "CO2_eq_upfront_PV", "CO2_eq_upfront_WT", "CO2_eq_upfront_batt", "CO2_eq_emission_grid"
        ]

        descriptions = [
            "Unit Investment Cost PV (€/kW)", "Useful Life PV (years)",
            "Unit Investment Cost Wind (€/kW)", "Useful Life Wind (years)",
            "Unit Investment Cost Battery (€/kWh)", "Useful Life Battery (years)",
            "Maintenance Cost (fraction of CAPEX)", "Maintenance Cost (fraction of CAPEX)",
            "Performance Ratio", "Installed PV Prosumer (reference)", 
            "Installed Wind Prosumer (reference)", "Installed Battery Prosumer (reference)",
            "Threshold buying price from the grid to allow charging",
            "Fixed CO2 eq. mass of PV installation (CO2 eq / KW installed)",
            "Fixed CO2 eq. mass of WT installation (CO2 eq / KW installed)",
            "Fixed CO2 eq. mass of BATT installation (CO2 eq / KW installed)",
            "CO2 eq emission of the Spanish grid (CO2 eq / KHh)"
        ]

        # Generamos el DataFrame final
        df_EC_parameters = pd.DataFrame({
            'Variable': param_names,
            'Value': parameters_values,
            'Description': descriptions
        })
        df_EC_parameters.set_index('Variable', inplace=True)
        
        # Mostramos la matriz completa al usuario de forma segura
        with st.expander("View Final Community Parameter Matrix"):
            st.dataframe(df_EC_parameters, use_container_width=True)
            
    
    with param_tab_pros:
        st.markdown("#### Prosumer Configuration")
        st.write("Define the parameters for each prosumer. You can edit the table directly, copy-paste from Excel, or change the number of prosumers below.")
        
        # 1. Define community size dynamically
        num_pros = st.number_input("Number of Prosumers in Community:", min_value=1, max_value=1000, value=5, step=1)
        
        # 2. Build the default data matrix
        # We pre-fill the exact values from your default CSV for the first 5 users
        default_data = {
            "Prosumer ID": [f"Prosumer_{i+1}" for i in range(num_pros)],
            "alpha": [0.2] * num_pros,
            "MPW_PV": [15.0] * num_pros,
            "MPW_WT": [15.0] * num_pros,
            "ME_B": [10.0] * num_pros,
            "pw_pv": [0.0] * num_pros, 
            "pw_wt": [0.0] * num_pros,
            "ic_B": [0.0] * num_pros,
            "tariff": [3.0] * num_pros
        }
        
        # Inject your specific default reference capacities if we have at least 5 prosumers
        if num_pros >= 5:
            default_data["pw_pv"][0:5] = [0.3971, 0.0, 0.1195, 0.2784, 0.3542]
            default_data["pw_wt"][0:5] = [0.0948, 1.8300, 1.5111, 0.1940, 0.3720]
            
        df_default_pros = pd.DataFrame(default_data)
        
        # 3. File Uploader for Power Users
        st.markdown("**Option A: Upload existing configuration (CSV)**")
        uploaded_pros_csv = st.file_uploader("Upload Prosumer CSV (Optional)", type=["csv"], help="Upload a CSV with Prosumers as rows and parameters as columns.")
        
        if uploaded_pros_csv is not None:
            # If they upload a file, override the default dataframe
            df_default_pros = pd.read_csv(uploaded_pros_csv)
        
        # 4. THE INTERACTIVE GRID
        st.markdown("**Option B: Interactive Data Grid (Double-click to edit, or copy-paste from Excel)**")
        edited_df_pros = st.data_editor(
            df_default_pros,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" # This allows the user to add or delete rows visually!
        )
        
        # 5. BACKEND TRANSLATION
        # When they click "Execute", we format this visual table back into the exact NumPy 
        # matrix shape your backend expects: (parameters, prosumers)
        st.divider()
        with st.expander("👀 View Backend Matrix Shape (For Verification)"):
            # Drop the string names, convert to numpy, and transpose
            members_data = edited_df_pros.drop(columns=["Prosumer ID"]).to_numpy().T
            row_names = edited_df_pros.columns[1:].to_numpy()
            
            st.write(f"**Members Data Shape:** `{members_data.shape}`")
            st.write(f"**Row Names (Parameters):** `{row_names}`")
            st.success("Matrix is perfectly formatted and ready for the simulator.")
        
    # 3. SENSITIVITY ANALYSIS (DoE BUILDER)
    st.divider()
    st.markdown("### 3. Sensitivity Analysis (DoE Builder)")
    st.write("Select the factors you want to sweep. Unselected factors will remain fixed at their baseline values.")

    # A. Valores Base por Defecto (Para los factores NO seleccionados)
    baseline_defaults = {
        "Season": ["Winter", "Spring", "Summer", "Autumn"], 
        "P2P Method": ["Market"],
        "Battery": [0.0],
        "Tariff": [1.0],       
        "Consumption": [1.0],  
        "PV Installed": [0.0], 
        "WT Installed": [1.5762] 
    }

# B. Selección de Factores Activos
    available_factors = ["Season", "P2P Method", "Battery", "Tariff", "Consumption", "PV Installed", "WT Installed"]
    selected_factors = st.multiselect(
        "Choose factors to include in the Full Factorial matrix:", 
        options=available_factors, 
        default=["P2P Method", "Battery"]
    )

    # Inicializamos la matriz DoE con los "Baselines"
    # 0 = Baseline para los factores numéricos
    final_doe_dict = {
        "Season": ["Winter", "Spring", "Summer", "Autumn"], 
        "P2P Method": ["Market"],
        "Battery": [0],
        "Tariff": [0],       
        "Consumption": [0],  
        "PV Installed": [0], 
        "WT Installed": [0] 
    }

    # NUEVO: Diccionario maestro para traducir los niveles en el backend
    level_master_dict = {}
    valid_configuration = True

    if selected_factors:
        st.markdown("#### Configure Selected Factors")
        
        for factor in selected_factors:
            with st.container(border=True):
                
                if factor == "Season":
                    chosen_seasons = st.multiselect("Select Seasons:", ["Winter", "Spring", "Summer", "Autumn"], default=["Winter", "Spring", "Summer", "Autumn"], key="cfg_season")
                    if not chosen_seasons: valid_configuration = False; st.error("⚠️ Select at least one Season.")
                    else: final_doe_dict[factor] = chosen_seasons
                    
                elif factor == "P2P Method":
                    chosen_p2p = st.multiselect("Select P2P Methods:", ["Market", "One price", "Social", "Environmental"], default=["Market", "One price", "Social", "Environmental"], key="cfg_p2p")
                    if not chosen_p2p: valid_configuration = False; st.error("⚠️ Select at least one P2P Method.")
                    else: final_doe_dict[factor] = chosen_p2p
                    
                elif factor in ["Tariff", "Consumption"]:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        var_pct = st.number_input(f"{factor} Variance (%)", min_value=1, max_value=100, value=20, step=1, key=f"cfg_var_{factor}")
                    with col2:
                        st.info(f"DoE Matrix will use levels: **1 (-{var_pct}%)**, **2 (Baseline)**, and **3 (+{var_pct}%)**")
                        
                    # En la matriz ponemos 1, 2, 3
                    final_doe_dict[factor] = [1, 2, 3] 
                    
                    # En el diccionario guardamos los multiplicadores matemáticos
                    low_val = round(1.0 - (var_pct / 100.0), 2)
                    high_val = round(1.0 + (var_pct / 100.0), 2)
                    level_master_dict[factor] = {
                        1: low_val,
                        2: 1.0,
                        3: high_val
                    }
                    
                elif factor in ["PV Installed", "WT Installed", "Battery"]:
                    col_levels, _ = st.columns([1, 2])
                    with col_levels:
                        num_levels = st.number_input(f"Number of levels for {factor}:", min_value=1, max_value=10, value=3, step=1, key=f"cfg_nl_{factor}")
                    
                    # En la matriz iteramos entre 1, 2, 3...
                    final_doe_dict[factor] = list(range(1, num_levels + 1))
                    
                    ref_var = "pw_pv_pr"
                    if factor == "WT Installed": ref_var = "pw_wt_pr"
                    if factor == "Battery": ref_var = "ic_pr"
                    
                    safe_num_pros = num_pros if 'num_pros' in locals() else 5
                    
                    default_level_data = {
                        "Level ID": [i+1 for i in range(num_levels)],
                        ref_var: [0.0] * num_levels
                    }
                    for p in range(safe_num_pros): default_level_data[f"Prosumer_{p+1}"] = [0.0] * num_levels
                        
                    if factor == "WT Installed":
                        default_level_data[ref_var] = [1.5762 + (i * 0.5) for i in range(num_levels)]
                        
                    df_levels = pd.DataFrame(default_level_data)
                    edited_levels = st.data_editor(df_levels, use_container_width=True, hide_index=True, key=f"editor_{factor}")
                    
                    # Convertimos el dataframe a un diccionario usando el "Level ID" como llave
                    edited_levels.set_index("Level ID", inplace=True)
                    level_master_dict[factor] = edited_levels.to_dict('index')

    # --- BASELINE CONFIGURATION: let the user choose what counts as "baseline" ---
    st.markdown("#### 🎯 Baseline Configuration")
    st.write("Choose which level of each active factor represents your baseline scenario (used for the Baseline KPI export and CI plots).")

    baseline_p2p_choice = "Market"
    baseline_levels_choice = {}

    with st.container(border=True):
        if "P2P Method" in selected_factors and final_doe_dict.get("P2P Method"):
            available_p2p = final_doe_dict["P2P Method"]
            default_idx = available_p2p.index("Market") if "Market" in available_p2p else 0
            baseline_p2p_choice = st.selectbox(
                "Baseline P2P Method:", options=available_p2p, index=default_idx, key="baseline_p2p"
            )

        for factor in ["Tariff", "Consumption"]:
            if factor in selected_factors:
                levels = final_doe_dict[factor]  # [1, 2, 3]
                mults = level_master_dict.get(factor, {})
                options_labels = [f"Level {lvl} ({mults.get(lvl, 1.0):.2f}x)" for lvl in levels]
                default_idx = levels.index(2) if 2 in levels else 0
                chosen_label = st.selectbox(
                    f"Baseline level for {factor}:", options=options_labels, index=default_idx, key=f"baseline_{factor}"
                )
                baseline_levels_choice[factor] = levels[options_labels.index(chosen_label)]

        for factor in ["Battery", "PV Installed", "WT Installed"]:
            if factor in selected_factors:
                levels = final_doe_dict[factor]  # [1, 2, ..., n]
                ref_var = {"Battery": "ic_pr", "PV Installed": "pw_pv_pr", "WT Installed": "pw_wt_pr"}[factor]
                level_rows = level_master_dict.get(factor, {})
                options_labels = [f"Level {lvl} ({ref_var}={level_rows.get(lvl, {}).get(ref_var, 0):.4f})" for lvl in levels]

                default_idx = 0
                for idx, lvl in enumerate(levels):
                    if abs(level_rows.get(lvl, {}).get(ref_var, 0)) < 1e-9:
                        default_idx = idx
                        break

                chosen_label = st.selectbox(
                    f"Baseline level for {factor}:", options=options_labels, index=default_idx, key=f"baseline_{factor}"
                )
                baseline_levels_choice[factor] = levels[options_labels.index(chosen_label)]



    # D. Cálculo de Tamaño de Matriz y Tiempos
    if valid_configuration:
        num_runs = 1
        for levels in final_doe_dict.values():
            num_runs *= len(levels)
            
        est_hours = (num_runs * 2) / 60 
        
        st.write("") 
        if num_runs > 600:
            st.error(f"**Warning:** Matrix size is **{num_runs} experiments**. Estimated time: **{est_hours:.1f} hours**. Consider reducing levels or active factors.")
        else:
            st.success(f"✅ Matrix size: **{num_runs} experiments**. Estimated time: **{est_hours:.1f} hours**.")
            
        with st.expander("👀 View DoE Matrix Preview"):
            preview_matrix = generate_dynamic_doe(final_doe_dict)
            st.dataframe(preview_matrix, use_container_width=True)
    else:
        num_runs = 0
        st.warning("Please resolve the errors above before the DoE Matrix can be generated.")


    # 4. MONTE CARLO SETTINGS
    st.divider()
    st.markdown("### 4. Monte Carlo Settings")
    st.write("Configure the stochastic engine parameters.")
    
    col_mc1, col_mc2, col_mc3 = st.columns(3)
    with col_mc1:
        num_iterations = st.number_input("Number of Iterations:", min_value=1, value=200, step=10, help="Number of Monte Carlo simulations per experiment.")
    with col_mc2:
        n_days = st.number_input("Days per Season:", min_value=1, max_value=365, value=31, step=1, help="Number of days evaluated in each season.")
    with col_mc3:
        sim_seed = st.number_input("Random Seed:", value=10, step=1, help="Fixes the random generation to make the experiment repeatable.")

    # 5. LAUNCH BUTTON (Versión Asíncrona Segura)
    st.divider()
    
    disable_launch = (not valid_configuration) or (num_runs == 0)
    
    # Importamos herramientas de hilos para ejecutar en segundo plano
    import threading
    import json
    
    PROGRESS_FILE = "Results/current_simulation_status.json"
    
    # Comprobamos si ya hay una simulación ejecutándose en segundo plano
    is_running = False
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                status = json.load(f)
                
                if status.get("status") == "running":
                    is_running = True
                elif status.get("status") == "failed":
                    # This will print the exact python error on your screen!
                    st.error(f"❌ El hilo de fondo falló con este error: {status.get('error')}")
                    
                    if st.button("Limpiar Error"):
                        os.remove(PROGRESS_FILE)
                        st.rerun()
        except:
            pass
         
    if is_running:
        st.warning("⏳ Hay una simulación de larga duración ejecutándose actualmente en segundo plano...")
        
        # Leemos el archivo de progreso para mostrarle al usuario cómo va desde la última vez
        with open(PROGRESS_FILE, 'r') as f:
            status = json.load(f)
        
        st.metric("Experimento Actual", f"{status.get('current')}/{status.get('total')}")
        progress_pct = min(1.0, status.get('current') / status.get('total'))
        st.progress(progress_pct)
        st.info(f"Iniciada el: {status.get('start_time')}. Puedes cerrar esta web con total tranquilidad, la simulación seguirá ejecutándose en el servidor.")
        
        # Botón para forzar la liberación si se quedase colgado por algún motivo externo
        if st.button("❌ Cancelar / Resetear Monitor"):
            os.remove(PROGRESS_FILE)
            st.rerun()
            
    else:
        if st.button("🚀 Execute Digital Twin (En segundo plano)", type="primary", use_container_width=True, disabled=disable_launch):
            
            final_doe_matrix = generate_dynamic_doe(final_doe_dict)
            members_data = edited_df_pros.drop(columns=["Prosumer ID"]).to_numpy().T
            
            safe_num_pros = C.shape[0]

            master_data_map = {
                'Solar': split_into_seasons(USR_PV),
                'Wind': split_into_seasons(USR_WT),
                'BP': split_into_seasons(BP_array),
                'SP': split_into_seasons(SP_array)
            }
            for i in range(safe_num_pros):
                master_data_map[f'C{i+1}'] = split_into_seasons(C[i, :, :])

            from datetime import datetime
            experiment_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

            init_status = {
                "status": "running",
                "current": 0,
                "total": len(final_doe_matrix),
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            os.makedirs("Results", exist_ok=True)
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(init_status, f)

            def run_in_background():
                try:
                    fullfactorial_app(
                        doe_matrix=final_doe_matrix,
                        level_master_dict=level_master_dict,
                        number_iterations=num_iterations,
                        n_days=n_days,
                        prosumer_based_data=members_data, 
                        df_EC_parameters=df_EC_parameters, 
                        master_data_map=master_data_map, 
                        seed=sim_seed,
                        experiment_timestamp=experiment_timestamp
                    )

                    # Post-processing: baseline KPI export + CI/Pareto/Sobol plots
                    run_postprocessing_app(
                        final_doe_matrix, experiment_timestamp,
                        baseline_p2p=baseline_p2p_choice,
                        baseline_levels=baseline_levels_choice
                    )

                    with open(PROGRESS_FILE, 'w') as f:
                        json.dump({"status": "completed"}, f)
                except Exception as e:
                    with open(PROGRESS_FILE, 'w') as f:
                        json.dump({"status": "failed", "error": str(e)}, f)

            simulation_thread = threading.Thread(target=run_in_background, daemon=True)
            simulation_thread.start()
            
            st.success("🎉 ¡Simulación enviada con éxito al motor de segundo plano!")
            st.info("El hilo paralelo ya está calculando las matemáticas. Puedes cerrar el navegador de forma segura. Vuelve mañana a esta pestaña para comprobar los resultados.")
            st.rerun()