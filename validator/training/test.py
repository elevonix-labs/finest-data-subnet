
import sys
import os
import asyncio
import csv
import time
import argparse
import numpy as np
import requests
from dotenv import load_dotenv
from collections import defaultdict
import bittensor as bt
from bittensor.extrinsics.serving import get_metadata
from datasets import load_dataset
from validator.config import generate_training_config
from validator.train import start_training_and_kill
from validator.evaluate import run_lighteval
from validator.check import DataProcessor
from typing import cast, Any

# Add the directory containing 'utilities' to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from utilities import utils

# Dictionary to store previous commits for comparison
previous_commits = defaultdict(dict)
previous_scores = defaultdict(float)

# Queue to manage commit evaluation and processing
commit_queue = asyncio.Queue()

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
    parser.add_argument("--epoch_duration", type=int, default=86400, help="Duration of one epoch in seconds (default: 86400 seconds = 24 hours)")

    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config

def calculate_score(time_elapsed, value, stderr, sample_similarities, x=0.5):
    """
    Calculate a score based on time elapsed, value, and sample similarities.
    """
    if all(similarity <= 70 for similarity in sample_similarities):
        return 0  # If all similarities are too low, return 0 score
    
    data_quality = value / (stderr + 1e-8)
    score = (time_elapsed * x) + (data_quality * (1 - x))
    return score

async def fetch_commits(config: bt.config):
    """
    Async task to fetch commits and put them into the commit queue.

    Args:
        config (bt.config): Configuration object.
    """
    try:
        wallet = bt.wallet(config=config)
        subtensor = bt.subtensor(config=config)
        metagraph: bt.metagraph = subtensor.metagraph(config.netuid)
        
        # Ensure the wallet is registered
        _ , uid = utils.assert_registered(wallet, metagraph)

        while True:
            print("Fetching commits...")
            
            for uid in metagraph.uids:
                try:
                    # Fetch the current commit
                    current_commit = subtensor.get_commitment(netuid=config.netuid, uid=uid)
                    
                    # Check if commit has changed
                    if current_commit and current_commit != previous_commits.get(uid):
                        hotkey = metagraph.hotkeys[uid]
                        metadata = cast(dict[str, Any], get_metadata(subtensor, metagraph.netuid, hotkey))
                        commit_block = metadata["block"]

                        api_url = os.getenv("API_URL")
                        response = requests.post(f"{api_url}/finish-task/", json={"uid": int(uid)})

                        if response.status_code == 200:
                            await commit_queue.put((uid, current_commit, commit_block))
                            previous_commits[uid] = current_commit
                        else:
                            print(f"Error: Failed to finish dataset for {uid}. Status code: {response.status_code}")

                except Exception as e:
                    print(f"Error fetching commit for uid {uid}: {e}")

            # Sleep for the interval defined in config
            await asyncio.sleep(config.interval * 3600)

    except Exception as e:
        print(f"Error in fetch_commits: {e}")

async def process_commits(config: bt.config):
    """
    Async task to process commits from the queue.

    Args:
        config (bt.config): Configuration object.
    """
    epoch_start_time = time.time()

    while True:
        current_time = time.time()
        time_elapsed_since_epoch = current_time - epoch_start_time

        if time_elapsed_since_epoch >= config.epoch_duration:
            
            # Process all commits in the queue
            while not commit_queue.empty():
                try:
                    uid, current_commit, commit_block = await commit_queue.get()

                    hf_url = utils.extract_commit(current_commit)

                    api_url = os.getenv("API_URL")
                    response = requests.post(f"{api_url}/check-dataset/", json={"uid": int(uid)})
                    data = response.json()
                    warc_files = data.get('warc_files')
                    request_block = data.get('request_block')

                    time_elapsed = (commit_block - request_block) * 12

                    processor = DataProcessor(warc_files=warc_files, hf_url=hf_url, num_samples=30)
                    sample_similarities = processor.run()

                    if generate_training_config(hf_url):
                        start_time = time.time()
                        training_success = start_training_and_kill('validator/config.yaml', config.world_size)
                        training_time = time.time() - start_time
                        print(f"Training took {training_time:.2f} seconds")

                        if training_success:
                            start_time = time.time()
                            matches = run_lighteval(config.world_size)
                            evaluating_time = time.time() - start_time
                            print(f"Evaluation took {evaluating_time:.2f} seconds")

                            values, stderrs = zip(*[(match[1], match[2]) for match in matches if match[0] == 'truthfulqa_mc2'])
                            
                            if values and stderrs:
                                mean_value = np.mean(values)
                                mean_stderr = np.mean(stderrs)
                            else:
                                mean_value = 0.0
                                mean_stderr = 0.0

                            score = calculate_score(time_elapsed, mean_value, mean_stderr, sample_similarities)
                            previous_scores[uid] = score
                            print(f"Score for uid {uid}: {score}")
                        else:
                            print(f"Training failed for uid {uid}")

                    commit_queue.task_done()

                except Exception as e:
                    print(f"Error processing commit: {e}")
            
            # Reset epoch start time
            epoch_start_time = current_time

        await asyncio.sleep(1)

async def main(config: bt.config):
    """
    Main function to start commit fetching and processing tasks.
    """
    fetch_task = asyncio.create_task(fetch_commits(config))
    process_task = asyncio.create_task(process_commits(config))

    # Run both tasks concurrently
    try:
        await asyncio.gather(fetch_task, process_task)
    except asyncio.CancelledError:
        print("Tasks were cancelled")
    finally:
        fetch_task.cancel()
        process_task.cancel()

if __name__ == "__main__":
    config = get_config()
    load_dotenv()
    asyncio.run(main(config))
