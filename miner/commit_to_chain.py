import bittensor as bt
import torch
import argparse
import asyncio
import traceback
import time
def get_config():
    # Initialize an argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--netuid", type = str, default = "18", help = "The unique identifier for the network")
    parser.add_argument("--hf_url", type = str, default = "https://huggingface.co/gpt2", help = "The huggingface url to load the dataset from")
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config( parser )
    return config

async def main(config: bt.config):
    bt.logging(config = config)
    wallet = bt.wallet( config = config )
    subtensor = bt.subtensor( config = config )
    metagraph: bt.metagraph = subtensor.metagraph(config.netuid)
    no_bug = False
    while no_bug is False:
        try:
            subtensor.commit(wallet, config.netuid, config.hf_url)
            bt.logging.success(f"📝 committed dataset to subtensor chain")
            no_bug = True
            traceback.print_exc()
        except BaseException as e:
            traceback.print_exc()
            bt.logging.error(f"Error while committing to subtensor chain: {e}, retrying now...")
            time.sleep(5)
    
    bt.logging.success(f"🎉 Successfully committed dataset to subtensor chain")

if __name__ == "__main__":
    # Parse and print configuration
    config = get_config()
    
    # print(config)
    asyncio.run(main(config))