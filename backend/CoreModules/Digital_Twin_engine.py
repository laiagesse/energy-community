#######################################################################################
#######################################################################################
############################Digital_Twin_engine########################################
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

def checking_producer_or_consumer(prosumer, time_period, time_based_data, prosumer_based_data, E_pv_pr,  E_wt_pr):
    alpha = prosumer_based_data[0, prosumer-1]
    energy_PV = time_based_data[prosumer-1, 4, time_period]
    energy_wind = time_based_data[prosumer-1, 5, time_period]

    ### Calculating generated Energy (E_total) and Consumption (C)
    C = time_based_data[prosumer-1, 0, time_period]
    E_total_PV = energy_PV + alpha * E_pv_pr[time_period]
    E_total_WT = energy_wind + alpha * E_wt_pr[time_period]
    E_total = E_total_PV + E_total_WT

    ##Consumminf from Own Generation
    if E_total >= C:
        E_surplus = E_total - C
        load = 0 
        bl = 1
    else:
        E_surplus = 0
        load = C - E_total
        bl = 0
        
    return C, E_total_PV, E_total_WT, bl, E_surplus, load



def charging_private_battery(prosumer, time_period, time_based_data, prosumer_based_data, df_EC_parameters, E_surplus, e_B, load, charging_batt_from_grid):
    
    ##Obtaining the needed values
    charged = 0
    ic = prosumer_based_data[6, prosumer-1]
    MCH = df_EC_parameters.loc['MCH', 'Value']
    BP_charging_allowed = df_EC_parameters.loc['BP_charging_allowed', 'Value']
    current_BP = time_based_data[prosumer-1, 2, time_period]
    load_bat =0 
    discharging_needed = 1 if load > 0 else 0
    
    ##We only charge if we have batteries
    if ic <= 0:
       return E_surplus, 0, 0, 0
    
    ##Inicial battery storage
    if time_period == 0:
        e_B = ic

    ##Battery charge from Generetion
    if E_surplus>0:
        charged = 1
        if (E_surplus <= (ic-e_B)) & (E_surplus <= MCH*ic):
            e_B_next = E_surplus + e_B ## from next time period
            E_surplus = 0
        elif (E_surplus >= (ic-e_B)) & ((ic-e_B) <= MCH*ic):
            E_surplus = E_surplus - (ic-e_B)
            e_B_next = ic
        else:
            E_surplus = E_surplus - MCH*ic
            e_B_next = e_B + ic*MCH
    else:
        e_B_next = e_B
    
    ## Battery charge from the grid
    if (current_BP < BP_charging_allowed) & (charging_batt_from_grid == True) & (discharging_needed == 0 ):
        remaining_space = ic - e_B_next
        energy_already_charged = e_B_next - e_B
        remaining_rate = (MCH * ic) - energy_already_charged
        
        if (remaining_space > 0) and (remaining_rate > 0):
            charged = 1
            load_bat = np.minimum(remaining_space, remaining_rate)
            e_B_next += load_bat
        
    return E_surplus, e_B_next, load_bat, charged


def discharging_private_battery(p_index, e_B, prosumer_based_data, df_EC_parameters, load, charged):
    
    ##We only discharge if battery has energy
    ic = prosumer_based_data[6, p_index]
    if ic <= 0:
        return e_B, load, 0
    
    E_batt = 0
    MDCH = df_EC_parameters.loc['MDCH', 'Value']
    ic = prosumer_based_data[6, p_index]

    ##Battery discharge logic
    if load>0:
        discharged = min(e_B, load, (ic * MDCH))
        e_B_next = e_B - discharged
        E_batt = min((ic * MDCH) - discharged, e_B_next)
        load = load - discharged
    elif load <= 0 and charged == 0:
        e_B_next = e_B
        E_batt = min(ic * MDCH, e_B_next)
    else:
        e_B_next = e_B

    return e_B_next, load, E_batt



#######################################################################################
##2.Energy Community level
#######################################################################################


#Groups and sorts buyers and sellers by price categories
def group_and_sort_vectors(original_prices, ascending=True, boolean_mask=None): 
    """
    Attaches original indices to prices.
    Filters by mask (if provided).The mask is an optional boolean array in case we only want to group seller/buyers data
    Sorts by price (Ascending).
    Groups indices by unique prices.
    """
    num_prosumers = len(original_prices)
    og_indices = np.arange(num_prosumers)
    
    # Combines [Index, Price]
    data = np.column_stack((og_indices, original_prices))
    
    # Filters by mask if provided (mask is in original order)
    if boolean_mask is not None:
        # We use the boolean mask directly on the stacked data
        data = data[boolean_mask.astype(bool)]
    
    if data.size == 0:
        return np.empty((0, 2), dtype=object)
    
    # Sorts by the second column (Price)

    sorted_indices = np.argsort(data[:, 1], kind='stable')
    sorted_data = data[sorted_indices]
    
    
    # Groups by Unique Prices
    unique_prices, inverse_mapping = np.unique(sorted_data[:, 1], return_inverse=True)
    
    # Creates the result object array
    result = np.empty((len(unique_prices), 2), dtype=object)
    
    for i in range(len(unique_prices)):
        # Extracts IDs belonging to this unique price
        group_ids = sorted_data[inverse_mapping == i, 0].astype(int)
        result[i, 0] = group_ids.tolist()
        result[i, 1] = unique_prices[i]

    if not ascending:
        result = result[::-1]
        
    return result


#Group to group pairing by prices and energy quatities for P2P sharing calculations
def group_to_group_asigning_P2P(f_P2P, total_load, total_E_extra, grouped_seller_ids, grouped_buyers_ids, E_extra_list, load_list):
     
    ## We will have that always at least one of the is fully consumed. That is the limiting array.
    if total_load > total_E_extra:
        real_E_given = total_E_extra
    else:
        real_E_given = total_load

    
    count_sellers = len(grouped_seller_ids)
    count_buyers = len(grouped_buyers_ids)
    
    max_energy_sold = real_E_given/count_sellers ## Per prosumer selling!!! This value can be updated
    max_energy_bought = real_E_given/count_buyers ## Per prosumer buying!!! This value can be updated

    ### Organize Enegy extra and load by capacity and show only the actual buyers and sellers.

    group_sellers_ids = np.array(grouped_seller_ids)
    re_sorted = np.argsort(group_sellers_ids)
    group_sellers_ids = group_sellers_ids[re_sorted]
    group_buyers_ids = np.array(grouped_buyers_ids)
    re_sorted = np.argsort(group_buyers_ids)
    group_buyers_ids = group_buyers_ids[re_sorted]
    E_extra_group = E_extra_list[group_sellers_ids]
    E_extra_array = np.column_stack((group_sellers_ids, E_extra_group))
    load_group = load_list[group_buyers_ids]
    load_array = np.column_stack((group_buyers_ids, load_group))
    sorted_indices_sellers = np.argsort(E_extra_array[:, 1], kind='stable')[::-1]## Descending order
    sorted_indices_buyers = np.argsort(load_array[:, 1], kind='stable')[::-1] ## Descending order
    
    E_extra_sorted = E_extra_array[sorted_indices_sellers]
    load_sorted = load_array[sorted_indices_buyers]
    
    ### Quantity sold per seller
    E_extra_remaining = np.zeros(count_sellers)
    E_extra_remaining += max_energy_sold
    
    ### Quantity bought per buyer
    load_remaining = np.zeros(count_buyers)
    load_remaining += max_energy_bought        

    remaining_to_allocate = real_E_given
    while remaining_to_allocate > 1e-9:
        prev_remaining = remaining_to_allocate
        for seller_index in range(0, count_sellers): 
            sellers_remaining = count_sellers - ( seller_index + 1 )
            buyers_remaining = count_buyers
            for buyer_index in range(0, count_buyers):
                buyers_remaining = buyers_remaining - 1
                
                og_buyer_index = int(load_sorted[buyer_index, 0])
                og_seller_index = int(E_extra_sorted[seller_index, 0])
                
                E_extra = E_extra_sorted[seller_index, 1]
                E_extra_rem = E_extra_remaining[seller_index]
                load = load_sorted[buyer_index, 1]
                load_rem = load_remaining[buyer_index]

                ### We need to check what is the minimum value:
                '''
                The energy shared between the current buyer and seller could be:
                    E_extra: real available energy from selling prosumer
                    E_extra_remaining: from the max amount of energy that the prosumer can share, how much is still available
                    load: real load for the current buyer
                    load_remaining: from the max amount of energy that the buyer can buy, how much is still not covered.
    
                Note that the minimum value between these will be the one that will be shared!!!
                '''

                if E_extra <= 1e-9 or E_extra_rem <= 1e-9:
                    break    # Seller is empty, break out and move to the next SELLER
                if load <= 1e-9 or load_rem <= 1e-9:
                    continue # Buyer is full, skip them and move to the next BUYER
    
                array_check_minimum = np.array([E_extra, E_extra_rem, load, load_rem])
                minimum_value_index = np.argmin(array_check_minimum)
                minimum  = array_check_minimum[minimum_value_index]
                remaining_to_allocate -= minimum
                
                ### Updating the values:
                values_updated = array_check_minimum - minimum
                
                load_sorted[buyer_index, 1] = values_updated[2]
                load_remaining[buyer_index] = values_updated[3]
                load_list[og_buyer_index] = values_updated[2]
                E_extra_sorted[seller_index, 1] = values_updated[0]
                E_extra_list[og_seller_index] = values_updated[0]
                E_extra_remaining[seller_index] = values_updated[1]
                f_P2P[og_seller_index, og_buyer_index] += minimum
    
                if minimum_value_index == 0:
                    E_seller_surplus = E_extra_rem-E_extra
                    E_extra_remaining[seller_index] = 0
                    if sellers_remaining > 0:
                        surplus_per_prosumer = E_seller_surplus / sellers_remaining 
                        for i in range(seller_index+1, count_sellers):
                            E_extra_remaining[i] = E_extra_remaining[i] + surplus_per_prosumer 
    
                elif minimum_value_index == 2:
                    load_surplus = load_rem-load
                    load_remaining[buyer_index] = 0
                    if buyers_remaining > 0:
                        surplus_per_buyer = load_surplus / buyers_remaining
                        for i in range(buyer_index+1, count_buyers):
                            load_remaining[i] = load_remaining[i] + surplus_per_buyer
        if remaining_to_allocate == prev_remaining:
            break        

    return f_P2P, E_extra_list, load_list



