import streamlit as st
import uuid # For generating unique character IDs
import copy # For deep copying character data
import re # For text manipulation if needed

# --- Page Configuration ---
st.set_page_config(
    page_title="Character Sheets",
    page_icon="🧑‍🎨", 
    layout="wide"
)

# --- Character Data Structure Template ---
def get_character_template():
    return {
        "doc_id": str(uuid.uuid4()), 
        "name": "New Character",
        "player_name": "",
        "race": "",
        "class_level": "", 
        "alignment": "",
        "background": "",
        "experience_points": 0,
        "image_url": "", # URL for character portrait

        "strength": 10, "dexterity": 10, "constitution": 10,
        "intelligence": 10, "wisdom": 10, "charisma": 10,

        "inspiration": False,
        "proficiency_bonus": 2,

        "saving_throws_proficiencies": [], # List of stat names e.g., ["strength", "dexterity"]
        "skills_proficiencies": [],       # List of skill names e.g., ["athletics", "stealth"]
        "skills_expertise": [],          # List of skill names for expertise

        "armor_class": 10,
        "initiative": 0, 
        "speed": "30 ft.",

        "max_hp": 10,
        "current_hp": 10,
        "temporary_hp": 0,
        "hit_dice_total": "1d8", 
        "hit_dice_current": "1d8",
        "death_saves_successes": 0,
        "death_saves_failures": 0,

        "personality_traits": "", 
        "ideals": "", 
        "bonds": "", 
        "flaws": "",

        "attacks_spellcasting_notes": "", # Text area for attacks, special actions
        "equipment_inventory_notes": "",  # Text area for general inventory
        "cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0,

        "features_traits_notes": "", # Text area for class features, racial traits etc.
        
        "spellcasting_ability": "None", # e.g., "Intelligence", "Wisdom", "Charisma"
        "spell_save_dc": 8,
        "spell_attack_bonus": 0,
        
        # Representing spell slots per level (1st to 9th)
        "spell_slots_level_1_total": 0, "spell_slots_level_1_used": 0,
        "spell_slots_level_2_total": 0, "spell_slots_level_2_used": 0,
        "spell_slots_level_3_total": 0, "spell_slots_level_3_used": 0,
        "spell_slots_level_4_total": 0, "spell_slots_level_4_used": 0,
        "spell_slots_level_5_total": 0, "spell_slots_level_5_used": 0,
        "spell_slots_level_6_total": 0, "spell_slots_level_6_used": 0,
        "spell_slots_level_7_total": 0, "spell_slots_level_7_used": 0,
        "spell_slots_level_8_total": 0, "spell_slots_level_8_used": 0,
        "spell_slots_level_9_total": 0, "spell_slots_level_9_used": 0,
        
        "prepared_spells_notes": "", # Text area for spells known/prepared list

        "notes": "", 
        "backstory": ""
    }

# --- Session State "Firestore Emulator" ---
def initialize_character_storage():
    if "characters_data" not in st.session_state:
        st.session_state.characters_data = {} # Stores all characters {doc_id: char_data}
    if "current_char_id" not in st.session_state:
        st.session_state.current_char_id = None
    if "editing_char" not in st.session_state: 
        st.session_state.editing_char = None

def save_character(character_data):
    if not character_data or "doc_id" not in character_data:
        st.error("Invalid character data. Cannot save.")
        return
    char_id = character_data["doc_id"]
    # Ensure all keys from template exist in character_data before saving
    # This helps if we add new fields to the template later.
    template_keys = get_character_template().keys()
    final_char_data = {key: character_data.get(key, get_character_template()[key]) for key in template_keys}
    final_char_data["doc_id"] = char_id # Preserve original ID

    st.session_state.characters_data[char_id] = copy.deepcopy(final_char_data) 
    st.toast(f"Character '{final_char_data['name']}' saved!", icon="✅")
    print(f"Saved character {char_id}: {final_char_data['name']}") # For local console
    # Force a reload of editing_char from the "saved" data
    st.session_state.editing_char = copy.deepcopy(final_char_data)


