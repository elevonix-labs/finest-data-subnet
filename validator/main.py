import sys
import os
import bittensor as bt
import torch
import argparse
import asyncio
import traceback
import time
from datasets import load_dataset

# Add the directory containing 'utilities' to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import utils

def get_config():
    """
    Initialize and parse command-line arguments and add Bittensor-specific arguments.

    Returns:
        config (bt.Config): Parsed configuration.
    """
    parser = argparse.ArgumentParser(description="Commit dataset to Bittensor subtensor chain.")
    
    parser.add_argument("--netuid", type=str, default="1", help="The unique identifier for the network")
    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config

async def main(config: bt.config):
    """
    Main function to commit dataset to Bittensor subtensor chain.

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
    
    try :
        for uid in metagraph.uids:
            commit = subtensor.get_commitment(netuid=1, uid = uid)
            if commit is not None:
                hf_url =utils.extract_commit(commit)

                print(hf_url)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    # Parse and print configuration
    config = get_config()
    
    # Run the main function asynchronously
    asyncio.run(main(config))