#P2P function for market based P2P allocation method
def P2P(time_period, load_list, E_extra_list, E_batt_list, bl_list, time_based, flow_P2P, num_prosumers):

    ### Saving values
    flow_P2P[:, 0, time_period] = E_extra_list.copy()
    flow_P2P[:, 1, time_period] = E_batt_list.copy()
    flow_P2P[:, 2, time_period] = load_list.copy()

    ### Setting the needed arrays:
    OG_index = np.arange(num_prosumers)
    SP = time_based[:, 1, time_period]
    PS = time_based[:, 3, time_period]
    BP = time_based[:, 2, time_period]
    flow_P2P[:, 3, time_period] = SP.copy()
    flow_P2P[:, 4, time_period] = BP.copy()
    flow_P2P[:, 5, time_period] = PS.copy()
    
    f_P2G = np.zeros([num_prosumers])
    f_G2P = np.zeros([num_prosumers])
    f_P2P = np.zeros((num_prosumers, num_prosumers)) ### Row: seller Column: buyer
    f_P2P_batt = np.zeros((num_prosumers, num_prosumers))
    
    ### Ckecking if prosumer will sell to the Energy Community
    seller_list = bl_list.copy()
    seller_list_batt = np.zeros([num_prosumers])
    for seller_id in range(0, num_prosumers):
        if (bl_list[seller_id] == 1) & (PS[seller_id] >= SP[seller_id]):
            seller_list[seller_id] = 1
        elif (bl_list[seller_id] == 1) & (PS[seller_id] <= SP[seller_id]):
            seller_list[seller_id] = 0
            f_P2G[seller_id] = E_extra_list[seller_id]
            E_extra_list[seller_id] = 0
        elif (bl_list[seller_id] == 0) & (E_batt_list[seller_id]>0):
            seller_list_batt[seller_id] = 1

    ### We create sorted arrays but with grouped number of sellers/buyers if they have the same price
    be_list = 1-bl_list
    grouped_PS = group_and_sort_vectors(PS, ascending=True, boolean_mask=seller_list)
    grouped_BP = group_and_sort_vectors(BP, ascending=True, boolean_mask=be_list)
    grouped_PS_batt = group_and_sort_vectors(PS, ascending=True, boolean_mask=seller_list_batt)    

    ### For each buyer we check if it's better to buy to grid or to other prosumers
    for buyer_grouped_ind in range(len(grouped_BP)): ## NOTE: index after sorting!!!!
        for seller_grouped_ind in range(len(grouped_PS)): ## NOTE: index after sorting!!!!
            
            ### Preparing the needed variables:
            seller_og_ids_this_group = grouped_PS[seller_grouped_ind, 0]
            selling_price = grouped_PS[seller_grouped_ind, 1]
            buyer_og_ids_this_group = grouped_BP[buyer_grouped_ind, 0]
            buyer_price = grouped_BP[buyer_grouped_ind, 1]
            
            #Needed load and avalable load for the whole group
            grouped_E_extra = np.sum(E_extra_list[seller_og_ids_this_group])
            grouped_load = np.sum(load_list[buyer_og_ids_this_group])
            
            ### Comparing the buying price to the grid 
            if (grouped_E_extra > 0) & (grouped_load > 0):
                    if buyer_price >= selling_price:
                        f_P2P, E_extra_list, load_list = group_to_group_asigning_P2P(f_P2P, grouped_load, grouped_E_extra, seller_og_ids_this_group, buyer_og_ids_this_group, E_extra_list, load_list)
                    
    flow_P2P[:, 6, time_period] = f_P2G.copy()
    flow_P2P[:, 7:(7+num_prosumers), time_period] = f_P2P.copy()
    flow_P2P[:, 7+num_prosumers , time_period] = E_extra_list.copy()
    flow_P2P[:, 8+num_prosumers, time_period] = load_list.copy()
    flow_P2P[:, 9+num_prosumers, time_period] = E_batt_list.copy()

    original_E_batt = E_batt_list.copy()
    
    for buyer_grouped_ind in range(len(grouped_BP)): ## NOTE: index after sorting!!!!
        for seller_grouped_ind in range(len(grouped_PS_batt)): ## NOTE: index after sorting!!!!
            
            ### Preparing the needed variables:
            seller_og_ids_this_group = grouped_PS_batt[seller_grouped_ind, 0]
            selling_price = grouped_PS_batt[seller_grouped_ind, 1]
            buyer_og_ids_this_group = grouped_BP[buyer_grouped_ind, 0]
            buyer_price = grouped_BP[buyer_grouped_ind, 1]
            
            #Needed load and avalable load for the whole group
            grouped_E_batt = np.sum(E_batt_list[seller_og_ids_this_group])
            grouped_load = np.sum(load_list[buyer_og_ids_this_group])
            
            ### Comparing the buying price to the grid 
            if (grouped_E_batt > 0) & (grouped_load > 0):
                    if buyer_price >= selling_price:
                        f_P2P_batt, E_batt_list, load_list = group_to_group_asigning_P2P(f_P2P_batt, grouped_load, grouped_E_batt, seller_og_ids_this_group, buyer_og_ids_this_group, E_batt_list, load_list)
    
    E_batt_list_end = E_batt_list.copy()      
    
    ### Saving values
    flow_P2P[:, (10+num_prosumers):(10+(2*num_prosumers)) , time_period] = f_P2P_batt.copy()
    flow_P2P[:, (10+2*(num_prosumers)) , time_period] = E_batt_list_end.copy()
    flow_P2P[:, (11+2*(num_prosumers)) , time_period] = load_list.copy()

    ### After looping through all sellers, any remaining load is bought from the grid
    f_G2P = load_list.copy() # Capture the remaining values
    load_list.fill(0)

    f_P2P = f_P2P + f_P2P_batt
    
    ### Will sell to grid
    f_P2G = f_P2G + E_extra_list.copy()
    E_extra_list.fill(0)
    batt_discharge = original_E_batt - E_batt_list_end

    ### Saving values
    flow_P2P[:, (12+2*(num_prosumers)) , time_period] = f_P2G.copy()
    flow_P2P[:, (14+2*(num_prosumers)) , time_period] = f_G2P.copy()
    flow_P2P[:, (15+2*(num_prosumers)) , time_period] = load_list.copy()
    flow_P2P[:, (16+2*(num_prosumers)) , time_period] = E_extra_list.copy()
    
    return f_P2G, f_G2P, f_P2P, PS, flow_P2P, batt_discharge



