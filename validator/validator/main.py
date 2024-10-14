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

    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config

async def fetch_commits(config: bt.config):
    """
    Async task to fetch commits and put them into the commit queue.

    Args:
        config (bt.config): Configuration object.
    """
    try:
        # Initialize wallet and subtensor
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
                    print(f"Current commit for uid {uid}: {current_commit}")
                    
                    # Check if commit has changed
                    if current_commit and current_commit != previous_commits[config.netuid].get(uid):
                        # Add the commit to the queue for evaluation
                        await commit_queue.put((uid, current_commit))
                        previous_commits[config.netuid][uid] = current_commit

                except Exception as e:
                    print(f"Error fetching commit for uid {uid}: {e}")
            # Sleep for the interval defined in config
            await asyncio.sleep(10)

    except Exception as e:
        print(f"Error in fetch_commits: {e}")

async def process_commits(config: bt.config):
    """
    Async task to process commits from the queue.

    Args:
        config (bt.config): Configuration object.
    """
    csv_data = [["uid", "hf_url", "metric", "value", "stderr", "training_time", "evaluating_time", "total_time"]]
    
    while True:
        # Get a commit from the queue
        uid, current_commit = await commit_queue.get()

        try:
            # Extract Hugging Face URL from commit
            hf_url = utils.extract_commit(current_commit)
            print(f"Processing commit for uid {uid} with hf_url {hf_url}")

            api_url = os.getenv("API_URL")
            response = requests.post(f"{api_url}/check-dataset/", json={"uid": uid})
            warc_files = response.json().get('warc_files')

            processor = DataProcessor(warc_files=warc_files, hf_url=hf_url, num_samples=30)
            scores = processor.run()
            print("Match Scores:", scores)

            print(current_commit)
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

            # Mark task as done
            commit_queue.task_done()

        except Exception as e:
            print(f"Error processing commit for uid {uid}: {e}")

        # Write the accumulated data to a CSV file
        file_path = "results.csv"
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

async def main(config: bt.config):
    """
    Main function to start commit fetching and processing tasks.
    """
    # Create tasks for fetching and processing commits
    fetch_task = asyncio.create_task(fetch_commits(config))
    process_task = asyncio.create_task(process_commits(config))

    # Run both tasks concurrently and allow cancellation
    try:
        await asyncio.gather(fetch_task, process_task)
    except asyncio.CancelledError:
        print("Tasks were cancelled")
    finally:
        fetch_task.cancel()
        process_task.cancel()

if __name__ == "__main__":
    # Parse and print configuration
    config = get_config()

    load_dotenv()
    # Run the main function asynchronously
    asyncio.run(main(config))
