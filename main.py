import streamlit as st

# Configure the page to use wide layout
st.set_page_config(page_title="Opencompute", layout="wide", page_icon ="icon.ico")

import wandb
import os
from dotenv import load_dotenv
import pandas as pd 
import requests

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

                row = [str(index), hotkey[:6] + ('...'), gpu_name, gpu_capacity, str(gpu_count), str(cpu_count), ram, hard_disk, "Pending"]

                # Update summaries for GPU instances and total counts
                if isinstance(gpu_name, str) and isinstance(gpu_count, int):
                    row = [str(index), hotkey[:6] + ('...'), gpu_name, gpu_capacity, str(gpu_count), str(cpu_count), ram, hard_disk, "Pending"]
                    gpu_key = (gpu_name, gpu_count)
                    gpu_instances[gpu_key] = gpu_instances.get(gpu_key, 0) + 1
                    total_gpu_counts[gpu_name] = total_gpu_counts.get(gpu_name, 0) + gpu_count
                else:
                    row = [str(index), hotkey[:6] + ('...'), "No GPU data"] + ["N/A"] * 6

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

# Fetching data from external server
SERVER_IP = "94.101.98.126"  # Example IP, change to your server's IP
SERVER_PORT = "8000"          # Example port, change to your server's port
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}/keys"

def get_keys_from_server():
    response = requests.get(SERVER_URL)
    if response.status_code == 200:
        keys_json = response.json()
        keys = keys_json.get("keys", [])
        return keys
    else:
        return []