#P2P function for one-price P2P allocation method
def P2P_one_price(time_period, load_list, E_extra_list, E_batt_list, bl_list, time_based, flow_P2P, num_prosumers):
    flow_P2P[:, 0, time_period] = E_extra_list.copy()
    flow_P2P[:, 1, time_period] = E_batt_list.copy()
    flow_P2P[:, 2, time_period] = load_list.copy()

    ### Setting the needed arrays:
    OG_index = np.arange(num_prosumers)
    SP = time_based[:, 1, time_period]
    PS = time_based[:, 3, time_period]
    BP = time_based[:, 2, time_period]
    flow_P2P[:, 3, time_period] = SP.copy()
    flow_P2P[:, 4, time_period] = BP.copy()

    f_P2G = np.zeros([num_prosumers])
    f_G2P = np.zeros([num_prosumers])
    f_P2P = np.zeros((num_prosumers, num_prosumers)) ### Row: seller Column: buyer
    f_P2P_batt = np.zeros((num_prosumers, num_prosumers))
    E_batt_list_end = np.zeros([num_prosumers])
    
    ### Defining the P2P unique price
    E_offer = np.sum(E_extra_list)
    E_demand = np.sum(load_list)
    
    sum_sell_prices = 0
    count_sellers = 0
    sum_buyers_prices = 0
    count_buyers = 0
    for i in range(0, num_prosumers):
        if bl_list[i]==1:
            sum_sell_prices += SP[i]
            count_sellers += 1
        else:
            sum_buyers_prices += BP[i]
            count_buyers += 1

    if count_sellers != 0:
        SP_average = sum_sell_prices/count_sellers
    else:
        SP_average = 0 ##random number will never be used
    if count_buyers != 0:    
        BP_average = sum_buyers_prices/count_buyers
    else:
        BP_average = 0 ##random number will never be used

    
    if (E_demand + E_offer) > 0:
        P_P2P = ((BP_average + SP_average)/2) + (((E_demand-E_offer)/(E_demand+E_offer))*((BP_average-SP_average)/2))
    else:
        P_P2P = SP_average # Default to selling price if no market activity
    

    ### Ckecking if prosumer will sell to the Energy Community
    seller_list = bl_list.copy()
    seller_list_batt = np.zeros([num_prosumers])        
    for seller_id in range(0, num_prosumers):
        if (bl_list[seller_id] == 1) & (PS[seller_id] >= SP[seller_id]):
            seller_list[seller_id] = 1
        elif (bl_list[seller_id] == 1) & (PS[seller_id] <= SP[seller_id]):
            seller_list[seller_id] = 0
            f_P2G[seller_id] = E_extra_list[seller_id]
            E_extra_list[seller_id] = 0
        elif (bl_list[seller_id] == 0) & (E_batt_list[seller_id]>0):
            seller_list_batt[seller_id] = 1

    ### We create sorted arrays but with grouped number of sellers/buyers if they have the same price
    P_P2P_arr = np.zeros(num_prosumers)
    P_P2P_arr = P_P2P_arr + P_P2P
    flow_P2P[:, 5, time_period] = P_P2P_arr.copy()
    be_list = 1-bl_list
    grouped_BP = group_and_sort_vectors(BP, ascending=False, boolean_mask=be_list) ## Only real buyers, because masked
    grouped_P2P = group_and_sort_vectors(P_P2P_arr, ascending=True, boolean_mask=seller_list) ## Only real sellers, because masked
    grouped_P2P_batt = group_and_sort_vectors(P_P2P_arr, ascending=True, boolean_mask=seller_list_batt)

    ### For each buyer we check if it's better to buy to grid or to other prosumers
    for buyer_grouped_ind in range(len(grouped_BP)): ## NOTE: index after sorting!!!!
        for seller_grouped_ind in range(len(grouped_P2P)): ## NOTE: index after sorting!!!!
            
            ### Preparing the needed variables:
            seller_og_ids_this_group = grouped_P2P[seller_grouped_ind, 0]
            selling_price = grouped_P2P[seller_grouped_ind, 1]
            buyer_og_ids_this_group = grouped_BP[buyer_grouped_ind, 0]
            buyer_price = grouped_BP[buyer_grouped_ind, 1]
            
            #Needed load and avalable load for the whole group
            grouped_E_extra = np.sum(E_extra_list[seller_og_ids_this_group])
            grouped_load = np.sum(load_list[buyer_og_ids_this_group])
            
            ### Comparing the buying price to the grid 
            if (grouped_E_extra > 0) & (grouped_load > 0):
                    if buyer_price >= selling_price:
                        f_P2P, E_extra_list, load_list = group_to_group_asigning_P2P(f_P2P, grouped_load, grouped_E_extra, seller_og_ids_this_group, buyer_og_ids_this_group, E_extra_list, load_list)
    
    flow_P2P[:, 6, time_period] = f_P2G.copy()
    flow_P2P[:, 7:(7+num_prosumers), time_period] = f_P2P.copy()
    flow_P2P[:, 7+num_prosumers , time_period] = E_extra_list.copy()
    flow_P2P[:, 8+num_prosumers, time_period] = load_list.copy()
    flow_P2P[:, 9+num_prosumers , time_period] = E_batt_list.copy()

    original_E_batt = E_batt_list.copy()
    
    for buyer_grouped_ind in range(len(grouped_BP)): ## NOTE: index after sorting!!!!
        for seller_grouped_ind in range(len(grouped_P2P_batt)): ## NOTE: index after sorting!!!!
            
            ### Preparing the needed variables:
            seller_og_ids_this_group = grouped_P2P_batt[seller_grouped_ind, 0]
            selling_price = grouped_P2P_batt[seller_grouped_ind, 1]
            buyer_og_ids_this_group = grouped_BP[buyer_grouped_ind, 0]
            buyer_price = grouped_BP[buyer_grouped_ind, 1]
            
            #Needed load and avalable load for the whole group
            grouped_E_batt = np.sum(E_batt_list[seller_og_ids_this_group])
            grouped_load = np.sum(load_list[buyer_og_ids_this_group])
            
            ### Comparing the buying price to the grid 
            if (grouped_E_batt > 0) & (grouped_load > 0):
                    if buyer_price >= selling_price:
                        f_P2P_batt, E_batt_list, load_list = group_to_group_asigning_P2P(f_P2P_batt, grouped_load, grouped_E_batt, seller_og_ids_this_group, buyer_og_ids_this_group, E_batt_list, load_list)

    E_batt_list_end = E_batt_list.copy()
    
    flow_P2P[:, (10+num_prosumers):(10+(2*num_prosumers)) , time_period] = f_P2P_batt.copy()
    flow_P2P[:, (10+(2*num_prosumers)) , time_period] = E_batt_list_end.copy()
    flow_P2P[:, (11+(2*num_prosumers)) , time_period] = load_list.copy()
       
    ### After looping through all sellers, any remaining load is bought from the grid
    f_G2P = load_list.copy() # Capture the remaining values
    load_list.fill(0)

    f_P2P = f_P2P + f_P2P_batt
    
    ### Will sell to grid
    f_P2G = f_P2G + E_extra_list.copy()
    E_extra_list.fill(0)
    batt_discharge =  original_E_batt- E_batt_list_end 

    ### Saving values
    flow_P2P[:, 12+(2*num_prosumers) , time_period] = f_P2G.copy()
    flow_P2P[:, 14+(2*num_prosumers) , time_period] = f_G2P.copy()
    flow_P2P[:, 15+(2*num_prosumers) , time_period] = load_list.copy()
    flow_P2P[:, 16+(2*num_prosumers) , time_period] = E_extra_list.copy()

    return f_P2G, f_G2P, f_P2P, P_P2P_arr, flow_P2P, batt_discharge



