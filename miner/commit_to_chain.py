import sys
import os
import bittensor as bt
import torch
import argparse
import asyncio
import traceback
import time

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
    parser.add_argument("--hf_url", type=str, default="https://huggingface.co/gpt2", help="The Hugging Face URL to load the dataset from")
    
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
    utils.assert_registered(wallet, metagraph)
    
    # Generate a unique hash for the dataset
    hf_url_hash = utils.get_hash_of_two_strings(config.hf_url, wallet.hotkey.ss58_address)
    
    # Loop to commit dataset to the subtensor chain, with retry on failure
    no_bug = False
    
    while not no_bug:
        try:
            subtensor.commit(wallet, config.netuid, f"{hf_url_hash}:{config.hf_url}")
            no_bug = True
            bt.logging.success(f"🎉 Successfully committed dataset to subtensor chain")
        except BaseException as e:
            traceback.print_exc()
            bt.logging.error(f"Error while committing to subtensor chain: {e}, retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    # Parse and print configuration
    config = get_config()
    
    # Run the main function asynchronously
    asyncio.run(main(config))