def load_characters():
    return list(st.session_state.characters_data.values())

def delete_character(char_id):
    if char_id in st.session_state.characters_data:
        deleted_char_name = st.session_state.characters_data[char_id].get("name", "Unknown")
        del st.session_state.characters_data[char_id]
        st.toast(f"Character '{deleted_char_name}' deleted.", icon="🗑️")
        if st.session_state.current_char_id == char_id:
            st.session_state.current_char_id = None
            st.session_state.editing_char = None
        return True
    return False

# --- Helper Functions for Character Sheet ---
def get_ability_modifier(score):
    return (score - 10) // 2

ABILITY_SCORES_FULL = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
SKILLS_DATA = {
    "Acrobatics": "dexterity", "Animal Handling": "wisdom", "Arcana": "intelligence",
    "Athletics": "strength", "Deception": "charisma", "History": "intelligence",
    "Insight": "wisdom", "Intimidation": "charisma", "Investigation": "intelligence",
    "Medicine": "wisdom", "Nature": "intelligence", "Perception": "wisdom",
    "Performance": "charisma", "Persuasion": "charisma", "Religion": "intelligence",
    "Sleight of Hand": "dexterity", "Stealth": "dexterity", "Survival": "wisdom"
}

def calculate_total_modifier(stat_name, char_data):
    base_mod = get_ability_modifier(char_data.get(stat_name, 10))
    is_proficient = stat_name in char_data.get("saving_throws_proficiencies", [])
    if is_proficient:
        return base_mod + char_data.get("proficiency_bonus", 0)
    return base_mod

def calculate_skill_total_modifier(skill_name, char_data):
    stat_for_skill = SKILLS_DATA.get(skill_name, "intelligence") # Default to INT if skill not found
    base_mod = get_ability_modifier(char_data.get(stat_for_skill, 10))
    is_proficient = skill_name in char_data.get("skills_proficiencies", [])
    is_expert = skill_name in char_data.get("skills_expertise", [])
    
    total_mod = base_mod
    if is_proficient:
        total_mod += char_data.get("proficiency_bonus", 0)
    if is_expert: # Expertise adds proficiency bonus again
        total_mod += char_data.get("proficiency_bonus", 0)
    return total_mod

# --- Main App UI ---
st.title("🧑‍🎨 Character Sheets")
st.caption("Manage your D&D 5e characters. (Data stored in this browser session only for this demo)")

initialize_character_storage()

# --- Character Selection and Management ---
characters_list = load_characters()
character_options = {char["doc_id"]: char["name"] for char in characters_list} # id:name mapping
character_names_in_order = [char["name"] for char in sorted(characters_list, key=lambda c: c.get("name", "").lower())]
sorted_char_ids = [char["doc_id"] for char in sorted(characters_list, key=lambda c: c.get("name", "").lower())]


# If editing_char exists, try to find its name in the current list for default index
current_selection_index = 0
if st.session_state.editing_char and st.session_state.editing_char.get("name") in character_names_in_order:
    current_selection_index = character_names_in_order.index(st.session_state.editing_char.get("name"))
elif character_names_in_order: # Default to first character if editing_char not found or is None
    current_selection_index = 0
else: # No characters
    current_selection_index = None


col_select, col_new, col_delete = st.columns([0.6, 0.2, 0.2])