#P2P function social P2P allocation method
def P2P_social(time_period, load_list, E_extra_list, E_batt_list, bl_list, time_based, flow_P2P, num_prosumers, prosumer_based_data, results_data, df_EC_parameters):

    ### Saving values
    flow_P2P[:, 0, time_period] = E_extra_list.copy()
    flow_P2P[:, 1, time_period] = E_batt_list.copy()
    flow_P2P[:, 2, time_period] = load_list.copy()

    ### Setting the needed arrays:
    OG_index = np.arange(num_prosumers)
    SP = time_based[:, 1, time_period]
    PS = time_based[:, 3, time_period]
    BP = time_based[:, 2, time_period]
    flow_P2P[:, 3, time_period] = SP.copy()
    flow_P2P[:, 4, time_period] = BP.copy()
    flow_P2P[:, 5, time_period] = PS.copy()
    
    f_P2G = np.zeros([num_prosumers])
    f_G2P = np.zeros([num_prosumers])
    f_P2P = np.zeros((num_prosumers, num_prosumers)) ### Row: seller Column: buyer
    f_P2P_batt = np.zeros((num_prosumers, num_prosumers))
    
    ### Ckecking if prosumer will sell to the Energy Community
    seller_list = bl_list.copy()
    seller_list_batt = np.zeros([num_prosumers])
    for seller_id in range(0, num_prosumers):
        if (bl_list[seller_id] == 1) & (PS[seller_id] >= SP[seller_id]):
            seller_list[seller_id] = 1
        elif (bl_list[seller_id] == 1) & (PS[seller_id] <= SP[seller_id]):
            seller_list[seller_id] = 0
            f_P2G[seller_id] = E_extra_list[seller_id]
            E_extra_list[seller_id] = 0
        elif (bl_list[seller_id] == 0) & (E_batt_list[seller_id]>0):
            seller_list_batt[seller_id] = 1

    ### We create sorted arrays but with grouped number of sellers/buyers if they have the same price
    be_list = 1-bl_list
    grouped_PS = group_and_sort_vectors(PS, ascending=True, boolean_mask=seller_list)
    grouped_PS_batt = group_and_sort_vectors(PS, ascending=True, boolean_mask=seller_list_batt)    

    if time_period == 0:
        grouped_buyers = group_and_sort_vectors(BP, ascending=True, boolean_mask=be_list)
    else:
        SP_kpi = flow_P2P[:, 3, 0:time_period]
        BP_kpi = flow_P2P[:, 4, 0:time_period]
        price_P2P_kpi = flow_P2P[:, 5, 0:time_period] #(seller, time)
        
        f_P2G_kpi = flow_P2P[:, 12 + 2*num_prosumers, 0:time_period]
        f_G2P_kpi = flow_P2P[:, 14 + 2*num_prosumers, 0:time_period]
        battery_charged_from_grid_kpi = results_data[:, 15 + num_prosumers, 0:time_period]
        
        # To get total sold by each prosumer, sum across the buyers (axis=1 of the P2P block)
        sold_total_P2P_kpi = np.sum(results_data[:, 12 : 12+num_prosumers, 0:time_period], axis=1) 
        
        # Calculate hourly cash flows for all prosumers simultaneously
        revenue_selling_grid = SP_kpi * f_P2G_kpi
        cost_buying_grid = BP_kpi * (f_G2P_kpi + battery_charged_from_grid_kpi)
        revenue_selling_P2P = price_P2P_kpi * sold_total_P2P_kpi
        cost_buying_P2P = np.sum(results_data[:, 12:12+num_prosumers, 0:time_period] * price_P2P_kpi[:, np.newaxis, :], axis=0)
        
        # Calculate the net hourly bills, then SUM across time (axis=1) to get the cumulative total!
        hourly_net_bills = revenue_selling_grid - cost_buying_grid + revenue_selling_P2P - cost_buying_P2P
        cumulative_net_bills = np.sum(hourly_net_bills, axis=1)
        
        # Calculate hypothetical costs and SUM across time (axis=1)
        hourly_hypothetical_costs = results_data[:, 0, 0:time_period] * BP_kpi
        cumulative_hypothetical_costs = np.sum(hourly_hypothetical_costs, axis=1)
    
        # Calculate the final percentage for the sorting algorithm
        bill_reduction_arr = 100 - np.divide(
            cumulative_net_bills * 100, 
            cumulative_hypothetical_costs, 
            out=np.zeros_like(cumulative_hypothetical_costs), 
            where=(cumulative_hypothetical_costs != 0)
        )
        grouped_buyers = group_and_sort_vectors(bill_reduction_arr, ascending=True, boolean_mask=be_list)
        
    ### For each buyer we check if it's better to buy to grid or to other prosumers
    for buyer_grouped_ind in range(len(grouped_buyers)): ## NOTE: index after sorting!!!!

        buyer_og_ids_this_group = np.atleast_1d(grouped_buyers[buyer_grouped_ind, 0]).astype(int)
        
        # Creating a temporary mask for JUST these buyers
        temp_buyer_mask = np.zeros(num_prosumers, dtype=int)
        temp_buyer_mask[buyer_og_ids_this_group] = 1
        subgrouped_buyers = group_and_sort_vectors(BP, ascending=True, boolean_mask=temp_buyer_mask)

        for subgroup_ind in range(len(subgrouped_buyers)):
            subgroup_buyer_ids = np.atleast_1d(subgrouped_buyers[subgroup_ind, 0]).astype(int)
            buyer_price = subgrouped_buyers[subgroup_ind, 1]

            for seller_grouped_ind in range(len(grouped_PS)): ## NOTE: index after sorting!!!!
                
                ### Preparing the needed variables:
                seller_og_ids_this_group = grouped_PS[seller_grouped_ind, 0]
                selling_price = grouped_PS[seller_grouped_ind, 1]
                
                #Needed load and avalable load for the whole group
                grouped_E_extra = np.sum(E_extra_list[seller_og_ids_this_group])
                grouped_load = np.sum(load_list[subgroup_buyer_ids])
                
                ### Comparing the buying price to the grid 
                if (grouped_E_extra > 0) & (grouped_load > 0):
                        if buyer_price >= selling_price:
                            f_P2P, E_extra_list, load_list = group_to_group_asigning_P2P(f_P2P, grouped_load, grouped_E_extra, seller_og_ids_this_group, subgroup_buyer_ids, E_extra_list, load_list)                            
    flow_P2P[:, 6, time_period] = f_P2G.copy()
    flow_P2P[:, 7:(7+num_prosumers), time_period] = f_P2P.copy()
    flow_P2P[:, 7+num_prosumers , time_period] = E_extra_list.copy()
    flow_P2P[:, 8+num_prosumers, time_period] = load_list.copy()
    flow_P2P[:, 9+num_prosumers, time_period] = E_batt_list.copy()

    original_E_batt = E_batt_list.copy()
    
    for buyer_grouped_ind in range(len(grouped_buyers)): ## NOTE: index after sorting!!!!

        buyer_og_ids_this_group = np.atleast_1d(grouped_buyers[buyer_grouped_ind, 0]).astype(int)
        
        # Creating a temporary mask for JUST these buyers
        temp_buyer_mask = np.zeros(num_prosumers, dtype=int)
        temp_buyer_mask[buyer_og_ids_this_group] = 1
        subgrouped_buyers = group_and_sort_vectors(BP, ascending=True, boolean_mask=temp_buyer_mask)

        for subgroup_ind in range(len(subgrouped_buyers)):
            subgroup_buyer_ids = np.atleast_1d(subgrouped_buyers[subgroup_ind, 0]).astype(int)
            buyer_price = subgrouped_buyers[subgroup_ind, 1]
        
            for seller_grouped_ind in range(len(grouped_PS_batt)): ## NOTE: index after sorting!!!!
                
                ### Preparing the needed variables:
                seller_og_ids_this_group = grouped_PS_batt[seller_grouped_ind, 0]
                selling_price = grouped_PS_batt[seller_grouped_ind, 1]
                
                #Needed load and avalable load for the whole group
                grouped_E_batt = np.sum(E_batt_list[seller_og_ids_this_group])
                grouped_load = np.sum(load_list[subgroup_buyer_ids])
                
                ### Comparing the buying price to the grid 
                if (grouped_E_batt > 0) & (grouped_load > 0):
                        if buyer_price >= selling_price:
                            f_P2P_batt, E_batt_list, load_list = group_to_group_asigning_P2P(f_P2P_batt, grouped_load, grouped_E_batt, seller_og_ids_this_group, subgroup_buyer_ids, E_batt_list, load_list)
                            
    E_batt_list_end = E_batt_list.copy()      
    
    ### Saving values
    flow_P2P[:, (10+num_prosumers):(10+(2*num_prosumers)) , time_period] = f_P2P_batt.copy()
    flow_P2P[:, (10+2*(num_prosumers)) , time_period] = E_batt_list_end.copy()
    flow_P2P[:, (11+2*(num_prosumers)) , time_period] = load_list.copy()

    ### After looping through all sellers, any remaining load is bought from the grid
    f_G2P = load_list.copy() # Capture the remaining values
    load_list.fill(0)

    f_P2P = f_P2P + f_P2P_batt
    
    ### Will sell to grid
    f_P2G = f_P2G + E_extra_list.copy()
    E_extra_list.fill(0)
    batt_discharge = original_E_batt - E_batt_list_end

    ### Saving values
    flow_P2P[:, (12+2*(num_prosumers)) , time_period] = f_P2G.copy()
    flow_P2P[:, (14+2*(num_prosumers)) , time_period] = f_G2P.copy()
    flow_P2P[:, (15+2*(num_prosumers)) , time_period] = load_list.copy()
    flow_P2P[:, (16+2*(num_prosumers)) , time_period] = E_extra_list.copy()
    
    return f_P2G, f_G2P, f_P2P, PS, flow_P2P, batt_discharge



