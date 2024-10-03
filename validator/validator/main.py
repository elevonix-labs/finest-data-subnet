import sys
import os
import asyncio
import csv
import time
import argparse
from dotenv import load_dotenv
from collections import defaultdict

import bittensor as bt
from datasets import load_dataset
import requests

from config import generate_training_config
from train import start_training_and_kill
from evaluate import run_lighteval
from check import DataProcessor

# Add the directory containing 'utilities' to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from utilities import utils

# Dictionary to store previous commits for comparison
previous_commits = defaultdict(dict)

def get_config():
    """
    Initialize and parse command-line arguments and add Bittensor-specific arguments.

    Returns:
        config (bt.Config): Parsed configuration.
    """
    parser = argparse.ArgumentParser(description="Commit dataset to Bittensor subtensor chain.")
    
    parser.add_argument("--netuid", type=str, default="204", help="The unique identifier for the network")
    parser.add_argument("--interval", type=int, default=1, help="Time interval in hours between commit checks")
    parser.add_argument("--world_size", type=int, default=1, help="Number of processes (usually corresponds to the number of GPUs)")
    
    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config

async def check_commits(config: bt.config):
    """
    Check and compare commits for all uids in the metagraph.

    Args:
        config (bt.config): Configuration object.
    """
    try:
        # Initialize logging, wallet, and subtensor
        bt.logging(config=config)
        wallet = bt.wallet(config=config)
        subtensor = bt.subtensor(config=config)
        metagraph: bt.metagraph = subtensor.metagraph(config.netuid)
        
        # Ensure the wallet is registered
        _ , uid = utils.assert_registered(wallet, metagraph)
        print(metagraph)

        csv_data = [["uid", "hf_url", "metric", "value", "stderr", "training_time", "evaluating_time", "total_time"]]

        for uid in metagraph.uids:
            print(uid)
            try:
                # Fetch and compare the current commit
                current_commit = subtensor.get_commitment(netuid=204, uid=uid)
                print(f"Current commit for uid {uid}: {current_commit}")

                if current_commit is not None:
                    previous_commit = previous_commits[config.netuid].get(uid)
                    if previous_commit != current_commit:
                        hf_url = utils.extract_commit(current_commit)
                        print(hf_url)

                        api_url = os.getenv("API_URL")
                                        
                        response = requests.post(f"{api_url}/check-dataset/",
                                                json = {
                                                    "uid" : 0,
                                                })
                        warc_files =  response.json().get('warc_files')

                        hf_url = 'barney49/original_data'  # Replace with your actual Hugging Face dataset URL
                        processor = DataProcessor(warc_files=warc_files, hf_url=hf_url, num_samples=30)
                        scores = processor.run()
                        print("Match Scores:", scores)

                        if generate_training_config(hf_url):
                            start_time = time.time()
                            training_success = start_training_and_kill('validator/config.yaml', config.world_size)
                            training_time = time.time() - start_time
                            print(f"start_training_and_kill took {training_time:.2f} seconds")
                            
                            matches = None
                            evaluating_time = None
                            if training_success:
                                start_time = time.time()
                                matches = run_lighteval(config.world_size)
                                evaluating_time = time.time() - start_time
                                print(f"run_lighteval took {evaluating_time:.2f} seconds")

                            print(matches)
                            for match in matches or []:
                                metric, value, stderr = match
                                csv_data.append([uid, hf_url, metric, value, stderr, f"{training_time:.2f}", f"{evaluating_time:.2f}", f"{training_time + evaluating_time:.2f}"])
                        
                    # Update the stored commit
                    previous_commits[config.netuid][uid] = current_commit

            except Exception as e:
                print(f"Error processing uid {uid}: {e}")

        # Write the accumulated data to a CSV file
        file_path = "results.csv"
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

    except Exception as e:
        print(f"Error in check_commits: {e}")

async def main(config: bt.config):
    """
    Main function to repeatedly check commits at specified intervals.

    Args:
        config (bt.config): Configuration object.
    """


    while True:
        await check_commits(config)
        print(f"Sleeping for {config.interval} hour(s)...")
        await asyncio.sleep(config.interval * 3600)

if __name__ == "__main__":
    # Parse and print configuration
    config = get_config()
    
    load_dotenv()
    # Run the main function asynchronously
    asyncio.run(main(config))
