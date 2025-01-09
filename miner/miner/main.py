"""Data Processing and Deduplication Pipeline Script.

This script processes data from a given S3 bucket, applies several filters,
and performs deduplication using Minhash.

Usage:
    python main.py --hf_repo <HF account repo> --data_url <data URL> --total_tasks <number of tasks> --cpus_per_task <number of CPUs per task> --limit <optional limit>

Example:
    python main.py --hf_repo barney49/original_data --total_tasks 4 --cpus_per_task 32 --limit 1000
"""

import sys
import argparse
from dotenv import load_dotenv
import os
import bittensor as bt
import nltk
import time
from miner.get_task import fetch_warc_files, send_finish_request
from miner.upload_to_hf import upload_dataset
from miner.refining_dataset import DataRefiner
import asyncio
import shutil

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from utilities import utils

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading 'punkt' package...")
    nltk.download('punkt')
    
def get_config() -> bt.config:
    """
    Initialize and parse command-line arguments and add Bittensor-specific arguments.

    Returns:
        bt.Config: Parsed configuration.
    """
    parser = argparse.ArgumentParser(description="Upload dataset to Hugging Face and commit dataset URL to Bittensor subtensor chain.")
    # parser.add_argument("--hf_repo", type=str,  help="The Hugging Face repository to upload the dataset.")
    parser.add_argument("--netuid", type=str, default=250, help="The unique identifier for the network.")
    parser.add_argument("--hf_repo", type=str, help="Link to the repo on huggingface.")
    parser.add_argument('--total_tasks', type=int, default=4, help='Total number of tasks')
    parser.add_argument('--cpus_per_task', type=int, default=32, help='Number of CPUs per task')
    parser.add_argument('--limit', type=int, default=-1, help='Number of records to process in WarcReader')

    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config
def remove_result_folder(folder_path):
    shutil.rmtree(folder_path)
    print(f"Folder '{folder_path}' removed successfully.")

async def main(config):
    """
    Main function to commit dataset to Bittensor subtensor chain.

    Args:
        config (bt.Config): Configuration object.
    """
    print(f"bittensor version: {bt.__version__}")
    while True:  # Infinite loop to keep the script running continuously
        start = time.time()
        # Initialize logging
        bt.logging(config=config)

        # Initialize wallet and subtensor
        wallet = bt.wallet(config=config)
        subtensor = bt.subtensor(config=config)

        # Retrieve the metagraph
        metagraph: bt.metagraph = subtensor.metagraph(config.netuid)

        # Ensure the wallet is registered
        hotkey, _ = utils.assert_registered(wallet, metagraph)

        warc_files = fetch_warc_files(hotkey)

        if not warc_files:  
            bt.logging.info("WARC files not found, waiting for 2 hours before retrying...")
            await asyncio.sleep(2 * 3600)  
            continue  

        result_path = f"./result"
        # Remove result path if it already exists
        if os.path.exists(result_path):
            remove_result_folder(result_path)
        refiner = DataRefiner(warc_files, result_path, config.total_tasks, config.cpus_per_task, config.limit)
        processing_success = refiner.refine()

        if processing_success:

            bt.logging.success("🎉 Data processing completed successfully")

            hf_repo_hash = upload_dataset(result_path, config.hf_repo)
            
            if hf_repo_hash:
                while True:
                    try:
                        print(f"{hf_repo_hash}:{config.hf_repo}")
                        subtensor.commit(wallet, config.netuid, f"{hf_repo_hash}:{config.hf_repo}")
                        bt.logging.success("🎉 Successfully committed dataset to subtensor chain")
                        break
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        bt.logging.error(f"Error while committing to subtensor chain: {e}, retrying in 300 seconds...")
                        await asyncio.sleep(300)
                
                send_finish_request(hotkey)

        end = time.time() - start
        print(f"Processing time: {end:.2f} seconds")

        await asyncio.sleep(8 * 3600) 

if __name__ == "__main__":

    load_dotenv()

    config = get_config()

    asyncio.run(main(config))