with col_select:
    if character_names_in_order:
        selected_char_name_from_box = st.selectbox(
            "Select Character:",
            options=character_names_in_order,
            index=current_selection_index if current_selection_index is not None else 0, # Ensure index is valid
            key="character_select_dropdown"
        )
        # If selection changes, update editing_char
        if selected_char_name_from_box and (st.session_state.editing_char is None or st.session_state.editing_char.get("name") != selected_char_name_from_box):
            selected_doc_id = sorted_char_ids[character_names_in_order.index(selected_char_name_from_box)]
            st.session_state.current_char_id = selected_doc_id
            st.session_state.editing_char = copy.deepcopy(st.session_state.characters_data.get(selected_doc_id))
            st.rerun() # Rerun to load the selected character into the form
    else:
        st.info("No characters yet. Click '➕ New Character' to create one!")
        if st.session_state.editing_char is not None: # Clear editing char if no chars exist
            st.session_state.editing_char = None
            st.session_state.current_char_id = None


with col_new:
    if st.button("➕ New Character", use_container_width=True):
        new_char_template = get_character_template()
        # Ensure unique default name
        existing_names = {c.get("name", "").lower() for c in characters_list}
        default_name_base = "New Character"
        new_name_candidate = default_name_base
        count = 1
        while new_name_candidate.lower() in existing_names:
            new_name_candidate = f"{default_name_base} {count}"
            count += 1
        new_char_template["name"] = new_name_candidate
        
        save_character(new_char_template)
        st.session_state.current_char_id = new_char_template["doc_id"]
        st.session_state.editing_char = copy.deepcopy(new_char_template)
        st.rerun()

with col_delete:
    if st.session_state.editing_char:
        if st.button("🗑️ Delete Current", type="secondary", use_container_width=True, key="delete_char_button"):
            char_to_delete_id = st.session_state.editing_char.get("doc_id")
            if char_to_delete_id and delete_character(char_to_delete_id):
                # Deletion successful, select next character or clear form
                remaining_chars = load_characters()
                if remaining_chars:
                    new_selected_id = remaining_chars[0]["doc_id"]
                    st.session_state.current_char_id = new_selected_id
                    st.session_state.editing_char = copy.deepcopy(st.session_state.characters_data.get(new_selected_id))
                else: # No characters left
                    st.session_state.current_char_id = None
                    st.session_state.editing_char = None
                st.rerun()
    else:
        st.write("") # Placeholder

st.markdown("---")