#P2P function for enviromental P2P allocation method
def P2P_enviromental(time_period, load_list, E_extra_list, E_batt_list, bl_list, time_based, flow_P2P, num_prosumers):

    ### Saving values
    flow_P2P[:, 0, time_period] = E_extra_list.copy()
    flow_P2P[:, 1, time_period] = E_batt_list.copy()
    flow_P2P[:, 2, time_period] = load_list.copy()

    ### Setting the needed arrays:
    OG_index = np.arange(num_prosumers)
    SP = time_based[:, 1, time_period]
    PS = time_based[:, 3, time_period]
    BP = time_based[:, 2, time_period]
    flow_P2P[:, 3, time_period] = SP.copy()
    flow_P2P[:, 4, time_period] = BP.copy()
    flow_P2P[:, 5, time_period] = PS.copy()
    
    f_P2G = np.zeros([num_prosumers])
    f_G2P = np.zeros([num_prosumers])
    f_P2P = np.zeros((num_prosumers, num_prosumers)) ### Row: seller Column: buyer
    f_P2P_batt = np.zeros((num_prosumers, num_prosumers))
    
    ### Ckecking if prosumer will sell to the Energy Community
    seller_list = bl_list.copy()
    seller_list_batt = np.zeros([num_prosumers])
    for seller_id in range(0, num_prosumers):
        if (bl_list[seller_id] == 0) & (E_batt_list[seller_id]>0):
            seller_list_batt[seller_id] = 1

    ### We create sorted arrays but with grouped number of sellers/buyers if they have the same price
    be_list = 1-bl_list
    grouped_PS = group_and_sort_vectors(PS, ascending=True, boolean_mask=seller_list)
    grouped_BP = group_and_sort_vectors(BP, ascending=False, boolean_mask=be_list)
    grouped_PS_batt = group_and_sort_vectors(PS, ascending=True, boolean_mask=seller_list_batt)    

    ### For each buyer we check if it's better to buy to grid or to other prosumers
    for buyer_grouped_ind in range(len(grouped_BP)): ## NOTE: index after sorting!!!!
        for seller_grouped_ind in range(len(grouped_PS)): ## NOTE: index after sorting!!!!
            
            ### Preparing the needed variables:
            seller_og_ids_this_group = grouped_PS[seller_grouped_ind, 0]
            selling_price = grouped_PS[seller_grouped_ind, 1]
            buyer_og_ids_this_group = grouped_BP[buyer_grouped_ind, 0]
            buyer_price = grouped_BP[buyer_grouped_ind, 1]
            
            #Needed load and avalable load for the whole group
            grouped_E_extra = np.sum(E_extra_list[seller_og_ids_this_group])
            grouped_load = np.sum(load_list[buyer_og_ids_this_group])
            
            ### Comparing the buying price to the grid 
            if (grouped_E_extra > 0) & (grouped_load > 0):
                    if buyer_price >= selling_price:
                        f_P2P, E_extra_list, load_list = group_to_group_asigning_P2P(f_P2P, grouped_load, grouped_E_extra, seller_og_ids_this_group, buyer_og_ids_this_group, E_extra_list, load_list)
                    
    flow_P2P[:, 6, time_period] = f_P2G.copy()
    flow_P2P[:, 7:(7+num_prosumers), time_period] = f_P2P.copy()
    flow_P2P[:, 7+num_prosumers , time_period] = E_extra_list.copy()
    flow_P2P[:, 8+num_prosumers, time_period] = load_list.copy()
    flow_P2P[:, 9+num_prosumers, time_period] = E_batt_list.copy()

    original_E_batt = E_batt_list.copy()
    
    for buyer_grouped_ind in range(len(grouped_BP)): ## NOTE: index after sorting!!!!
        for seller_grouped_ind in range(len(grouped_PS_batt)): ## NOTE: index after sorting!!!!
            
            ### Preparing the needed variables:
            seller_og_ids_this_group = grouped_PS_batt[seller_grouped_ind, 0]
            selling_price = grouped_PS_batt[seller_grouped_ind, 1]
            buyer_og_ids_this_group = grouped_BP[buyer_grouped_ind, 0]
            buyer_price = grouped_BP[buyer_grouped_ind, 1]
            
            #Needed load and avalable load for the whole group
            grouped_E_batt = np.sum(E_batt_list[seller_og_ids_this_group])
            grouped_load = np.sum(load_list[buyer_og_ids_this_group])
            
            ### Comparing the buying price to the grid 
            if (grouped_E_batt > 0) & (grouped_load > 0):
                    if buyer_price >= selling_price:
                        f_P2P_batt, E_batt_list, load_list = group_to_group_asigning_P2P(f_P2P_batt, grouped_load, grouped_E_batt, seller_og_ids_this_group, buyer_og_ids_this_group, E_batt_list, load_list)
    
    E_batt_list_end = E_batt_list.copy()      
    
    ### Saving values
    flow_P2P[:, (10+num_prosumers):(10+(2*num_prosumers)) , time_period] = f_P2P_batt.copy()
    flow_P2P[:, (10+2*(num_prosumers)) , time_period] = E_batt_list_end.copy()
    flow_P2P[:, (11+2*(num_prosumers)) , time_period] = load_list.copy()

    ### After looping through all sellers, any remaining load is bought from the grid
    f_G2P = load_list.copy() # Capture the remaining values
    load_list.fill(0)

    f_P2P = f_P2P + f_P2P_batt
    
    ### Will sell to grid
    f_P2G = f_P2G + E_extra_list.copy()
    E_extra_list.fill(0)
    batt_discharge = original_E_batt - E_batt_list_end

    ### Saving values
    flow_P2P[:, (12+2*(num_prosumers)) , time_period] = f_P2G.copy()
    flow_P2P[:, (14+2*(num_prosumers)) , time_period] = f_G2P.copy()
    flow_P2P[:, (15+2*(num_prosumers)) , time_period] = load_list.copy()
    flow_P2P[:, (16+2*(num_prosumers)) , time_period] = E_extra_list.copy()
    
    return f_P2G, f_G2P, f_P2P, PS, flow_P2P, batt_discharge




#Runs the Digital Twin for one time period
def twin_time_instance(P2P_method, results_data, time_period, time_based_data, prosumer_based_data, flow_P2P, df_EC_parameters, E_pv_pr,  E_wt_pr, charging_batt_from_grid):
    P = prosumer_based_data.shape[1]
    
    for p_index in range(0, P):
        ic = prosumer_based_data[6, p_index]
        if time_period == 0:
            e_B = ic
        else:
            e_B = results_data[p_index, 16+P, time_period-1]
           
        C, E_total_PV, E_total_WT, bl, E_surplus_1, load_1 = checking_producer_or_consumer(p_index+1, time_period, time_based_data, prosumer_based_data, E_pv_pr,  E_wt_pr)
        E_surplus_2, e_B_next, grid2Batt, have_charged = charging_private_battery(p_index+1, time_period, time_based_data, prosumer_based_data, df_EC_parameters, E_surplus_1, e_B, load_1, charging_batt_from_grid)
        e_B_final, load_2, E_batt = discharging_private_battery(p_index, e_B_next, prosumer_based_data, df_EC_parameters, load_1, have_charged)

        results_data[p_index, 0, time_period] = C           #Load initial
        results_data[p_index, 1, time_period] = E_total_PV  #PV gen
        results_data[p_index, 2, time_period] = E_total_WT  #WT gen
        results_data[p_index, 3, time_period] = e_B         #Battery SOC
        results_data[p_index, 4, time_period] = bl          #Buyer or seller
        results_data[p_index, 5, time_period] = E_surplus_1 #Surplus after gen consumption
        results_data[p_index, 6, time_period] = load_1      #Load after gen consumption
        results_data[p_index, 7, time_period] = E_surplus_2 #Surplus after charge
        results_data[p_index, 8, time_period] = E_surplus_1 - E_surplus_2 #Amount charged
        results_data[p_index, 9, time_period] = load_2 #Load after discharge
        results_data[p_index, 10, time_period] = e_B_next - e_B_final #Discharged amount
        results_data[p_index, 11, time_period] = E_batt #Amount batt can share                  #
        results_data[p_index, 15+P, time_period] = grid2Batt ## Charged from grid
        
    ### Data one time period and all prosumers
    load_list = results_data[:, 9, time_period].copy()
    E_surplus_list = results_data[:, 7, time_period].copy()
    E_batt_list = results_data[:, 11, time_period].copy()
    bl_list = results_data[:, 4, time_period].copy()    
    G2Batt = results_data[:, 15+P, time_period].copy()
    flow_P2P[:,13+2*P,time_period] = G2Batt.copy()
    
    ### Peer to peer
    if P2P_method == 'P2P_market':
        f_P2G, f_G2P, f_P2P, price_sold, flow_P2P, batt_discharge = P2P(time_period, load_list, E_surplus_list, E_batt_list, bl_list, time_based_data, flow_P2P, P)
    elif P2P_method == 'P2P_one_price':
        f_P2G, f_G2P, f_P2P, price_sold, flow_P2P, batt_discharge = P2P_one_price(time_period, load_list, E_surplus_list, E_batt_list, bl_list, time_based_data, flow_P2P, P)
    elif P2P_method == 'P2P_social':
        f_P2G, f_G2P, f_P2P, price_sold, flow_P2P, batt_discharge = P2P_social(time_period, load_list, E_surplus_list, E_batt_list, bl_list, time_based_data, flow_P2P, P, prosumer_based_data, results_data, df_EC_parameters)
    elif P2P_method == 'P2P_enviromental':
        f_P2G, f_G2P, f_P2P, price_sold, flow_P2P, batt_discharge = P2P_enviromental(time_period, load_list, E_surplus_list, E_batt_list, bl_list, time_based_data, flow_P2P, P)

    for p_index in range(0, P): ## seller / row
        for buyer in range(0, P): 
            results_data[p_index, 12+buyer, time_period] = f_P2P[p_index, buyer] #P2P flows
                
    results_data[:, 12+P, time_period] = batt_discharge #Total battery shared
    results_data[:, 13+P, time_period] = f_P2G.copy()  #P2G
    results_data[:, 14+P, time_period] = f_G2P.copy()
    results_data[:, 16+P, time_period] = (results_data[:, 3, time_period] 
                                          + results_data[:, 8, time_period] 
                                          - results_data[:, 10, time_period] 
                                          - batt_discharge 
                                          + results_data[:, 15+P, time_period]) #e_B_final
    results_data[:, 17+P, time_period] = flow_P2P[:, 15+(2*P), time_period]  #Load final
    results_data[:, 18+P, time_period] = flow_P2P[:, 16+(2*P), time_period]  #E_surplus final
    
    return results_data, time_based_data, flow_P2P




