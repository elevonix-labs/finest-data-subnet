import os
import sys
import time
from typing import Any, cast
import bittensor as bt
from bittensor.core.extrinsics.serving import get_metadata
import argparse
import redis
import json
from collections import defaultdict

import utils

previous_commits = defaultdict(dict)

def get_config():
    """
    Initialize and parse command-line arguments and add Bittensor-specific arguments.
    Returns:
        config (bt.Config): Parsed configuration.
    """
    parser = argparse.ArgumentParser(description="Commit dataset to Bittensor subtensor chain.")
    parser.add_argument("--netuid", type=str, default="250", help="The unique identifier for the network")
    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config


def fetch_commits(config: bt.config, redis_queue: redis.Redis):
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

                        data = {
                            "uid": int(uid),
                            "current_commit": current_commit,
                            "commit_block": commit_block
                        }
                        redis_queue.rpush("commit_queue", json.dumps(data))
                        print(f"pushing to redis {data}")
                        previous_commits[uid] = current_commit

                except Exception as e:
                    print(f"Error fetching commit for uid {uid}: {e}")

            # Sleep for the interval defined in config
            time.sleep(1 * 10)

    except Exception as e:
        print(f"Error in fetch_commits: {e}")

if __name__ == "__main__":

    redis_queue = redis.Redis(host='localhost', port=6379, db=0)

    config = get_config()
    fetch_commits(config, redis_queue)