import bittensor as bt
import numpy as np
import utils
import redis
import time
from utils import process_weights_for_netuid, convert_weights_and_uids_for_emit
import logging

def set_weights(scores: list, config: bt.config, metagraph: bt.metagraph, subtensor: bt.subtensor):
    """Sets weights on the blockchain based on provided scores."""
    
    if np.isnan(scores).any():
        logging.warning("Scores contain NaN values. Exiting weight setting.")
        return

    # Compute the norm of the scores
    norm = np.linalg.norm(scores, ord=1, axis=0, keepdims=True)

    if np.any(norm == 0) or np.isnan(norm).any():
        logging.warning("Norm is zero or NaN. Adjusting to avoid division by zero.")
        norm = np.ones_like(norm)  # Avoid division by zero or NaN

    # Compute raw_weights safely
    raw_weights = scores / norm

    wallet = bt.wallet(config=config)

    try:
        processed_weight_uids, processed_weights = process_weights_for_netuid(
            uids=metagraph.uids,
            weights=raw_weights,
            netuid=config.netuid,
            subtensor=subtensor,
            metagraph=metagraph,
        )

        uint_uids, uint_weights = convert_weights_and_uids_for_emit(
            uids=processed_weight_uids, weights=processed_weights
        )
        result, msg = subtensor.set_weights(
            wallet=wallet,
            netuid=config.netuid,
            uids=uint_uids,
            weights=uint_weights,
            wait_for_finalization=False,
            wait_for_inclusion=False,
        )

        if result:
            logging.info("set_weights on chain successfully!")
        else:
            logging.error(f"set_weights failed: {msg}")

    except Exception as e:
        logging.error(f"An error occurred during weight setting: {e}")

def main(config: bt.config, subtensor: bt.subtensor):
    """Main loop to periodically set weights."""

    while True:
        try:
            if subtensor.get_current_block() % 100 == 0:
                metagraph: bt.metagraph = subtensor.metagraph(config.netuid)
                redis_queue = redis.Redis(host='localhost', port=6379, db=0)
                raw_scores = redis_queue.hgetall('scores')
                scores =  [float(raw_scores.get(bytes(str(uid), 'utf-8'), b'0')) for uid in metagraph.uids]
                set_weights(scores, config, metagraph, subtensor)
                time.sleep(10)
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")

if __name__ == "__main__":

    config = utils.get_config()
    subtensor = bt.subtensor(config=config)
    main(config, subtensor)