#Runs the digital twin for T time periods
def twin(time_based_data, prosumer_based_data, df_EC_parameters, E_pv_pr,  E_wt_pr, P2P_method = 'P2P_market', charging_batt_from_grid=True):
    T = time_based_data.shape[2]
    P =  prosumer_based_data.shape[1]
    results_data = np.zeros((P, 19 + P , T))
    flow_P2P = np.zeros((P,(17+(2*P)),T))
    
    # 1. Generate results_names ONCE (2D Matrix: P rows x Columns)
    results_names = np.empty((19 + P ), dtype=object)
    flow_P2P_names = np.empty((17 + (2*P)), dtype=object)
    
    base_labels = [
        'Inicial Load',                                         # Index 0
        'Generation PV in KWh',                                 # Index 1
        'Generation WT in KWh',                                 # Index 2
        'Stored energy in battery inicial (e_B_inicial)',       # Index 3
        'Binary value, if sellers (bl)',                        # Index 4
        'Energy surplus after own consumption (E_surplus_1)',   # Index 5 
        'Load after own consumption (Load_1)',                  # Index 6
        'Energy surplus after charging (E_surplus_2)',          # Index 7
        'Charged amount in KWh',                                # Index 8
        'Load after battery discharge (Load_2)',                # Index 9                          
        'Discharged amount in KWh',                             # Index 10
        'Batt. energy allowed to be sold in P2P market(E_bat)', # Index 11
    ]
    
    base_labels_1 = [
        'Total_battery to P2P market (Total batt2P)',           # Index 12+P
        'Peer to Grid (f_P2G) in Kwh',                          # Index 13+P
        'Grid to Peer (f_G2P) in KWh',                          # Index 14+P
        'Grid to Batt (f_G2Batt) in KWh)',                      # Index 15+P
        'Battery capacity final (e_B_final)',                   # Index 16+P
        'Load final (load_final)',                              # Index 17+P
        'E_surplus_final (E_surplus_final)'                     # Index 18+P
    ]

    base_labels_P2P_0 = [
        'Energy surplus before P2P (E_surplus_2)',              # Index 0
        'Batt. energy allowed to be sold in P2P market(E_bat)', # Index 1
        'Load to be covered before P2P (load_2)',               # Index 2
        'Price selling to grid (SP)',                           # Index 3
        'Price buying from grid (BP)',                          # Index 4
        'Price in P2P market (price_P2P)',                      # Index 5
        'First asigned f_P2G because SP>price_P2P (f_P2G_0)'    # Index 6
    ]

    base_labels_P2P_1 = [
        'Generated surplus after P2P (E-surplus_3)',             # Index 7+P
        'Load after P2P (Load_3)',                               # Index 8+P
        'Batt. energy allowed to be sold in P2P market(E_bat)',  # Index 9+P
    ]
    
    base_labels_P2P_2 = [
        'Batt. available remaining (E_bat_2)',                   # Index 10+2P
        'Load after battery P2P (Load_4)',                        # Index 11+2P
        'Selling rest to the Grid (f_P2G_total)',                # Index 12+2P
        'Grid to Battery (f_G2Batt)',                            # Index 13+2P
        'Grid to Prosumer (f_G2P)',                              # Index 14+2P
        'Load after P2P (Load_5)',                               # Index 15+2P
        'Energy surplus after P2P (surplus_4)'                   # Index 16+2P
        
    ]
    
    results_names[0:12] = base_labels
    flow_P2P_names[0:7] = base_labels_P2P_0

    # Fill dynamic P2P names
    for p_idx in range(P):
        name = f"Flow to Prosumer {p_idx+1} (f_P2P)"
        results_names[12 + p_idx] = name
        flow_P2P_names[7 + p_idx] = name
    
    # Fill the tail labels for flow_P2P
    flow_P2P_names[7+P : 10+P] = base_labels_P2P_1
    results_names[12+P : 19+P] = base_labels_1
    
    # Fill dynamic P2P names, second round
    for p_idx in range(P):
        name = f"Battery flow to Prosumer {p_idx+1} (f_P2P_batt)"
        flow_P2P_names[10 + P + p_idx] = name

    flow_P2P_names[10+2*P : 17+2*P] = base_labels_P2P_2

    ### Time period loop
    for time_period in range(T):
        results_data, time_based_data, flow_P2P = twin_time_instance(P2P_method, results_data, time_period, time_based_data, prosumer_based_data, flow_P2P, df_EC_parameters, E_pv_pr,  E_wt_pr, charging_batt_from_grid)

    #print(results_data)
    return results_names, results_data, time_based_data, flow_P2P_names, flow_P2P



#######################################################################################
##3.KPI's
#######################################################################################



##Function to store the sum of all the Digital Twins variables for KPI analysis
def sum_analysis(prosumer_based_data, time_based_data, results_data, flow_P2P):
    P = prosumer_based_data.shape[1]
    sum_analysis_data = np.zeros((P,22))

    for i in range(P):

        #Totals by prosumer
        #From P2P market
        SP = flow_P2P[i, 3, :]
        BP = flow_P2P[i, 4, :]
        price_P2P = flow_P2P[i, 5, :]
        f_P2G = flow_P2P[i, 12+2*P, :]
        f_G2P = flow_P2P[i, 14+2*P, :]
        sold_total_P2P_by_i = np.sum( results_data[i , 12 : (12+P) , :], axis=0)  #Axis 0 because after slicing we have (f_P(seller)2Ps, hours). Result is sold per hour by prosumer i
        price_P2P_all_prosumers = flow_P2P[:,5,:]
        bought_P2P_by_i = results_data[:, 12+i, :]
        
        battery_charged_from_grid = results_data[i,15+P, :]
        revenue_selling_grid = SP * f_P2G
        cost_buying_grid = BP * (f_G2P + battery_charged_from_grid)
        revenue_selling_P2P = price_P2P * sold_total_P2P_by_i
        cost_buying_P2P = np.sum( ( price_P2P_all_prosumers * bought_P2P_by_i ) , axis=0) # Sum cost of all prosumers at all time periods
        net_revenue = revenue_selling_grid - cost_buying_grid + revenue_selling_P2P - cost_buying_P2P
        net_final_bill = - net_revenue
        
        #General market data
        total_consumption = results_data[i, 0, :]
        generation_PV = results_data[i,1,:]
        generation_WT = results_data[i,2,:]
        battery_charged_own_gen = results_data[i,8,:]
        battery_discharged_for_i = results_data[i,10,:]
        battery_discharge_for_P2P = results_data[i,12+P, :]
        battery_charged_from_grid = results_data[i,15+P, :]
        direct_self_consumption = total_consumption - results_data[i, 6, :]
        
        hypothetical_consumption_cost = total_consumption * BP #If prosumers didn't have any generation technology
        generation_total = generation_PV + generation_WT 

    
        proportion_PV = np.divide( generation_PV, generation_total,
                                  out=np.zeros_like(generation_total), 
                                  where=generation_total != 0)
        
        proportion_WT = np.divide( generation_WT, generation_total,
                                  out=np.zeros_like(generation_total), 
                                  where=generation_total != 0)

        #Profits energy generation technologies:
        profit_battery = (battery_discharged_for_i * BP) + (battery_discharge_for_P2P * price_P2P) - (battery_charged_own_gen * SP) - (battery_charged_from_grid * BP)
        direct_P2P_sales = sold_total_P2P_by_i - battery_discharge_for_P2P
        profit_PV = proportion_PV * (direct_self_consumption * BP + direct_P2P_sales * price_P2P + f_P2G * SP + battery_charged_own_gen * SP)
        profit_WT = proportion_WT * (direct_self_consumption * BP + direct_P2P_sales * price_P2P + f_P2G * SP + battery_charged_own_gen * SP)
        saved = hypothetical_consumption_cost - net_final_bill

        #Addition of values per month
        sum_analysis_data[i,0] = generation_total.sum() #sum E_total
        sum_analysis_data[i,1] = direct_self_consumption.sum() #sum own gen consumption
        sum_analysis_data[i,2] = np.sum(battery_discharged_for_i + battery_discharge_for_P2P) #sum of own battery consump
        sum_analysis_data[i,3] = np.sum(battery_charged_own_gen + battery_charged_from_grid) #sum of Own battery charge
        sum_analysis_data[i,4] = f_P2G.sum() #sum of P2G
        sum_analysis_data[i,5] = f_G2P.sum() #sum G2P
        sum_analysis_data[i,6] = bought_P2P_by_i.sum() #sum P2P received
        sum_analysis_data[i,7] = sold_total_P2P_by_i.sum() #summ of P2P given
        sum_analysis_data[i,8] = net_final_bill.sum() #Net final bill 
        sum_analysis_data[i,9] = np.sum( hypothetical_consumption_cost - net_final_bill ) #Saved per prosumer
        sum_analysis_data[i,10] = np.sum( sold_total_P2P_by_i * ( price_P2P - SP ) ) #Profit due to entering the P2P market
        sum_analysis_data[i,11] = profit_PV.sum() #Profit due to PV
        sum_analysis_data[i,12] = profit_WT.sum() #Profit due to WT
        sum_analysis_data[i,13] = profit_battery.sum() #Profit due to battery
        sum_analysis_data[i,14] = saved.sum() / generation_total.sum() if generation_total.sum() != 0 else 0  # x_m, which is the proportion of gain per prosumer to their generation. From Bara & Oprea (2023)
        sum_analysis_data[i,15] = np.sum(battery_discharged_for_i) #sum of own battery consump by i
        sum_analysis_data[i,16] = np.sum(battery_discharge_for_P2P) #sum of own battery shared to P2P
        sum_analysis_data[i,17] = np.sum(battery_charged_own_gen) #sum of Own battery charge by gen
        sum_analysis_data[i,18] = np.sum(battery_charged_from_grid) #sum of Own battery charge by grid
        sum_analysis_data[i,19] = np.sum(hypothetical_consumption_cost)
        sum_analysis_data[i,20] = np.sum(generation_PV)
        sum_analysis_data[i,21] = np.sum(generation_WT)
        
    return sum_analysis_data





