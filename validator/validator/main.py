import sys
import os
import bittensor as bt
import torch
import argparse
import asyncio
import traceback
import time
from datasets import load_dataset
from collections import defaultdict
from config import generate_training_config
from train import start_training_and_kill
from evaluate import run_lighteval
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
    
    parser.add_argument("--netuid", type=str, default="1", help="The unique identifier for the network")
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
    # Initialize logging
    bt.logging(config=config)
    # Initialize wallet and subtensor
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    # Retrieve the metagraph
    metagraph: bt.metagraph = subtensor.metagraph(config.netuid)
    
    # Ensure the wallet is registered
    uid = utils.assert_registered(wallet, metagraph)
    
    print(metagraph)
    for uid in metagraph.uids:
        print(uid)
        try:
            # Fetch the current commit
            current_commit = subtensor.get_commitment(netuid=204, uid=uid)
            print(f"Current commit for uid {uid}: {current_commit}")

            if current_commit is not None:
                # Compare with the previous commit
                previous_commit = previous_commits[config.netuid].get(uid)
                if not previous_commit and previous_commit != current_commit:
                    hf_url = utils.extract_commit(current_commit)
                    if generate_training_config(hf_url):
                        if start_training_and_kill('validator/config.yaml',config.world_size):
                            run_lighteval(config.world_size)
                    # print(f"Commit changed for uid {uid} from {previous_commit} to {current_commit}")
                    
                # Update the stored commit
                previous_commits[config.netuid][uid] = current_commit
                
                hf_url = utils.extract_commit(current_commit)
        except Exception as e:
            print(e)

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
    
    # Run the main function asynchronously
    asyncio.run(main(config))
