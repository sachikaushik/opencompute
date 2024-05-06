import streamlit as st

# Configure the page to use wide layout
st.set_page_config(page_title="Opencompute", layout="wide", page_icon ="icon.ico")

import wandb
import os
from dotenv import load_dotenv
import pandas as pd 
import bittensor as bt

# Load the API key from environment variable
load_dotenv()
api_key = os.getenv("WANDB_API_KEY")

# Constants for W&B
PUBLIC_WANDB_NAME = "opencompute"
PUBLIC_WANDB_ENTITY = "neuralinternet"

# Function to log in to wandb
def wandb_login(api_key):
    wandb.login(key=api_key)

# Function to fetch hardware specs from wandb
def fetch_hardware_specs(api, hotkeys):
    db_specs_dict = {}
    project_path = f"{PUBLIC_WANDB_ENTITY}/{PUBLIC_WANDB_NAME}"
    runs = api.runs(project_path)
    try:
        for run in runs:
            run_config = run.config
            hotkey = run_config.get('hotkey')
            details = run_config.get('specs')
            role = run_config.get('role')
            if hotkey in hotkeys and details and role == 'miner':
                index = hotkeys.index(hotkey)
                db_specs_dict[index] = (hotkey, details)
    except Exception as e:
        print(f"An error occurred while getting specs from wandb: {e}")
    return db_specs_dict

def get_allocated_hotkeys(api):
        """
        This function gets all allocated hotkeys from all validators.
        Only relevant for validators.
        """
        # Query all runs in the project
        api.flush()
        runs = api.runs(f"{PUBLIC_WANDB_ENTITY}/{PUBLIC_WANDB_NAME}")

         # Check if the runs list is empty
        if not runs:
            print("No validator info found in the project opencompute.")
            return []

        # Filter runs where the role is 'validator'
        validator_runs = [run for run in runs if run.config.get('role') == 'validator']

        # Initialize an empty list to store allocated keys from runs with a valid signature
        allocated_keys_list = []

        # Verify the signature for each validator run
        for run in validator_runs:
            try:
                # Access the run's configuration
                run_config = run.config
                hotkey = run_config.get('hotkey')
                allocated_keys = run_config.get('allocated_hotkeys')

                if allocated_keys:
                        allocated_keys_list.extend(allocated_keys)  # Add the keys to the list

            except Exception as e:
                print(f"Run ID: {run.id}, Name: {run.name}, Error: {e}")

        return allocated_keys_list

def display_hardware_specs(specs_details, allocated_keys):
    # Compute all necessary data before setting up the tabs
    column_headers = ["UID", "Hotkey", "GPU Name", "GPU Capacity (GiB)", "GPU Count", "CPU Count", "RAM (GiB)", "Disk Space (GiB)", "Status"]
    table_data = []

    gpu_instances = {}
    total_gpu_counts = {}

    for index in sorted(specs_details.keys()):
        hotkey, details = specs_details[index]
        if details:
            try:
                gpu_miner = details['gpu']
                gpu_capacity = "{:.2f}".format(gpu_miner['capacity'] / 1024)  # Capacity is in MiB
                gpu_name = str(gpu_miner['details'][0]['name']).lower()
                gpu_count = gpu_miner['count']

                cpu_miner = details['cpu']
                cpu_count = cpu_miner['count']

                ram_miner = details['ram']
                ram = "{:.2f}".format(ram_miner['available'] / 1024.0 ** 3)  # Convert bytes to GiB

                hard_disk_miner = details['hard_disk']
                hard_disk = "{:.2f}".format(hard_disk_miner['free'] / 1024.0 ** 3)  # Convert bytes to GiB

                row = [hotkey[:6] + ('...'), gpu_name, gpu_capacity, str(gpu_count), str(cpu_count), ram, hard_disk, "Pending"]
            except (KeyError, IndexError, TypeError):
                row = [str(index), hotkey[:6] + ('...'), "Invalid details"] + ["N/A"] * 6
        else:
            row = [str(index), hotkey[:6] + ('...')] + ["No details available"] + ["N/A"] * 6

        row[-1] = "Res." if hotkey in allocated_keys else "Avail."  # Allocation check
        table_data.append(row)

    # Display the tabs
    tab1, tab2, tab3 = st.tabs(["Hardware Overview", "Instances Summary", "Total GPU Counts"])

    with tab1:
        df = pd.DataFrame(table_data, columns=column_headers)
        st.table(df)

    with tab2:
        summary_data = [[gpu_name, str(gpu_count), str(instances)] for (gpu_name, gpu_count), instances in gpu_instances.items()]
        if summary_data:
            st.table(pd.DataFrame(summary_data, columns=["GPU Name", "GPU Count", "Instances Count"]))

    with tab3:
        summary_data = [[name, str(count)] for name, count in total_gpu_counts.items()]
        if summary_data:
            st.table(pd.DataFrame(summary_data, columns=["GPU Name", "Total GPU Count"]))


# Log in to wandb
wandb_login(api_key)

api = wandb.Api()

# Streamlit App Layout
st.title('Compute Subnet - Hardware Specifications')

# Fetching data with loading indicator
with st.spinner('Fetching metagraph data...'):
    metagraph = bt.metagraph(netuid=27)
    hotkeys = metagraph.hotkeys

# Fetch specs and display them
with st.spinner('Fetching hardware specifications...'):
    specs_details = fetch_hardware_specs(api, hotkeys)
    allocated_keys = get_allocated_hotkeys(api)

# Display fetched hardware specs
display_hardware_specs(specs_details, allocated_keys)