##Function to store the sum of all the UPC variables for KPI analysis
def sum_analysis_UPC(UPC_results_data, prosumer_based_data, time_based_data):
    P = UPC_results_data.shape[0]
    sum_analysis_data = np.zeros((P,22))
    hours = UPC_results_data.shape[2]
    
    for i in range(P):

        #Totals by prosumer
        #From P2P market
        SP = time_based_data[i,1,:]
        BP = time_based_data[i,2,:]
        price_P2P = time_based_data[i,3,:]
        f_P2G = (-1)*(UPC_results_data[i,9+2*(P-2),:])
        f_G2P = UPC_results_data[i,2+P,:]
        sold_total_P2P_by_i = (-1)*(np.sum(UPC_results_data[i,(6+P):(9+2*(P-2)),:], axis=0))  #Axis 0 because after slicing we have (f_P2Ps, hours)
        peer_indices = [j for j in range(P) if j != i]
        price_P2P_all_prosumers = time_based_data[peer_indices, 3, :]
        bought_P2P_by_i = UPC_results_data[i,3:(2+P),:] #Bought by i to every other prosumer
        
        revenue_selling_grid =  SP * f_P2G
        cost_buying_grid = BP * f_G2P
        revenue_selling_P2P = price_P2P * sold_total_P2P_by_i
        cost_buying_P2P = np.sum( price_P2P_all_prosumers *  bought_P2P_by_i, axis=0) # Sum bought by prosumer i to all other prosumers by hour-
        net_revenue = revenue_selling_grid - cost_buying_grid + revenue_selling_P2P - cost_buying_P2P
        net_final_bill = - net_revenue

        #General market data
        total_consumption = time_based_data[i, 0, :]
        generation_PV = UPC_results_data[i,0,:] + UPC_results_data[i,3+P,:]*prosumer_based_data[0,i]
        generation_WT = UPC_results_data[i,1,:] + UPC_results_data[i,4+P,:]*prosumer_based_data[0,i]
        generation_total = generation_PV + generation_WT
        ec_t0 = UPC_results_data[i,2,:]
        ec_t1 = -UPC_results_data[i,10+2*(P-2),:]
        batt_discharge = np.maximum(ec_t0 - ec_t1, 0)
        batt_charge = np.maximum(ec_t1 - ec_t0, 0)

        battery_discharged_for_i = np.minimum(total_consumption, batt_discharge)
        battery_discharge_for_P2P = batt_discharge-battery_discharged_for_i
        surplus = np.maximum(0, generation_total-total_consumption)
        battery_charged_own_gen = np.minimum(surplus, batt_charge)
        battery_charged_from_grid = batt_charge-battery_charged_own_gen
        direct_self_consumption = np.minimum(generation_total, total_consumption)

        hypothetical_consumption_cost = total_consumption * BP #If prosumers didn't have any generation technology
        
        proportion_PV = np.divide( generation_PV, generation_total,
                                  out=np.zeros_like(generation_total), 
                                  where=generation_total != 0)
        proportion_WT = np.divide( generation_WT, generation_total,
                                  out=np.zeros_like(generation_total), 
                                  where=generation_total != 0)
        
        #Profits energy generation technologies:
        profit_battery = (battery_discharged_for_i * BP) + (battery_discharge_for_P2P * price_P2P) - (battery_charged_own_gen * SP) - (battery_charged_from_grid * BP)
        direct_P2P_sales = sold_total_P2P_by_i - battery_discharge_for_P2P
        profit_PV = proportion_PV * (direct_self_consumption * BP + direct_P2P_sales * price_P2P + f_P2G * SP + battery_charged_own_gen * SP)
        profit_WT = proportion_WT * (direct_self_consumption * BP + direct_P2P_sales * price_P2P + f_P2G * SP + battery_charged_own_gen * SP)
        saved = hypothetical_consumption_cost - net_final_bill

        #Addition of values per month 
        sum_analysis_data[i,0] = generation_total.sum() #sum E_total
        sum_analysis_data[i,1] = direct_self_consumption.sum() #sum own gen consumption
        sum_analysis_data[i,2] = np.sum(battery_discharged_for_i + battery_discharge_for_P2P) #sum of own battery consump
        sum_analysis_data[i,3] = np.sum(battery_charged_own_gen + battery_charged_from_grid) #sum of Own battery charge
        sum_analysis_data[i,4] = f_P2G.sum() #sum of P2G
        sum_analysis_data[i,5] = f_G2P.sum() #sum G2P
        sum_analysis_data[i,6] = bought_P2P_by_i.sum() #sum P2P received
        sum_analysis_data[i,7] = sold_total_P2P_by_i.sum() #summ of P2P given
        sum_analysis_data[i,8] = net_final_bill.sum() #Net final bill 
        sum_analysis_data[i,9] = np.sum( hypothetical_consumption_cost - net_final_bill ) #Saved per prosumer
        sum_analysis_data[i,10] = np.sum( sold_total_P2P_by_i * ( price_P2P - SP ) ) #Profit due to entering the P2P market
        sum_analysis_data[i,11] = profit_PV.sum() #Profit due to PV
        sum_analysis_data[i,12] = profit_WT.sum() #Profit due to WT
        sum_analysis_data[i,13] = profit_battery.sum() #Profit due to battery
        sum_analysis_data[i,14] = saved.sum() / generation_total.sum() if generation_total.sum() != 0 else 0  # x_m, which is the proportion of gain per prosumer to their generation. From Bara & Oprea (2023)
        sum_analysis_data[i,15] = np.sum(battery_discharged_for_i) #sum of own battery consump by i
        sum_analysis_data[i,16] = np.sum(battery_discharge_for_P2P) #sum of own battery shared to P2P
        sum_analysis_data[i,17] = np.sum(battery_charged_own_gen) #sum of Own battery charge by gen
        sum_analysis_data[i,18] = np.sum(battery_charged_from_grid) #sum of Own battery charge by grid
        sum_analysis_data[i,19] = np.sum(hypothetical_consumption_cost)
        sum_analysis_data[i,20] = np.sum(generation_PV)
        sum_analysis_data[i,21] = np.sum(generation_WT)
   
    return sum_analysis_data





