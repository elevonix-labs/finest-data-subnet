import os
import sys
import time
import logging
from typing import Any, cast
import bittensor as bt
from bittensor.core.extrinsics.serving import get_metadata
import redis
import json
from collections import defaultdict
import utils

previous_commits = defaultdict(dict)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Outputs to the console
        logging.FileHandler('commit_fetching.log', mode='w')  # Overwrites the log file each time
    ]
)

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

        logging.info("Started fetching commits...")

        while True:
            logging.info("Fetching commits...")
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
                        logging.info(f"Pushed commit data to Redis: {data}")
                        previous_commits[uid] = current_commit

                except Exception as e:
                    logging.error(f"Error fetching commit for UID {uid}: {e}", exc_info=True)

            # Sleep for the interval defined in config
            logging.info("sleeping 5 mins for next fetching commits")
            time.sleep(300)

    except Exception as e:
        logging.error(f"Error in fetch_commits: {e}", exc_info=True)

if __name__ == "__main__":

    redis_queue = redis.Redis(host='localhost', port=6379, db=0)

    config = utils.get_config()
    fetch_commits(config, redis_queue)