# --- Character Sheet Display and Editing ---
if st.session_state.editing_char:
    char = st.session_state.editing_char 

    if st.button("💾 Save Character Changes", type="primary", key="save_top_button"):
        save_character(char)
        # No rerun needed here, save_character updates session_state.editing_char if successful

    tab_core, tab_combat, tab_skills_saves, tab_inventory, tab_spells, tab_features_notes_bg = st.tabs([
        "👤 Core & Abilities", "⚔️ Combat", "🎯 Skills & Saves", "🎒 Equipment", 
        "✨ Spells", "🌟 Features, Traits, Notes & Backstory"
    ])

    with tab_core:
        c1, c2, c3 = st.columns(3)
        with c1:
            char["name"] = st.text_input("Character Name", value=char.get("name", ""), key=f"name_{char['doc_id']}")
            char["player_name"] = st.text_input("Player Name", value=char.get("player_name", ""), key=f"player_name_{char['doc_id']}")
            char["image_url"] = st.text_input("Character Image URL", value=char.get("image_url", ""), placeholder="https://example.com/image.png", key=f"image_url_{char['doc_id']}")
            if char["image_url"]:
                st.image(char["image_url"], width=200, caption=char.get("name", "Portrait"))
        with c2:
            char["race"] = st.text_input("Race", value=char.get("race", ""), key=f"race_{char['doc_id']}")
            char["class_level"] = st.text_input("Class(es) & Level(s)", value=char.get("class_level", ""), placeholder="e.g., Fighter 5", key=f"class_level_{char['doc_id']}")
            char["background"] = st.text_input("Background", value=char.get("background", ""), key=f"background_{char['doc_id']}")
        with c3:
            char["alignment"] = st.text_input("Alignment", value=char.get("alignment", ""), key=f"alignment_{char['doc_id']}")
            char["experience_points"] = st.number_input("Experience Points", value=char.get("experience_points", 0), min_value=0, step=10, key=f"xp_{char['doc_id']}")
            char["inspiration"] = st.checkbox("Inspiration", value=char.get("inspiration", False), key=f"inspiration_{char['doc_id']}")
        
        st.subheader("Ability Scores")
        cols_stats = st.columns(6)
        for i, stat_full in enumerate(ABILITY_SCORES_FULL):
            with cols_stats[i]:
                char[stat_full] = st.number_input(
                    stat_full.capitalize(), 
                    value=char.get(stat_full, 10), 
                    min_value=1, max_value=30, step=1, key=f"stat_{stat_full}_{char['doc_id']}"
                )
                mod = get_ability_modifier(char[stat_full])
                st.metric(label=f"{stat_full.capitalize()[:3].upper()} Mod", value=f"{mod:+}")

    with tab_combat:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            char["armor_class"] = st.number_input("Armor Class (AC)", value=char.get("armor_class", 10), min_value=0, key=f"ac_{char['doc_id']}")
        with c2:
            dex_mod = get_ability_modifier(char.get("dexterity", 10))
            char["initiative"] = st.number_input("Initiative Bonus", value=char.get("initiative", dex_mod), help="Typically your Dexterity Modifier", key=f"initiative_{char['doc_id']}") 
        with c3:
            char["speed"] = st.text_input("Speed", value=char.get("speed", "30 ft."), key=f"speed_{char['doc_id']}")
        
        st.markdown("---")
        st.subheader("Hit Points")
        hp_c1, hp_c2, hp_c3 = st.columns(3)
        with hp_c1: char["max_hp"] = st.number_input("Maximum HP", value=char.get("max_hp", 10), min_value=1, key=f"max_hp_{char['doc_id']}")
        with hp_c2: char["current_hp"] = st.number_input("Current HP", value=char.get("current_hp", char.get("max_hp",10)), min_value=0, max_value=char["max_hp"], key=f"current_hp_{char['doc_id']}")
        with hp_c3: char["temporary_hp"] = st.number_input("Temporary HP", value=char.get("temporary_hp", 0), min_value=0, key=f"temp_hp_{char['doc_id']}")

        st.markdown("---")
        st.subheader("Hit Dice & Death Saves")
        hd_c1, hd_c2, ds_c1, ds_c2 = st.columns(4)
        with hd_c1: char["hit_dice_total"] = st.text_input("Total Hit Dice", value=char.get("hit_dice_total", "1d8"), placeholder="e.g., 5d10", key=f"hd_total_{char['doc_id']}")
        with hd_c2: char["hit_dice_current"] = st.text_input("Current Hit Dice", value=char.get("hit_dice_current", char.get("hit_dice_total","1d8")), key=f"hd_current_{char['doc_id']}")
        with ds_c1: char["death_saves_successes"] = st.number_input("Death Saves Successes", value=char.get("death_saves_successes", 0), min_value=0, max_value=3, key=f"ds_success_{char['doc_id']}")
        with ds_c2: char["death_saves_failures"] = st.number_input("Death Saves Failures", value=char.get("death_saves_failures", 0), min_value=0, max_value=3, key=f"ds_fail_{char['doc_id']}")
        
        st.markdown("---")
        st.subheader("Attacks & Actions")
        char["attacks_spellcasting_notes"] = st.text_area("List Attacks, Special Actions, Bonus Actions, Reactions", value=char.get("attacks_spellcasting_notes", ""), height=250, placeholder="Name | Atk Bonus | Damage/Type | Notes\nShortsword | +5 | 1d6+3 Piercing | Finesse\n...", key=f"attacks_{char['doc_id']}")

    with tab_skills_saves:
        char["proficiency_bonus"] = st.number_input("Proficiency Bonus", value=char.get("proficiency_bonus", 2), min_value=0, step=1, key=f"prof_bonus_{char['doc_id']}")
        
        st.subheader("Saving Throws")
        # Use a unique key for multiselect by appending doc_id
        char["saving_throws_proficiencies"] = st.multiselect(
            "Proficient Saving Throws:", options=ABILITY_SCORES_FULL,
            default=char.get("saving_throws_proficiencies", []), key=f"saving_throw_profs_{char['doc_id']}"
        )
        
        cols_saves_disp = st.columns(6)
        for i, stat_full in enumerate(ABILITY_SCORES_FULL):
            with cols_saves_disp[i]:
                save_mod = calculate_total_modifier(stat_full, char)
                st.metric(label=f"{stat_full.capitalize()[:3].upper()} Save", value=f"{save_mod:+}")

        st.subheader("Skills")
        char["skills_proficiencies"] = st.multiselect(
            "Proficient Skills:", options=list(SKILLS_DATA.keys()),
            default=char.get("skills_proficiencies", []), key=f"skill_profs_{char['doc_id']}"
        )
        char["skills_expertise"] = st.multiselect(
            "Expertise Skills (select from proficient skills):",
            options=[skill for skill in char["skills_proficiencies"]], # Only allow expertise in proficient skills
            default=[skill for skill in char.get("skills_expertise", []) if skill in char["skills_proficiencies"]],
            key=f"skill_expertise_{char['doc_id']}"
        )

        st.markdown("---")
        num_skill_cols = 3
        skill_cols = st.columns(num_skill_cols)
        sorted_skills = sorted(list(SKILLS_DATA.keys()))
        for idx, skill_name in enumerate(sorted_skills):
            with skill_cols[idx % num_skill_cols]:
                stat_for_skill = SKILLS_DATA[skill_name]
                skill_mod = calculate_skill_total_modifier(skill_name, char)
                is_prof = skill_name in char["skills_proficiencies"]
                is_exp = skill_name in char["skills_expertise"]
                label = f"**{skill_name}** ({stat_for_skill[:3].upper()}): `{skill_mod:+}`"
                if is_exp: label += " ⭐ (Expertise)"
                elif is_prof: label += " ✅ (Proficient)"
                st.markdown(label)
    
    with tab_inventory:
        st.subheader("Equipment & Inventory")
        char["equipment_inventory_notes"] = st.text_area("Equipment, Armor, Weapons, Tools, Magic Items, etc.", value=char.get("equipment_inventory_notes", ""), height=300, key=f"inventory_notes_{char['doc_id']}")
        st.subheader("Treasure (Coins)")
        coin_cols = st.columns(5)
        coin_types = ["cp", "sp", "ep", "gp", "pp"]
        for i, coin in enumerate(coin_types):
            with coin_cols[i]:
                char[coin] = st.number_input(coin.upper(), value=char.get(coin, 0), min_value=0, step=1, key=f"coin_{coin}_{char['doc_id']}")

    with tab_spells:
        st.subheader("Spellcasting Details")
        sc_cols = st.columns(3)
        with sc_cols[0]:
            spellcasting_ability_options = ["None"] + [s.capitalize() for s in ABILITY_SCORES_FULL]
            current_spell_ability = char.get("spellcasting_ability", "None")
            # Ensure current_spell_ability is in options, default to "None" if not
            if current_spell_ability not in spellcasting_ability_options:
                current_spell_ability = "None"

            char["spellcasting_ability"] = st.selectbox(
                "Spellcasting Ability", options=spellcasting_ability_options, 
                index=spellcasting_ability_options.index(current_spell_ability),
                key=f"spell_ability_{char['doc_id']}"
            )
        
        calculated_spell_save_dc = 8
        calculated_spell_attack_bonus = 0
        if char["spellcasting_ability"] != "None":
            spell_ability_score = char.get(char["spellcasting_ability"].lower(), 10)
            spell_ability_mod = get_ability_modifier(spell_ability_score)
            calculated_spell_save_dc = 8 + char["proficiency_bonus"] + spell_ability_mod
            calculated_spell_attack_bonus = char["proficiency_bonus"] + spell_ability_mod
        
        with sc_cols[1]:
            char["spell_save_dc"] = st.number_input("Spell Save DC", value=char.get("spell_save_dc", calculated_spell_save_dc), min_value=0, key=f"spell_dc_{char['doc_id']}", help=f"Auto-calc suggestion: {calculated_spell_save_dc}")
        with sc_cols[2]:
            char["spell_attack_bonus"] = st.number_input("Spell Attack Bonus", value=char.get("spell_attack_bonus", calculated_spell_attack_bonus), min_value=0, key=f"spell_atk_{char['doc_id']}", help=f"Auto-calc suggestion: {calculated_spell_attack_bonus}")

        st.markdown("---")
        st.subheader("Spell Slots per Level (Total / Used)")
        slot_cols = st.columns(3) # 3 levels per row
        for i in range(1, 10): # Spell levels 1-9
            with slot_cols[(i-1)%3]:
                char[f"spell_slots_level_{i}_total"] = st.number_input(f"Lvl {i} Total", value=char.get(f"spell_slots_level_{i}_total",0), min_value=0, key=f"slot_total_{i}_{char['doc_id']}")
                char[f"spell_slots_level_{i}_used"] = st.number_input(f"Lvl {i} Used", value=char.get(f"spell_slots_level_{i}_used",0), min_value=0, max_value=char.get(f"spell_slots_level_{i}_total",0), key=f"slot_used_{i}_{char['doc_id']}")
            if i % 3 == 0 and i < 9: # Create new row of columns
                slot_cols = st.columns(3)
        
        st.subheader("Spells Known / Prepared")
        char["prepared_spells_notes"] = st.text_area("List your spells here by level", value=char.get("prepared_spells_notes", ""), height=400, placeholder="Cantrips:\n- Spell Name\n\nLevel 1:\n- Spell Name (P)\n- Spell Name\n...", key=f"spells_known_{char['doc_id']}")

    with tab_features_notes_bg:
        st.subheader("Features & Traits")
        char["features_traits_notes"] = st.text_area("Class Features, Racial Traits, Feats, etc.", value=char.get("features_traits_notes", ""), height=300, key=f"features_{char['doc_id']}")
        
        st.markdown("---")
        st.subheader("Character Appearance & Personality")
        pers_c1, pers_c2 = st.columns(2)
        with pers_c1:
            char["personality_traits"] = st.text_area("Personality Traits", value=char.get("personality_traits", ""), height=100, key=f"pers_traits_{char['doc_id']}")
            char["ideals"] = st.text_area("Ideals", value=char.get("ideals", ""), height=100, key=f"ideals_{char['doc_id']}")
        with pers_c2:
            char["bonds"] = st.text_area("Bonds", value=char.get("bonds", ""), height=100, key=f"bonds_{char['doc_id']}")
            char["flaws"] = st.text_area("Flaws", value=char.get("flaws", ""), height=100, key=f"flaws_{char['doc_id']}")
        
        st.markdown("---")
        st.subheader("Backstory")
        char["backstory"] = st.text_area("Character Backstory", value=char.get("backstory", ""), height=250, key=f"backstory_{char['doc_id']}")
        
        st.markdown("---")
        st.subheader("Other Notes")
        char["notes"] = st.text_area("General Notes", value=char.get("notes", ""), height=150, key=f"gen_notes_{char['doc_id']}")
    
    st.markdown("---")
    if st.button("💾 Save All Changes to This Character", type="primary", key="save_bottom_button", use_container_width=True):
        save_character(char)
        # No rerun needed here, save_character updates session_state.editing_char if successful

elif len(characters_list) == 0 and st.session_state.editing_char is None : # Only show if no characters and nothing being edited
    st.markdown("### Welcome! Click '➕ New Character' to create your first character sheet.")


st.sidebar.markdown("---")
st.sidebar.info("Manage your D&D characters here. Data is stored in this browser session only for this demonstration.")