#Computes KPI's
def compute_prosumer_kpis(prosumer_based_data, results_data, flow_P2P, time_based_data, df_EC_parameters, UPC_results_data=None):
    if UPC_results_data is not None:
        sum_analysis_data = sum_analysis_UPC(UPC_results_data, prosumer_based_data, time_based_data)
        H = UPC_results_data.shape[2]
    else:
        sum_analysis_data = sum_analysis(prosumer_based_data, time_based_data, results_data, flow_P2P)
        H = results_data.shape[2]
    
    num_prosumers = prosumer_based_data.shape[1]
    period_year_fraction = H / 8760

    E_total = sum_analysis_data[:,0] 
    own_consump = sum_analysis_data[:,1] 
    batt_discharge = sum_analysis_data[:,2] 
    batt_charge = sum_analysis_data[:,3] 
    P2G = sum_analysis_data[:,4] 
    G2P = sum_analysis_data[:,5] 
    P2P_received = sum_analysis_data[:,6] 
    P2P_given = sum_analysis_data[:,7]
    net_final_bill = sum_analysis_data[:,8]
    net_revenue = - net_final_bill
    saved_money = sum_analysis_data[:,9]
    profit_due_to_P2P = sum_analysis_data[:,10]
    PV_profit = sum_analysis_data[:,11]
    WT_profit = sum_analysis_data[:,12]
    bat_profit = sum_analysis_data[:,13]
    total_profit_investment = PV_profit + WT_profit + bat_profit
    x_m = sum_analysis_data[:,14] #From Bara & Oprea (2023)
    alpha = prosumer_based_data[0,:]
    battery_disch_own_consump = sum_analysis_data[:,15]
    battery_disch_P2P = sum_analysis_data[:,16]
    battery_charge_own_generation = sum_analysis_data[:,17]
    battery_charge_grid = sum_analysis_data[:,18]
    hypothetical_consumption_cost = sum_analysis_data[:,19] 
    generation_PV = sum_analysis_data[:,20] 
    generation_WT = sum_analysis_data[:,21] 
    total_load = own_consump + battery_disch_own_consump + P2P_received + G2P
    energy_surplus = P2G + P2P_given + battery_disch_P2P
    energy_deficit = G2P + battery_charge_grid + P2P_received

    #Installed values
    pw_pv_pr = df_EC_parameters.loc['pw_pv_pr', 'Value']
    pw_wt_pr = df_EC_parameters.loc['pw_wt_pr', 'Value']
    ic_pr = df_EC_parameters.loc['ic_pr', 'Value']
    UIC_PV = df_EC_parameters.loc['UIC_PV', 'Value']
    UIC_WT = df_EC_parameters.loc['UIC_WT', 'Value']
    UIC_B = df_EC_parameters.loc['UIC_B', 'Value']
    UL_PV = df_EC_parameters.loc['UL_PV', 'Value']
    UL_WT = df_EC_parameters.loc['UL_WT', 'Value']
    UL_B = df_EC_parameters.loc['UL_B', 'Value']
    CO2_eq_upfront_PV = df_EC_parameters.loc['CO2_eq_upfront_PV', 'Value']
    CO2_eq_upfront_WT = df_EC_parameters.loc['CO2_eq_upfront_WT', 'Value']
    CO2_eq_upfront_batt = df_EC_parameters.loc['CO2_eq_upfront_batt', 'Value']
    CO2_eq_emission_grid = df_EC_parameters.loc['CO2_eq_emission_grid', 'Value']
    pw_pv = prosumer_based_data[4,:]
    pw_wt = prosumer_based_data[5,:]
    ic_B = prosumer_based_data[6,:]

    invested_pv = ((( alpha * pw_pv_pr ) + pw_pv ) * UIC_PV).round(4)
    invested_wt = ((( alpha * pw_wt_pr ) + pw_wt ) * UIC_WT).round(4)
    invested_bat = ((( alpha * ic_pr ) + ic_B ) * UIC_B).round(4)
    total_invested = invested_pv + invested_wt + invested_bat

    envi_upfront_PV =  ((( alpha * pw_pv_pr ) + pw_pv ) * CO2_eq_upfront_PV).round(4)
    envi_upfront_WT =  ((( alpha * pw_wt_pr ) + pw_wt ) * CO2_eq_upfront_WT).round(4)
    envi_upfront_BATT = ((( alpha * ic_pr ) + ic_B ) * CO2_eq_upfront_batt).round(4)
    total_upfront = envi_upfront_PV + envi_upfront_WT + envi_upfront_BATT
    period_hardware_emissions = (
        (envi_upfront_PV / UL_PV)
        + (envi_upfront_WT / UL_WT)
        + (envi_upfront_BATT / UL_B)
    ) * period_year_fraction

    period_previous_emissions = total_load * CO2_eq_emission_grid
    period_current_grid_emissions = (G2P + battery_charge_grid) * CO2_eq_emission_grid
    period_total_emissions = period_hardware_emissions + period_current_grid_emissions
    period_carbon_savings = (
        generation_PV + generation_WT + batt_discharge - battery_charge_grid
    ) * CO2_eq_emission_grid

    kpis = pd.DataFrame(index=[f"P{i+1}" for i in range(num_prosumers)])

    kpis["Self-Consumption Ratio"] = np.divide(own_consump, E_total, out=np.zeros_like(own_consump, dtype=float), where=(E_total != 0)).round(4)
    kpis["Self-Sufficiency Ratio"] =  np.divide((own_consump + battery_disch_own_consump), total_load, out=np.zeros_like(own_consump, dtype=float), where=(total_load != 0)).round(4)
    kpis["Grid Dependency"] = np.divide(G2P, total_load, out=np.zeros_like(G2P, dtype=float), where=(total_load != 0)).round(4)
    kpis["Net P2P Balance in KWh per simulated period"] = P2P_given - P2P_received 
    kpis["P2P Participation in KWh per simulated period"] = P2P_given + P2P_received
    kpis["Shared energy in KWH (G2P-P2G) per simulated period"] = G2P - P2G
    kpis["Total consumption in kWh"] = total_load
    kpis["Energy surplus in kWh"] = energy_surplus
    kpis["P2P trading index in deficit"] = np.divide(P2P_received, energy_deficit, out=np.zeros_like(P2P_received, dtype=float), where=(energy_deficit > 0)).round(4)
    kpis["P2P trading index in surplus"] = np.divide(P2P_given, energy_surplus, out=np.zeros_like(P2P_given, dtype=float), where=(energy_surplus > 0)).round(4)
    
    economic_kpis = pd.DataFrame(index=[f"P{i+1}" for i in range(num_prosumers)])

    economic_kpis['Total final bill in €']= net_final_bill
    economic_kpis['Saved by entering community €']= saved_money
    economic_kpis['Total invested in €'] = total_invested
    economic_kpis['Profit in %'] = np.divide((total_profit_investment), total_invested, out=np.zeros_like(total_invested, dtype=float), where=(total_invested != 0)).round(4)
    economic_kpis['Profit PV in %'] = np.divide(PV_profit, invested_pv, out=np.zeros_like(invested_pv, dtype=float), where=(invested_pv != 0)).round(4)
    economic_kpis['Profit WT in %'] = np.divide(WT_profit, invested_wt, out=np.zeros_like(invested_wt, dtype=float), where=(invested_wt != 0)).round(4)
    economic_kpis['Profit batteries in %'] = np.divide(bat_profit, invested_bat, out=np.zeros_like(invested_bat, dtype=float), where=(invested_bat != 0)).round(4)
    economic_kpis['Payback time'] = np.divide(
        total_invested,
        total_profit_investment,
        out=np.zeros_like(total_invested, dtype=float),
        where=((total_invested > 1) & (np.abs(total_profit_investment) > 1e-5))
    ).round(4)
    economic_kpis['Payback time PV'] = np.divide(invested_pv, PV_profit, out=np.zeros_like(invested_pv, dtype=float), where=((invested_pv > 1) & (np.abs(PV_profit) > 1e-5)))
    economic_kpis['Payback time WT'] = np.divide(invested_wt, WT_profit, out=np.zeros_like(invested_wt, dtype=float), where=((invested_wt > 1) & (np.abs(WT_profit) > 1e-5)))
    economic_kpis['Payback time BATT'] = np.divide(invested_bat, bat_profit, out=np.zeros_like(invested_bat, dtype=float), where=((invested_bat > 1) & (np.abs(bat_profit) > 1e-5)))

    social_kpis = pd.DataFrame(index=[f"P{i+1}" for i in range(num_prosumers)])

    social_kpis['Bill reduction in %'] = 100 - np.divide(net_final_bill*100, hypothetical_consumption_cost,  out=np.zeros_like(hypothetical_consumption_cost, dtype=float), where=(hypothetical_consumption_cost != 0)).round(4)
    social_kpis['EC gain appropiation'] =  np.divide(net_revenue, net_revenue.sum(),  out=np.zeros_like(net_revenue, dtype=float), where=(net_revenue.sum() != 0)).round(4)
    social_kpis['EC savings appropiation'] =  np.divide(saved_money, saved_money.sum(),  out=np.zeros_like(saved_money, dtype=float), where=(saved_money.sum() != 0)).round(4)
    social_kpis['Contribution into EC investment'] =  np.divide(total_invested, total_invested.sum(),  out=np.zeros_like(total_invested, dtype=float), where=(total_invested.sum() != 0)).round(4)

    enviromental_kpis = pd.DataFrame(index=[f"P{i+1}" for i in range(num_prosumers)])

    enviromental_kpis['Avoided emissions (Kg CO2 eq)'] = period_previous_emissions - period_hardware_emissions - period_current_grid_emissions
    enviromental_kpis['Enviromental impact'] = np.divide(period_total_emissions, period_previous_emissions, out=np.zeros_like(period_total_emissions, dtype=float), where=(period_previous_emissions != 0)).round(4)
    enviromental_kpis['Upfront carbon debt (Kg CO2 eq)']= total_upfront
    enviromental_kpis['TOTAL carbon payback time'] = np.divide(total_upfront, period_carbon_savings, out=np.zeros_like(total_upfront, dtype=float), where=(period_carbon_savings != 0)).round(4)
    enviromental_kpis['PV carbon payback time'] = np.divide(envi_upfront_PV, (generation_PV * CO2_eq_emission_grid), out=np.zeros_like(envi_upfront_PV, dtype=float), where=((generation_PV * CO2_eq_emission_grid) != 0)).round(4)
    enviromental_kpis['WT carbon payback time'] = np.divide(envi_upfront_WT, (generation_WT * CO2_eq_emission_grid), out=np.zeros_like(envi_upfront_WT, dtype=float), where=((generation_WT * CO2_eq_emission_grid) != 0)).round(4)
    enviromental_kpis['BATT carbon payback time'] = np.divide(envi_upfront_BATT, ((batt_discharge - battery_charge_grid) * CO2_eq_emission_grid), out=np.zeros_like(envi_upfront_BATT, dtype=float), where=(((batt_discharge - battery_charge_grid) * CO2_eq_emission_grid) != 0)).round(4)
    
    community = {}

    community["Community Self-Sufficiency"] = round(((own_consump.sum()+battery_disch_own_consump.sum()) / total_load.sum()), 4) if total_load.sum() != 0 else 0
    community["Community total consumption in kWh"] = total_load.sum()
    community["Community total energy surplus in kWh"] = energy_surplus.sum()
    community["Community P2P trading index in surplus"] = (
        round(P2P_given.sum() / energy_surplus.sum(), 4)
        if energy_surplus.sum() > 0 else 0
    )
    community_profit = total_profit_investment.sum()
    community_investment = total_invested.sum()
    community["Community Profit in %"] = (
        round(community_profit / community_investment, 4)
        if community_investment != 0 else 0
    )
    community["Community Payback time"] = (
        round(community_investment / community_profit, 4)
        if community_investment > 1 and abs(community_profit) > 1e-5 else 0
    )
    community["Community total invested in €"] = community_investment
    community["Self-sufficiency difference between prosumers"] = kpis["Self-Sufficiency Ratio"].max() - kpis["Self-Sufficiency Ratio"].min()
    community["Community Grid Dependency"] = round(G2P.sum() / total_load.sum(), 4) if total_load.sum() != 0 else 0
    community["Community Self-Consumption"] = round((own_consump.sum()) / E_total.sum(), 4) if E_total.sum() != 0 else 0
    community["Community total final bill in €"] = net_final_bill.sum()
    community["Community total saved in €"] = saved_money.sum()
    community["Fairness index"] = (1 / num_prosumers) * (((x_m.sum())**2) / (x_m**2).sum()) if (x_m**2).sum() != 0 else 0 #From Bara & Oprea (2023)
    community['Baseline poverty help'] = saved_money.sum() / hypothetical_consumption_cost.mean() if hypothetical_consumption_cost.mean() != 0 else 0
    community['Avoided emissions (Kg CO2 eq)'] = period_previous_emissions.sum() - period_hardware_emissions.sum() - period_current_grid_emissions.sum()
    community['Enviromental impact'] = period_total_emissions.sum() / period_previous_emissions.sum() if period_previous_emissions.sum() != 0 else 0
    community['TOTAL carbon payback time'] = total_upfront.sum() / period_carbon_savings.sum() if period_carbon_savings.sum() != 0 else 0

    return kpis, community, economic_kpis, social_kpis, enviromental_kpis, sum_analysis_data






