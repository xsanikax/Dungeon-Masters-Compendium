import streamlit as st
import requests 
import json     
import re       
import os       

# --- Page Configuration ---
# This should be the very first Streamlit command in the script, after imports.
st.set_page_config(
    page_title="SRD Rulebook Search (API)",
    page_icon="S",  # Using a simple ASCII character "S" for Search
    layout="wide"
)

API_DOMAIN = "https://www.dnd5eapi.co" 
API_BASE_ENDPOINT = f"{API_DOMAIN}/api" 

CATEGORIES_TO_FETCH = {
    "Spells": "/spells",
    "Monsters": "/monsters",
    "Magic Items": "/magic-items",
    "Equipment": "/equipment",
    "Conditions": "/conditions"
}

# --- Helper function to fetch a list of items for a category ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def fetch_category_list(category_endpoint_suffix):
    """Fetches the list of all items in a category."""
    try:
        response = requests.get(f"{API_BASE_ENDPOINT}{category_endpoint_suffix}")
        response.raise_for_status()  
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        # This error will be displayed on the page if fetching a category list fails
        st.error(f"Error fetching category list for {category_endpoint_suffix}: {e}")
        return []

# --- Helper function to fetch details for a single item ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def fetch_item_details(item_url_suffix): 
    """Fetches the detailed data for a single item given its API URL suffix."""
    try:
        full_url = f"{API_DOMAIN}{item_url_suffix}" 
        response = requests.get(full_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for {full_url}: {e}") # Log to console for debugging
        return None

# --- Function to load, preprocess, and combine all SRD data from the API ---
@st.cache_data(ttl=3600) 
def load_and_combine_srd_data_from_api():
    all_srd_items = []
    
    has_st_progress = hasattr(st, 'progress')
    overall_progress_bar = None # Initialize to None
    if has_st_progress:
        overall_progress_bar = st.progress(0, text="Initializing data load...") 
    
    total_categories = len(CATEGORIES_TO_FETCH)
    
    for i, (category_name, category_endpoint_suffix) in enumerate(CATEGORIES_TO_FETCH.items()):
        current_progress_value = i / total_categories
        if has_st_progress and overall_progress_bar:
             overall_progress_bar.progress(current_progress_value, text=f"Fetching list: {category_name}...")
        
        item_list = fetch_category_list(category_endpoint_suffix) 
        
        if not item_list:
            # A warning for skipped categories will be shown on the page by fetch_category_list or here
            st.warning(f"Could not fetch or an error occurred for the list of {category_name}. Skipping that category.")
            if has_st_progress and overall_progress_bar: 
                overall_progress_bar.progress( (i + 1) / total_categories, text=f"Skipped {category_name}")
            continue

        if has_st_progress and overall_progress_bar:
            overall_progress_bar.progress(current_progress_value, text=f"Fetching details for {len(item_list)} {category_name.lower()}...")
        
        details_fetched_count = 0
        for j, item_summary in enumerate(item_list):
            item_detail = fetch_item_details(item_summary["url"]) 
            if item_detail:
                details_fetched_count +=1
                name = item_detail.get("name", "Unknown Name")
                search_text_parts = [name.lower()] 
                
                if category_name == "Spells":
                    desc_list = item_detail.get("desc", [])
                    search_text_parts.append(desc_list[0].lower() if isinstance(desc_list, list) and desc_list else str(item_detail.get("desc", "")).lower())
                    search_text_parts.append(item_detail.get("school", {}).get("name", "").lower())
                elif category_name == "Monsters":
                    search_text_parts.append(item_detail.get("type", "").lower())
                    search_text_parts.append(item_detail.get("size", "").lower())
                    search_text_parts.append(item_detail.get("alignment", "").lower()) # Added alignment
                    for key in ["special_abilities", "actions", "legendary_actions", "reactions"]:
                        abilities_list = item_detail.get(key, [])
                        if abilities_list is None: abilities_list = [] 
                        for ability in abilities_list: 
                            if isinstance(ability, dict): 
                                search_text_parts.append(ability.get("name", "").lower())
                                search_text_parts.append(ability.get("desc", "").lower())
                elif category_name == "Magic Items" or category_name == "Equipment":
                    desc_data = item_detail.get("desc", [])
                    desc_text = " ".join(desc_data) if isinstance(desc_data, list) else str(desc_data)
                    search_text_parts.append(desc_text.lower())
                    search_text_parts.append(item_detail.get("equipment_category", {}).get("name","").lower())
                elif category_name == "Conditions":
                    desc_data = item_detail.get("desc", [])
                    desc_text = " ".join(desc_data) if isinstance(desc_data, list) else str(desc_data)
                    search_text_parts.append(desc_text.lower())

                search_text = " ".join(filter(None, search_text_parts))
                search_text = re.sub(r'\s+', ' ', search_text).strip()

                all_srd_items.append({
                    "name": name, 
                    "category": category_name,
                    "search_text": search_text, 
                    "raw_data": item_detail 
                })
            
            # Update progress more granularly within detail fetching if desired
            if has_st_progress and overall_progress_bar and (j + 1) % 20 == 0: # Update every 20 items
                # Calculate progress within the current category more smoothly
                progress_within_category = (j + 1) / len(item_list)
                # Overall progress is how many full categories done, plus fraction of current one
                current_overall_progress = (i + progress_within_category) / total_categories
                overall_progress_bar.progress(min(current_overall_progress, 1.0), text=f"Fetching {category_name}: {j+1}/{len(item_list)}")

        if has_st_progress and overall_progress_bar: 
            overall_progress_bar.progress( (i + 1) / total_categories, text=f"Completed fetching {category_name} ({details_fetched_count} items)")
        
    if has_st_progress and overall_progress_bar: 
        overall_progress_bar.empty() 

    if not all_srd_items:
         # Errors from fetch_category_list will have already been displayed by st.error
         # This is a fallback if everything returned empty lists.
         st.error("Failed to load any SRD data from the API. Please ensure an internet connection.")
         return []
    return all_srd_items

# --- Main app UI ---
st.title("📚 Unified Rulebook Search (D&D 5e SRD via API)")
st.caption("Search across SRD Spells, Monsters, Magic Items, Equipment, and Conditions.")
st.markdown("Data is fetched from [dnd5eapi.co](https://www.dnd5eapi.co/) and cached. Initial load may take a minute or two.")

# The st.spinner will show while the load_and_combine_srd_data_from_api function executes for the first time
# or when the cache is invalid.
with st.spinner("Loading SRD data from API... This may take a moment on the very first run..."):
    srd_combined_data = load_and_combine_srd_data_from_api()

# After the spinner, srd_combined_data is available (or an empty list if loading failed)
if not srd_combined_data:
    st.error("SRD data could not be fully loaded. The search functionality will be unavailable. Check for specific errors during data fetching above (e.g., category list errors).")
else:
    st.success(f"SRD Data loaded! {len(srd_combined_data)} items available for search.")
    
    search_query = st.text_input("Search all SRD content:", placeholder="e.g., Fireball, Orc, Grapple, Longsword, Blinded")

    if search_query:
        results = []
        query = search_query.lower().strip()
        
        if query: 
            name_matches = []
            text_matches = []
            
            for item_wrapper in srd_combined_data: 
                item_name_lower = item_wrapper.get("name", "").lower()
                # Ensure item_search_text is a string before 'in' operator
                item_search_text = str(item_wrapper.get("search_text", "")) 

                is_name_match = query in item_name_lower
                
                if is_name_match:
                    name_matches.append(item_wrapper)
                elif query in item_search_text: 
                    text_matches.append(item_wrapper)
            
            final_results = []
            added_names_categories = set() 
            
            for item in name_matches:
                unique_key = (item.get("name"), item.get("category"))
                if unique_key not in added_names_categories:
                    final_results.append(item)
                    added_names_categories.add(unique_key)
            
            for item in text_matches:
                unique_key = (item.get("name"), item.get("category"))
                if unique_key not in added_names_categories: 
                    final_results.append(item)
                    added_names_categories.add(unique_key)
            
            results = final_results

            if results:
                st.subheader(f"Found {len(results)} item(s) matching '{search_query}':")
                for item_wrapper in results: 
                    data = item_wrapper['raw_data'] 
                    category = item_wrapper['category']
                    name = item_wrapper.get('name', 'N/A')

                    with st.expander(f"{name} ({category})", expanded=False):
                        st.markdown(f"### {data.get('name', 'Unknown Entry')}")
                        st.markdown("---")

                        if category == "Spells":
                            level_text = str(data.get('level', 'N/A')) 
                            school_name = data.get('school', {}).get('name', 'N/A')
                            if level_text == "0":
                                st.markdown(f"*{school_name} Cantrip*")
                            else:
                                st.markdown(f"*Level {level_text} {school_name}*")
                            st.markdown(f"**Casting Time:** {data.get('casting_time', 'N/A')}")
                            st.markdown(f"**Range:** {data.get('range', 'N/A')}")
                            components = data.get('components', [])
                            material = data.get('material', '')
                            comp_str = ", ".join(components)
                            if "M" in components and material and material.strip() != ".": 
                                comp_str += f" ({material.strip('.')})" 
                            st.markdown(f"**Components:** {comp_str if comp_str else 'N/A'}")
                            st.markdown(f"**Duration:** {data.get('duration', 'N/A')}")
                            ritual_text = "Yes" if data.get('ritual') else "No"
                            concentration_text = "Yes" if data.get('concentration') else "No"
                            st.markdown(f"**Ritual:** {ritual_text} | **Concentration:** {concentration_text}")
                            st.markdown("---")
                            description = data.get('desc', [])
                            st.markdown("\n\n".join(description) if isinstance(description, list) else str(description))
                            higher_level = data.get('higher_level', [])
                            if higher_level:
                                st.markdown("---")
                                st.markdown("**At Higher Levels:**")
                                st.markdown("\n\n".join(higher_level) if isinstance(higher_level, list) else str(higher_level))
                            classes_list = data.get('classes', [])
                            if classes_list:
                                class_names = [c.get('name') for c in classes_list if isinstance(c, dict) and c.get('name')]
                                if class_names: # Ensure list is not empty before joining
                                    st.markdown("---")
                                    st.markdown(f"**Classes:** {', '.join(class_names)}")
                            if data.get('damage') and isinstance(data.get('damage'), dict):
                                damage_info = data['damage']
                                damage_type_info = damage_info.get('damage_type', {}) 
                                damage_type = damage_type_info.get('name', 'N/A') if isinstance(damage_type_info, dict) else 'N/A'
                                st.markdown("---")
                                st.markdown(f"**Damage Type:** {damage_type}")
                                if damage_info.get('damage_at_slot_level'):
                                    st.markdown("**Damage At Slot Level:**")
                                    for lvl, dmg_dice in damage_info['damage_at_slot_level'].items():
                                        st.markdown(f"  - Level {lvl}: {dmg_dice}")
                        
                        elif category == "Monsters":
                            st.markdown(f"**Size:** {data.get('size', 'N/A')} | **Type:** {data.get('type', 'N/A')} | **Alignment:** {data.get('alignment', 'N/A')}")
                            ac_value = data.get('armor_class', []) # API returns list for AC for monsters
                            ac_display = "N/A"
                            if isinstance(ac_value, list) and ac_value: 
                                ac_display = f"{ac_value[0].get('value')} ({ac_value[0].get('type')})" if isinstance(ac_value[0], dict) else str(ac_value[0].get('value'))
                            elif isinstance(ac_value, (int,str)): # Fallback if it's a direct value (not typical for this API)
                                ac_display = str(ac_value)
                            st.markdown(f"**Armor Class:** {ac_display}")
                            st.markdown(f"**Hit Points:** {data.get('hit_points', 'N/A')} ({data.get('hit_dice', 'N/A')})")
                            speed_data = data.get('speed', {})
                            speed_str = ", ".join([f"{k.capitalize().replace('_', ' ')}: {v}" for k, v in speed_data.items() if v])
                            st.markdown(f"**Speed:** {speed_str if speed_str else 'N/A'}")
                            st.markdown(f"**STR:** {data.get('strength', 'N/A')} | **DEX:** {data.get('dexterity', 'N/A')} | **CON:** {data.get('constitution', 'N/A')} | **INT:** {data.get('intelligence', 'N/A')} | **WIS:** {data.get('wisdom', 'N/A')} | **CHA:** {data.get('charisma', 'N/A')}")
                            prof_list = [f"{p.get('proficiency', {}).get('name','').replace('Saving Throw: ', '').replace('Skill: ', '')} +{p.get('value','')}" for p in data.get('proficiencies', []) if p.get('proficiency')]
                            if prof_list: st.markdown(f"**Saving Throws & Skills Proficiencies:** {', '.join(prof_list)}")
                            if data.get('damage_vulnerabilities'): st.markdown(f"**Damage Vulnerabilities:** {', '.join(data.get('damage_vulnerabilities'))}")
                            if data.get('damage_resistances'): st.markdown(f"**Damage Resistances:** {', '.join(data.get('damage_resistances'))}")
                            if data.get('damage_immunities'): st.markdown(f"**Damage Immunities:** {', '.join(data.get('damage_immunities'))}")
                            condition_immunities_list = data.get('condition_immunities', [])
                            if condition_immunities_list: 
                                condition_immunities_str = ", ".join([ci.get('name', '') for ci in condition_immunities_list if isinstance(ci, dict) and ci.get('name')])
                                if condition_immunities_str: st.markdown(f"**Condition Immunities:** {condition_immunities_str}")
                            senses_data = data.get('senses', {})
                            senses_str = ", ".join([f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in senses_data.items() if v])
                            st.markdown(f"**Senses:** {senses_str if senses_str else 'N/A'}")
                            st.markdown(f"**Languages:** {data.get('languages', 'N/A')}")
                            st.markdown(f"**Challenge Rating:** {data.get('challenge_rating', 'N/A')} ({data.get('xp', 0)} XP)")
                            st.markdown("---")
                            for section_title, section_key in [("Special Abilities", "special_abilities"), ("Actions", "actions"), ("Reactions", "reactions"), ("Legendary Actions", "legendary_actions")]:
                                section_list = data.get(section_key, []) 
                                if section_list: 
                                    st.markdown(f"**{section_title}**")
                                    for ability in section_list:
                                        if isinstance(ability, dict):
                                            st.markdown(f"***{ability.get('name', 'Ability')}***: {ability.get('desc', '')}")
                                    st.markdown("---")
                        
                        elif category == "Magic Items":
                            st.markdown(f"**Category:** {data.get('equipment_category', {}).get('name', 'N/A')}")
                            rarity_data = data.get('rarity', {}) 
                            st.markdown(f"**Rarity:** {rarity_data.get('name', 'N/A') if isinstance(rarity_data, dict) else str(rarity_data)}")
                            st.markdown("---")
                            desc = data.get('desc', [])
                            st.markdown("\n\n".join(desc) if isinstance(desc, list) else str(desc))

                        elif category == "Equipment":
                            st.markdown(f"**Category:** {data.get('equipment_category', {}).get('name', 'N/A')}")
                            if data.get('gear_category', {}).get('name'): st.markdown(f"**Gear Category:** {data.get('gear_category',{}).get('name','N/A')}")
                            if data.get('armor_category'): st.markdown(f"**Armor Category:** {data.get('armor_category', 'N/A')}")
                            if data.get('weapon_category'): st.markdown(f"**Weapon Category:** {data.get('weapon_category', 'N/A')} ({data.get('weapon_range', 'N/A')})")
                            cost = data.get('cost', {})
                            st.markdown(f"**Cost:** {cost.get('quantity', 0)} {cost.get('unit', '')}")
                            if data.get('weight'): st.markdown(f"**Weight:** {data.get('weight')} lb.")
                            if data.get('damage') and isinstance(data.get('damage'), dict):
                                dmg = data['damage']
                                dmg_dice = dmg.get('damage_dice', 'N/A')
                                dmg_type_info = dmg.get('damage_type', {})
                                dmg_type = dmg_type_info.get('name', 'N/A') if isinstance(dmg_type_info, dict) else 'N/A'
                                st.markdown(f"**Damage:** {dmg_dice} {dmg_type}")
                            if data.get('armor_class') and isinstance(data.get('armor_class'), dict): # Armor AC is an object
                                ac = data['armor_class']
                                ac_str = f"{ac.get('base',0)}"
                                if ac.get('dex_bonus'): ac_str += " + Dex bonus"
                                if ac.get('max_bonus') is not None: ac_str += f" (max {ac.get('max_bonus')})" 
                                st.markdown(f"**Armor Class:** {ac_str}")
                            elif isinstance(data.get('armor_class'), (int, float)): # Other equipment might have simple AC
                                st.markdown(f"**Armor Class:** {data.get('armor_class')}")

                            if data.get('str_minimum', 0) > 0 : st.markdown(f"**Strength Minimum:** {data.get('str_minimum')}")
                            if data.get('stealth_disadvantage'): st.markdown(f"**Stealth:** Disadvantage")
                            properties_list = data.get('properties')
                            if properties_list and isinstance(properties_list, list): 
                                prop_names = [p.get('name') for p in properties_list if isinstance(p, dict) and p.get('name')]
                                if prop_names: st.markdown(f"**Properties:** {', '.join(prop_names)}")
                            st.markdown("---")
                            desc = data.get('desc', []) 
                            if desc: # Equipment can also have a top-level desc
                                st.markdown("\n\n".join(desc) if isinstance(desc, list) else str(desc))
                        
                        elif category == "Conditions":
                            desc = data.get('desc', [])
                            st.markdown("\n\n".join(desc) if isinstance(desc, list) else str(desc))
                        
                        else: 
                            st.json(data) 
            elif search_query: 
                st.info(f"No items found in the SRD matching '{search_query}'.")
        else:
            st.info("Please enter a search term.")

st.sidebar.markdown("---")
st.sidebar.info("This page fetches data from a public D&D 5e SRD API and caches it for faster subsequent loads.")