with st.spinner('Fetching metagraph data...'):
     hotkeys = get_keys_from_server()
     if not hotkeys:
        hotkeys = ['5CM7574h62PdUaFWEQTtMcGc5tazWj5LivCr3naBLA3Ebjj9', '5Hddm3iBFD2GLT5ik7LZnT3XJUnRnN8PoeCFgGQgawUVKNm8', '5CXRfP2ekFhe62r7q3vppRajJmGhTi7vwvb2yr79jveZ282w', '5HK5tp6t2S59DywmHRWPBVJeJ86T61KjurYqeooqj8sREpeN', '5H9UZf3EVctDLciBXbcQsBbqxA5tavg8g6VVzY5uwCwoBvCY', '5Gpdu3q1XT3i8qXL6wmZHTHYF9tgUnC7dYAi1m1Q23HGBw5R', '5FFKmnCSjLPE9vJFtvNKWEN9PXXy9uU1rtSAgUTkpqBKNe3h', '5CAhaWUabo5REh8Mkfhy1XosbN5MyyvoWDLASzWvXmgBTMxu', '5EREznCptbfNnazBbxi8jBfxKz1rEa4hkPykm1bVsqoJqwpX', '5Cw19YD6MwDoJFfnWiJsgWwBmnTqkHNuFwpTPY66aXn7VZ3W', '5C86mAxWzUodmRZMAw7QRMGnj4jxfioQJSCC9SSjKPCrFbkN', '5G4hfczhh1r5duR787BHGmMv7FDMboiGV5NnDos8NHTpbYst', '5FjvVHZXL2sNFVrB3eajTLHDGa7oTs2JtBw7nBLRJpyx9Q9J', '5EciBX61nybnXhQuHPRyFiv6puLBuTunQrXywktKTCHiDjQw', '5EUMoEsqrEjtUQGKFLf1BXLZGxJCt54vAnZMN3AHLYkHSUHz', '5C7crpGtZ9tPPxGJCWK4aUpLSBMJ7HMSNzDNNFryoWCZ1apa', '5DFTAeTg9iR9USDejXLjD2GJjT6Txu3aia5EwKDf1KYahtiX', '5G9w87gHpYXv3sxSpjm9HqFvYYjkcp742AGGjmra7ghYzpkT', '5CRsUFZceavvykbVTA9wABRyTx7KeGxDheUAVu19SJqnJwbB', '5FWbujfHUh1AiNpd4BsawZ2VrJ7yrjCmynDgfYxqBFJExEQj', '5Fy6mwMm5mprYjbULuEDDVUgzEmDwPcaujU2hWE4K2Nb7xUA', '5DvTpiniW9s3APmHRYn8FroUWyfnLtrsid5Mtn5EwMXHN2ed', '5Dt4GwdDZXRaW72u8tUrjRhFkzQMoJpQAM24PXSsMVHhfnUW', '5E4VdNQLC9Yv4tRUZhhpKTrCEFbw4vCgNis8zdfDpv66Xvhh', '5FmkEFgFhyqmoAVznayf5Zcfazvv7TAbXPXPE7fVEbabaBLw', '5Gebu6twT5pzrengLCdsPk2HLi8oZ7FetYRvPEPyjYnkAyyW', '5DhCrTJAboTanQLuhptPGRpFUqw1ATtWEDY1CVgSecVkdN9T', '5GR4BYzzxzhW7WezgPNzK89aXsbfJ389TWyYc6DiHScRmE7q', '5D8BcsgcW1dBmjC1mfufsBai6oDxvr5pZK9FNuk3ywLesPxj', '5Do4up9iq749bpopCDresEYMNxoxHWWqA7AVMY1V5nkZ2VxX', '5Dch8Pt3E9hFpDm6KqMbeZUfgS96uhH8HVe4uzRGkQnzRjYa', '5CHufrFZkDMkVA3zzRvkXWxkrCH8CyYrpb8kMUTduNuWbsE9', '5Fs7Wykc2rvNk84mdidpCwNVjJRoTwQ1NuqrpS4TXfwxSnUm', '5FsAyDQkWkPAi6QB4dFGhXjApXZC5YSU5pg38axYdUr16fkR', '5GNMrRTB2zHU1zNFJ2eQ7vMRALGKUid2Fo5ZCURkS78vLYg7', '5D2RLL2tBD5gm6U3EDJdATXSRXWhgJhfDoZBimZfEAR6UmB6', '5Evjd49nWR3DEbjEKdLCQh19o5D2DndkHZwKbMTpghnTHEYk', '5DvM3cqizsnkDwY3PkvzSPWLEmSAS4vLrnHu4JkkxCV6cHaW', '5GNhnrM4BRCVs59BnSDP3ZNNVyc7Fqe4FfAj3G5UffN7E4ic', '5CY8sdxqXpsqkVANBXkxmzNxzZ6iGNK2ceDKWbGeYrXofgag', '5G74kT4YrD9ecWFskg8AEXyrF9LDTBo8Ed2V45cP9rMf5KZe', '5DSNF32tNXfsirKVu8RQvHbQPtHA4aayRYi6tVDCk2yBdcrY', '5GsL9zNp1CdKmKSYBGjeF9kGReRpS8KdQv2yJ3mHVwKq2YCq', '5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v', '5DjjaRjRxafRmYpHMMaYjZq7p28Dx93m8gZqdEtDrLzLVc2H', '5FZ4QwE72w4HavWVkKw3DbvL5EBc9MCXak7X6E7oPXgppW4G', '5FWYGDvtpKBSvi6bzuWXtEyoS3nt82EjXZMFWwg5eWgSbYYY', '5HDg7ts5XNqxfe3Tt9R3AT1L5GmpeiXQFJL5PH2Ff3tfdF9i', '5GZRgzc6o4mKW9Utbt9hHNp1yuu6CsUoSzyT9XZzLK5BKVXt', '5GU4YWKzTwPe2qevSk4BVJMmQR923NXqpWZVyRuWdRerYjQV', '5GReLGXaHWTwef3WQY4PmeKRtQVmGHmh8TaRa4mYiw79yNki', '5GQq6hyCgCxUD8HaSniRufiMEAiS2WNnFhkDGPCKV6FomJWc', '5HbLYXUBy1snPR8nfioQ7GoA9x76EELzEq9j7F32vWUQHm1x', '5Gsoh3DcMBXvaAPNNWrbA6fFbyy4CKN4mP1vNq2WWJHH2RiL', '5GpNCUoAtusb1pEbfCTzDQhrSZs5vZY3tXyMTLRFojNN4vq5', '5FWed5DqP53jb534DZxNQ2YZhTycZNvxnCoMtKHLZw9eqmX6', '5GisYyddyMJ56BxAfR3rpcAuKSgcgvsHKJybehMwZ4TQ5ceq', '5DnXm2tBGAD57ySJv5SfpTfLcsQbSKKp6xZKFWABw3cYUgqg', '5FxegrWgAVuBsGLHyWoQisZwF4vnTUP3iZRdcz8FtYakorx6', '5Egs282yNwHCbKRmvfXeHp78GFZqw4LtZa6e6er6HBqwwJS6', '5F4Ft1qJmkTBJsUjRM9PUjqVzgkdRo2aTpPPQRT6dhfjQ4jw', '5HHJxNN1sUFuVdfEvpYHKet9w53ScfpAhHGnkn3uhDbwFyXX', '5F6eGbHXGtT7nC9aJPfyBJJYfwyJLgCnNQigahCndVSk5SDG', '5EqcT8DDNgat1WTXNtUmw756HDTMnWJParXenFVChNunj3EC', '5FKstHjZkh4v3qAMSBa1oJcHCLjxYZ8SNTSz1opTv4hR7gVB', '5G1NjW9YhXLadMWajvTkfcJy6up3yH2q1YzMXDTi6ijanChe', '5CafshVwrqFTVE4F69xp2fjv3f6FKJ6bewaijoRhBYR6aCp9', '5DLgAFCnipqnGhev1pT7gJdgM3s6Z6ZbMhmYKW5AXyZwUW2V', '5FWSuRMJkA5H4RBZuX2VE8jxht8vfcsFgZLDLJG7FEhV9vim', '5FmnjSxNqUsCm7n6BvuDHxZhe2VCEScKpeRx58THMetZpLZW', '5Gk6By42oGiAR7AjzdnU63fTgg8PhgbDauGyXDMGvPgZ88Bd', '5DLHtEk7MUpXxukXDp8MmJhQKb4iQjauAXfxrUbsQH7RjAVN', '5FmnNPNa6yMUD5d8f4Eu3L8HQX6wjZEARVzcUFBHwqe5Ya9w', '5CFCawAuMHysd5xQ83nzL83dGiMUMEj4ywiWxeM9Mctcx3zU', '5Gpxxb24veKGGKWn1y5MeG5hvkyVtV8uVgSAuuGHQvDTXZpZ', '5F7MbYYxLPMErVSttauz9xtvMyMbqPWqshdD4w4XfLT7mmPT', '5HHXBLZWTPrx5XfuukCf73u5kB7U6fRVvcT4a1nY79egbgGJ', '5HKkuGGp9VTngo157WFUzDpHuoQzoW9bJ97nrHzWeExVWQNQ', '5DAswwW3MGytovkeFQKsy6tNjnbt1G5PxYzcqfPikFhsY1RK', '5Hg1qdXiMsUxdtPq2NLkwYBzdembQkijmDfjNq6QzLoVDFpp', '5Ci5VDoPxuoy7esDoXMjxauyi6kB2AVXwHw1UrpeUABwaSpr', '5G15uRdifTwpwdWWydMFhp3doPKYqwAtdUPaz77N35sWJLPY', '5D7f2CcNY9ZfVpVMzvJFyd9rsU2LQrYcFqS2ogC2jreNgaR3', '5GR5iBgjtjzrX9QmoovfEGMBE83dWEHVUth4J8FqkVc48Jep', '5FmvrAKaB58i5ft2WmWe6aFLDK7A4fz6FkkhNFZVDcpZktZP', '5Gzr2tLxzf5Tn3d1XBcGmyvv1ADTPm58JL8ZRwrCP4hMWibq', '5HGz5cMHzVm3PaqmECVwVxersAxBQNPvjPoP2914dTVcHd1H', '5DLaGKLoHSxiNgVbuMko2PQAbraWyZuAR8hfMgTqFPWqYX4y', '5E55icNLS47k6YC3f9T2tujFnnSi2J2GHU8YfdiSsXJm4J7d', '5Chse1Yx9BY57B3JBURHfvFBqKZsd9rAdD7MnBPJDTWxaxFZ', '5EhvL1FVkQPpMjZX4MAADcW42i3xPSF1KiCpuaxTYVr28sux', '5HirCaemRt1L8PW7A8WYLhJTQw8bfWQUkek5YymTEvnbPVTA', '5HgeJotfkByVWEGMKUZ2V4MfGxEXiY23JU65LfEaSdWirU3R', '5Eh4RSE5KNVs8CBV9i7e2qsCvXJYyD9zfedrQcGMh3zWeQW2', '5GTRWr6vgqu8gt6UhBd2kEAQGhryzMYj4Vb4EWj4ryrS11Ye', '5ExxKFa7mKkzW2LEeR5GatypZ3T4UPKSb3oB92XWCi81zm6b', '5FjsVkS9EWXjT4pM7HQbE3czLPmex4uFPZr5je4BcbnT4Zj1', '5FeCzpaD7RDvZoKJZFAToDi5u95TTu8Z9HzidgV9uyQp5pzC', '5Funp2AxJ2NbML55j46KaC94eoA9UFP1kmUJ44qCh9TBaodq', '5HW3XnruebQjgpG43fVwwVgeXcBwGCjMuajtJck4hkVfuSaG', '5H6wdTtQzkuaCRaUev1GrpSQhJQ3xRrNYV52SYcXaPdS4nuH', '5EeHsNRVeuqGH68EvuX5Vxe7XCr3VWmU9PP1V2NXXJoKMzkD', '5GuNntFupTnDKfusZzkn13NckiseHergbR4fnM4aFabNFD4H', '5FukG4i4nxtpLXszYZGK98Kr55aVYiFv2LQ7LRiWGDYNpdLX', '5DCPJzYLpEh1fiVbFb5fPQbKv5JHe9HFhTG6TJ8uLp4eb6NJ', '5FPNi86CJRwGeSN6Mpvr7B631TnTMwq55wFwLktUFx3kQh9Z', '5C8CXKezJqu7tw6L1wGzx2C3UXEY5MT6xjeiS444A5mu3Ltz', '5HicHEnzKNrQKwwXcNRVSnkrZgePAPj9Q27jshRnLVtdzMYJ', '5GCLnVuT2V4Qd3xfBCfaKBJWT4dgrwjCxEgGB5SfWJWDtPhF', '5CXtEVD65VGgqWbUfbXabNsnxCPZmytkYBRdRJha9zjJYVnY', '5EvDk2e2B7kC6KHxcQ6hBeJcvcCvV1mxQNWNoDFPeoA5vCZa', '5FqT6BhnAXRur2dsNkNF6zWBGz8FjL7yY65AH26SEL1TDdZ5', '5FZtFZ2DXyrhDc8Ba95h9nUqtD78qEUhd4q4a2ecsGVNRJor', '5GmXYzMwucUit4mLQFY1w6DJZVxWpDMd3SBrCvSdiZQXDopL', '5GTTbepnx7v6rVBBPAogwY5N7fgrNzLrLvBASvSSzygW3R6p', '5FYkvfktkA7f7dhKWNpqhRjbRN5eLfqqC6AKfpbUYJKS4vAL', '5FsnPGg31y2MpXafyQJ5SKQjrDgqHj3nxiNcNKwUPH8p13KB', '5Dy9iBs5vQ14UHiWnHU6JmjrZQ3uCLSQB27Wit5yESqsABd3', '5GTsfmDRXHj5y2pByWpFSG1dGmyg6pX1vMNqHz9KE95jXeb7', '5FA3t3jjmtHy8zqnBwzJfesK75FP7sRtKivVPowhv9gV1Vvd', '5G4kBFz2DBC4EU1Nf2ia18xippAHkVHr3mQmJwisVFygyDxX', '5CJ8eV41sZz8N8qSiUYDnwVb2FJ8ZSfEdsZ8ZrQWRU6tGhPw', '5HTLUH97mUsMcHzhjHrb2SdZjsf5BTr7ajXi4Sct4V3AjmYH', '5Ca9TnvdvktoqXWZWZJyn2fDW1TTX6TC4qdBDiN97f4aSSsp', '5EpiktDUzTHWZ4V6SxnxXnKek5ZWgzcH1yQ8WSq1w76Hbsek', '5CY1HvBJCUSAeEDMryvYASTwsnCAVZf9m1YqHz8tBz8Yuy4M', '5Fn6okyjWg7sYZ1ueAKCy73AvPh9Afx1KRYkxYxNLvSfPxT4', '5GEJLNM3ZaQzJsYgKjUEiMMjZUNZXpnpyVn5dK3MDZu63udw', '5EkPHXpWWVfahfByK9DsqXSXnegunDxdt1YBBEu8K3zjyg9s', '5FhL1XnYrV2cJbHDRfskC21YrxwyZzjGKRhVWgrZpTLDE2Mu', '5GuNY5oZCRoMBd9EjGyAj5hVX4MqMkFsQLfGerGFEP11nCWJ', '5FUGBqcvkvzUxe1KGYiQ4s9tGzxJ1HMausXVxJoahfpNg3TY', '5CLV5cDWQK1bSCLTPzdrwGAqS49HdzZhu41DMPxjNFzZEPTq', '5DcGoDN398QaNPvWo3bQ2ZZqgzvhC9JEYafs4jPS92EnSFEH', '5DMCSkXqHx3avzzGhivvQLw4zZWYoVRgu51V1wviT6by7oD5', '5FNj91A6NshcCS6iBBtYzvuFyPReKiFT5j76wafp3VMBMpQE', '5FTswZLPTGLs4RYiaXantDk2w18m3NtQfiNLUymKQqcSUNx8', '5Gzr9s3J1mkFZSNUUhsQUaCpBDEiBTDXNH3158njA8dgun5P', '5E4Rz2HU4HXYwqz1nReyhjJVpCqcs7No45qyiWaPJBh8cL9u', '5C8dDUerfttWuLvrHjx2wk8whmdwbbmyHDaE3wLgBctCLiWA', '5E4HRBbYwRoEVYi2HKRpkMDVLJyaENaS7rRECcBfEsTRCkMh', '5FBj3oaXbNH5QQbLsSEwAwAUz5CUkSaZ7a9gT4Rr4tk8RUkk', '5FHoPCGnFtRoch3jruZnTLP9KuoCw2XChdDgimGa4RsBt1Tu', '5D7nk8EF9eQzPYuNRPLciubV8o2J7vgDfc9QxZox2LmVdMBx', '5HGqzw2TiBZscF7Xw27vVMPqsmpdHJt8trxwmpvhYX5idLEs', '5H4FwvJ5BnzZ1j7hLc7VqC2jhk7D9arSpHUiufJWECPubxxG', '5HEnRzcfRx8hjXsPgC4GA32i4KuKuKHw2QsbG84CfMoLy8xq', '5CaNj3BarTHotEK1n513aoTtFeXcjf6uvKzAyzNuv9cirUoW', '5EnoCibhwHdTGrNhFbv3EjJz77F89CHXnyhnKwFHJjrLLazR', '5GnTKgwNL7DjuFTqPMw3mtNd3RpSTjx16e86BdZGzBWbBafZ', '5FjSzmq1Tzmfj3TWchMju4p1mGvtkCwqRfkcmrV54sGtbXB3', '5CSRycLFCovzJQsuUCSTNz2c4bMWuknjGmXinPKNihPCaHV1', '5FbLN3RpPUn1iwGgN2iYvTYHKJTEe2w4QAQis3RLsBBesQjj', '5CfXNcKQdJqLSpkpXG6x5Mw1TQxcgnKdQNciTGuF5UHVnV73', '5CyhyjPh1vfaMq4ZgrsbBXb6tuAsJxxTBpwCQ2iwz7B1zXhQ', '5DJGHyqoAHwwXt3NC5JcqryPZL8WN1hG6ayrAukJzzY3Z6ky', '5FLDGJHiyyR2h9FWb8dig1xybz8wAoM4SEtNET7LVD18E1RH', '5CsvRJXuR955WojnGMdok1hbhffZyB4N5ocrv82f3p5A2zVp', '5HoxFLctJZTH2w5PqyMj7TKHPctz7NowFUNu9capxU28Nd99', '5FnSpKcKGMrYrPkcEVTFbbUscw2AY53jdwed5ZUeSFsDvn2K', '5HRStCcqTTcJSfoNApGPQsMVVnbuxJPaoRneq2HCHia88eKc', '5GUKo4yzJuN4bMDDcCmpLZwLQoV8zvsUPp6K6TtjL2HQVNE9', '5C5kUpLWkEN1WDzN9e2b3gdzSPeYbr1TbQSXV5Wxtx58eKqN', '5FTde2C54VfGfHeMmxNADysayHaJGF7KLWPpqdh87V4qj1tZ', '5ELkxEVAKPHnc9t7CzF6C3AqRCvniGTYgtdd8ce5yVmqUBX4', '5D2gLZsWcw5xXtUsRS5YLGQjeawwKQjNt7oFGFrNLmsmwpKh', '5Ek831En9kHUXqTPuEzNFTZjYmYYohGGU6GhgNVQ6kq8aqnP', '5GWRhP3d36rfBVV8EiBsTS7rGEC596ReAhLiMQnM2JY8U6vj', '5HYidb5mrP72xomTnjrhxJCLzoPKm8pKS1zWAEoHqs56Gens', '5H64CbH69nY9XYfadiqnMw2zKnwNmnV2LrZbmH1rnDfzqWV6', '5HokNPWea1ksbtbSLQ2K5gfzZ5NS1wZAVrzuYqr8JYg83fo2', '5Gzm6rWWVqj8XRy7kvyrdfStqn3yeF4j9XQCA7Tc8UGrcJ6o', '5E9yZkwwECVD6tqFopE9QGTsDpEq79qPHAVJFjtRxUECDs2N', '5H63R7K5q7A4KkQmRaEp2Q3ExgGAy1QNxAXFwh2Lx1TgkY28', '5ECKXd2jnjKQKsEybpsoXu3iihGebK6ZmVKrweuK5SpSdYrc', '5EFL3q2UEoxtFjUfk281XF994cJsduY4aJnNzv9F6ArHcRxC', '5He7wASWDT7hUd4kjteixB9iv11fFe3f5JD3QykJ5LdPADjN', '5FeZNe2C8vZFb2gtC5v6Kwr1sEv9dxxTR4Py9ZNyG7BdqrhH', '5ES3i7tWiuS7bLeersG2HWaZYRirWXcHB6vfBvdEyQA5TSmF', '5GVrBbHuPpAQwdTCbse2cF3jcgRhnzABh9EQo1eXnTQ7w3cr', '5DvxAh4JvsdePw3vmTE7DSWYmojbWNL3NuykLq51gEATmRGw', '5FqXKF2RR33ZHcv5VcKF3aSXFHHu9eThgdvyKiU6rig3RbvW', '5DP71LWHkLH9zjt9gToJjdK3x1gwjCuyGwydX72DTyJMpQSQ', '5DvJeSbgVqCXsNjuQj8rFJ55iZSqHsY772JnzPGkDrLVmqEv', '5Gp9WdezvYWEEQy4DHEwsTpdY6gytgai7CLDb3pk5ff6MtKF', '5GL9HGJjbWXn2YXEs9D7ap5KEQUUSJiUmm47BATSeLkhDnvY', '5FRhGN9BTwnYaEHnVmzCrwVbyJaFDF7pTwaT3eh1afkyrYMY', '5HWMshjPsSTYTZ5W8t71ikmDcXouekhxu1qiE2YMyqrGKVVu', '5HKNri36aysErfQd4qFKKraQPidCHbUDb98tEZZUT1tjrewt', '5Gju2quo8K2Py5fv495YmJXzwvRY5NbnZjobsyU7EYCbMJfx', '5GbpAb6NHXGJRCmxLy1QD3hJhnrJfqQo99Z9nywmfHCzZ65y', '5FsRLm4SJVzyAqHUntd2PCAP4ffTjWoZCZdYeMCCeRNCLb5A', '5Cg1NgLF4WtreGKwUL9euTe8zKz9FfP7mEbkoBMbSsgBA9M1', '5E9w5KDj3V2s8qfcELtNBLGqzUG4uKKaTxurMhmAj9QkdKRY', '5Gpo1r8SSWqn9M9MD7LKZQaoQUBVp1mRbobbAZgRdqoadAFB', '5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3', '5H66wXNiKjB7qQPLQbU3W39wcaCDNd6x5AoLn4pWJU7CY8e1', '5FxJ13HRJmatMHWRc42NnfNa9AcbFRT12ibeHMNA2ks5STHj', '5HbScNssaEfioJHXjcXdpyqo1AKnYjymidGF8opcF9rTFZdT', '5DJcdWW3YLzEdR5JgLZ3FuF8FmsYzwjR9uPi3NoxWHjLtRcf', '5EPgtc4iE78gdK1sxowo1knYMeMt8tBUjniYuDVL34jXy6oE', '5G7BN7J9otbAxBKKceJa1rW6xHPVZMCMk1bsWzzS2mt8fwb5', '5DXNKTByEkFDUxMNaJL2wfKr3VnZDm9ReVAaHaJWM4NGRyYg', '5C8aben7SdFdfj5sTASDSGUs6vdJ2SkQNYv99A7B262oh2YQ', '5FsHayRT193RSYiiL2BVKwMRMzLUveZPfpdQw9p2NZKjTPcN', '5F4GRw9eMUktW6aYK3aTW6PP662uwDTWojMLsd462ot73Zxz', '5H9V3dRtJsY8mBchKkFQ32BU24Hjd5LMgLLXAgeaBwwDe9ce', '5CqeK9FsL5iiohamrGeLocLDAmgynsNivxLZWJTAZarcucyf', '5FFM6Nvvm78GqyMratgXXvjbqZPi7SHgSQ81nyS96jBuUWgt', '5CAxybERLjvK4ZnbJ7mR9YQ2kE6MvfQSv8ULSmYjvd7fMEjR', '5HEo565WAy4Dbq3Sv271SAi7syBSofyfhhwRNjFNSM2gP9M2', '5HEqrGrV4VWFMuiRMUqBPWB2maCptNjpYMD155ZX97pxxwax', '5EJSxrYS7zGXn6H9vQH8KEu5ttQ4MmLYomjCucMGgA8byZ6s', '5ENmejdm5EiPtHkRvDgMkNtnPiBP1puKy1VYry8oc2MASsaK', '5Ci4HZAaiC15mP9mm2RQBd77mPxSZYBLRypKTB3YiKatuq5C', '5F1WUSfFNz2SLsADsvwX6AXdMzQDNT7wKG9t8FGqsfXbmna6', '5D28uvtucmV1gqg9rqrYbK1nULjv2CpbstZMaSfbamFZjyNL', '5EHmDZruMCRZkXYq85BkZT46HMMJ66wnCX6i9xtq5r3xTyuM', '5FH9UCCwkTW6WpYGG4KdLosic3SsxtHkdrq8ioeZb7wD4nxx', '5G9AZnfc8Xhos6L8y6ima7BsFALFwTrpx1Wg91F4fC3S8NP7', '5D74bFYrWJSvtZwz5bCePazHvL3vwVNF3FZKyj9b5ajtBMWe', '5FL7XSKGyWS1X4sit3mPaVdhNkKB96FvVsrGn4pMJ3opSwpi', '5HNQURvmjjYhTSksi8Wfsw676b4owGwfLR2BFAQzG7H3HhYf', '5E56G7aFhNgMbHRXifysGoBWNrqzqEuqH2Lfr7kqhncc4Stn', '5HTc8ev7Uos9n1Xqiyc7Fse5R5wxyavXD7MGi3c57v4QRpUk', '5F9AV5DjZp3fc4W7unb5Qb77B4cGh5ft2ggrtdSKAv1QSWEF', '5G94rT1kpwpP4kMzrx2iHbRM7PL2Woj7en9roJonLfUzrHDt', '5Cu7gnJMv28jAvRUvtPNXfFgk5vHfhSA1RkgGzpumeMi6y3h', '5EtHvfUMV5CXsohbw5sgBwtNYhaATk87azRQYc9RfRzxzN1c', '5DDRVmexX8fPW1yFhV7JJTQD4zoTCx8kXrThJi6Puom8btKq', '5DwPQXyD3vudBuwEXkWGBD3S2Hx8xgCEbjnrfGUDUpH9zGoP', '5FeH9RJy8aVzK16acNhpH5TfnQJuZjp4PWmjXowQRh7WAY4G', '5HNUYyqSkswLuUtQf6V49f5kdbBmTcdamWg4UAqc6pcp6WLL', '5Hh7TBQSVc2SiWvvtDafr5xAmupUoNwBSGtQFcqUhy7BYGjV', '5GnSVqh26emJxRjvEfDeRgdiEyc3jJ8hRyDyeaB5xzrbNHws', '5C4rSowurxm3xLGWaVSw7dL1LMHZVqGVMkovHhG96wPnMEAN', '5CzSZxhjPStrx4FmQRMCBnCwr13NWSjMsNdLyAYiJJw8WVFW', '5GExrXrQysfitZeadZshSSgTHjXBDhWicAQ4EoWdhEaWFVRZ', '5FH4PAw125NnLBsMeH6dnY7eGDrWKgF9cfXetxbp2xKRDnbm', '5Fq5v71D4LX8Db1xsmRSy6udQThcZ8sFDqxQFwnUZ1BuqY5A', '5E483QTi8rh7bne7JLSJoL2uazSpWuYVRygGciayqFSpBcV7', '5GjpavAhJGQsNkc84efbuHF7T37JQmg4YmM9xtuTYzVS756Q', '5F28j3j2vUXnib8xKGYJj2uRNtwA9DSzcFQT149NeiqibT8t', '5H3sCSf1CmGuatkhJbsh6eMHivZyZoAYViCe42B8GFssohCD', '5DSKxiMEoE3Nr8wutGh4sUrpyEcUWT2c1QYpCoHuQyNQwQ4Z', '5CPzVgYhQVeRjdYF61CAEpnpEEM5EWS8m6rqCgvtzsju4EAF', '5Dd8gaRNdhm1YP7G1hcB1N842ecAUQmbLjCRLqH5ycaTGrWv', '5GEBANDwRk56nRVB6J2rV9QGk2jjPSiwbvpfJ1F3VifQhDud', '5CaJP3u5rKZ5gR4APBsAmk7Bjqs5zhCgUwverZYQAkhHF1r5', '5GLDZSmqMYKyxkJYdFMLzCwxZrc254LFkXHLQhPArqGJxU2Z', '5EUEfch4AKMuQC9uVDHm2pfdTmMFSzFgYTpTccWvv7ohvGzp', '5EWULtYyU6pMeBjfMpK5jFdwguNigi4r39cuq4gdUFWpJGFH', '5CVS9d1NcQyWKUyadLevwGxg6LgBcF9Lik6NSnbe5q59jwhE', '5G21ZX5NbqLErZfRyFKpq4j4jLDsHvwKSWxqPse2RNKBgmnk', '5GNwYW5qvLb4iiDxQSWHuwUyeZTEPbBZFXYNvqZBR9kzyhum', '5F1TLzLLiKj76JBNH1smjm6EicU6ufFpGqc7GE3KiDiVrWvn']

# Fetch specs and display them
with st.spinner('Fetching hardware specifications...'):
    specs_details = fetch_hardware_specs(api, hotkeys)
    allocated_keys = get_allocated_hotkeys(api)

# Display fetched hardware specs
display_hardware_specs(specs_details, allocated_keys)
