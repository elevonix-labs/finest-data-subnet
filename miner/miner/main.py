"""Data Processing and Deduplication Pipeline Script.

This script processes data from a given S3 bucket, applies several filters,
and performs deduplication using Minhash.

Usage:
    python main.py --hf_repo <HF account repo> --data_url <data URL> --total_tasks <number of tasks> --cpus_per_task <number of CPUs per task> --limit <optional limit>

Example:
    python main.py --hf_repo tobiashomie/refined_dataset --total_tasks 4 --cpus_per_task 32 --limit 1000
"""

from datetime import datetime
import argparse
from dotenv import load_dotenv
import os
import bittensor as bt
import nltk
import time
from miner.get_task import fetch_warc_files, send_finish_request
from miner.upload_to_hf import upload_dataset
from miner.refining_dataset import DataRefiner
import asyncio
import shutil
import logging
from utils import assert_registered
from generate import generate_signature
from miner.check_slurm import terminate_slurm_jobs
from miner.logger_config import logger

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    logger.info("Downloading 'punkt' package...")
    nltk.download("punkt")


def get_config() -> bt.config:
    """
    Initialize and parse command-line arguments and add Bittensor-specific arguments.

    Returns:
        bt.Config: Parsed configuration.
    """
    parser = argparse.ArgumentParser(
        description="Upload dataset to Hugging Face and commit dataset URL to Bittensor subtensor chain."
    )
    parser.add_argument(
        "--netuid", type=int, default=63, help="The unique identifier for the network."
    )
    parser.add_argument(
        "--hf_repo", type=str, help="The Hugging Face repository to upload the dataset."
    )
    parser.add_argument(
        "--total_tasks", type=int, default=4, help="Total number of tasks"
    )
    parser.add_argument(
        "--cpus_per_task", type=int, default=32, help="Number of CPUs per task"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=-1,
        help="Number of records to process in WarcReader",
    )

    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config


def remove_result_folder(folder_path):
    shutil.rmtree(folder_path)
    logging.critical(f"Folder '{folder_path}' removed successfully.")


async def processing(config):
    """
    Main function to commit dataset to Bittensor subtensor chain.

    Args:
        config (bt.Config): Configuration object.
    """
    logger.info(f"bittensor version: {bt.__version__}")

    while True:  # Infinite loop to keep the script running continuously

        start = time.time()
        bt.logging(config=config)
        wallet = bt.wallet(config=config)
        subtensor = bt.subtensor(config=config)
        timestamp = datetime.now()
        timezone = timestamp.astimezone().tzname()

        message = f"{timestamp}{timezone}"
        signature = generate_signature(wallet, message)
        metagraph: bt.metagraph = subtensor.metagraph(config.netuid)
        hotkey, uid = assert_registered(wallet, metagraph)
        if not hotkey:
            logger.error(f"You are not registered. \nUse: \n`btcli s register --netuid {metagraph.netuid}` to register via burn \n or btcli s pow_register --netuid {metagraph.netuid} to register with a proof of work")
            return
        logger.info( f"You are registered with address: {wallet.hotkey.ss58_address} and uid: {uid}")
        warc_files = fetch_warc_files(hotkey, message, signature)
       
        logger.info(f"Received {len(warc_files)} warc files")

        if not warc_files:
            logger.warning(
                "WARC files not found, waiting for 2 hours before retrying..."
            )
            await asyncio.sleep(2 * 3600)
            continue

        result_path = f"./result"
        if os.path.exists(result_path):
            logger.warning(f"Removing result folder {result_path}")
            remove_result_folder(result_path)

        logger.info(f"Refining {len(warc_files)} warc files 📚")
        refiner = DataRefiner(
            warc_files,
            result_path,
            config.total_tasks,
            config.cpus_per_task,
            config.limit,
        )
        processing_success = refiner.refine()

        if processing_success:
            logger.info("Data processing completed successfully 🎉")

            hf_repo_id = upload_dataset(result_path, config.hf_repo)

            if hf_repo_id:
                while True:
                    try:
                        logger.info(
                            f"Committing dataset to subtensor chain {hf_repo_id}"
                        )
                        subtensor.commit(wallet, config.netuid, f"{hf_repo_id}")
                        logger.info(
                            "🎉 Successfully committed dataset to subtensor chain 🎉"
                        )
                        break
                    except Exception as e:
                        import traceback

                        traceback.print_exc()
                        logger.error(
                            f"Can't commit to subtensor chain now, retrying in 300 seconds..{e}"
                        )
                        await asyncio.sleep(300)

                max_retries = 10
                retry_count = 0

                while retry_count < max_retries:
                    try:
                        logger.info(
                            f"Sending finish request for hotkey {hotkey} 📤"
                        )
                        message = f"{timestamp}{timezone}"
                        signature = generate_signature(wallet, message)
                        response = send_finish_request(
                            hotkey, message, signature, f"{hf_repo_id}"
                        )
                        if response:
                            break
                    except Exception as e:
                        logger.error(
                            f"Can't send finish request now, trying again in 20 seconds {e}"
                        )
                        await asyncio.sleep(20)
                        retry_count += 1
        else:
            logger.error("Data processing failed, waiting for 8 hours before retrying 🕒")
            await asyncio.sleep(8 * 3600)
            continue
        end = time.time() - start
        logger.info(f"Processing time: {end:.2f} seconds 🕒")
        
        logger.error("Waiting for 8 hours before starting next task again 🕒")
        try:
            await asyncio.wait_for(asyncio.sleep(8 * 3600), timeout=8 * 3600)
        except asyncio.TimeoutError:
            pass 

def main():
    try:
        config = get_config()
        logger.info("Initiating the mining process 🚀")
        asyncio.run(processing(config))

    except KeyboardInterrupt:
        logger.error("🔴 Mining process interrupted by user.")
        terminate_slurm_jobs()


if __name__ == "__main__":

    load_dotenv()

    main()