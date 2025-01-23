"""Data Processing and Deduplication Pipeline Script.

This script processes data from a given S3 bucket, applies several filters,
and performs deduplication using Minhash.

Usage:
    python main.py --hf_repo <HF account repo> --data_url <data URL> --total_tasks <number of tasks> --cpus_per_task <number of CPUs per task> --limit <optional limit>

Example:
    python main.py --hf_repo barney49/original_data --total_tasks 4 --cpus_per_task 32 --limit 1000
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
from colorama import Fore, init
# Initialize colorama
init(autoreset=True)

# Custom logging formatter to add colors and emojis
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
    }

    def format(self, record):
        log_level = record.levelname
        color = self.COLORS.get(log_level, Fore.WHITE)
        
        message = super().format(record)
        return f"{color} {message}"

# Configure logging with color logging for console output
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Outputs to the console
        logging.FileHandler('commit_processing.log', mode='w')  # Logs to a file
    ],
)

# Get the root logger
logger = logging.getLogger()

# Set custom colored formatter for the console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers[0] = console_handler 

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading 'punkt' package...")
    nltk.download('punkt')
    
def get_config() -> bt.config:
    """
    Initialize and parse command-line arguments and add Bittensor-specific arguments.

    Returns:
        bt.Config: Parsed configuration.
    """
    parser = argparse.ArgumentParser(description="Upload dataset to Hugging Face and commit dataset URL to Bittensor subtensor chain.")
    # parser.add_argument("--hf_repo", type=str,  help="The Hugging Face repository to upload the dataset.")
    parser.add_argument("--netuid", type=str, default=250, help="The unique identifier for the network.")
    parser.add_argument("--hf_repo", type=str, help="Link to the repo on huggingface.")
    parser.add_argument('--total_tasks', type=int, default=4, help='Total number of tasks')
    parser.add_argument('--cpus_per_task', type=int, default=32, help='Number of CPUs per task')
    parser.add_argument('--limit', type=int, default=-1, help='Number of records to process in WarcReader')

    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config
def remove_result_folder(folder_path):
    shutil.rmtree(folder_path)
    logging.info(f"Folder '{folder_path}' removed successfully.")

async def main(config):
    """
    Main function to commit dataset to Bittensor subtensor chain.

    Args:
        config (bt.Config): Configuration object.
    """
    try:
        print(f"bittensor version: {bt.__version__}")


        while True:  # Infinite loop to keep the script running continuously
            start = time.time()
            # Initialize logging
            bt.logging(config=config)
            # Initialize wallet and subtensor
            wallet = bt.wallet(config=config)
            subtensor = bt.subtensor(config=config)
            timestamp = datetime.now()
            timezone = timestamp.astimezone().tzname()

            message =f"{timestamp}{timezone}"
            signature = generate_signature(wallet, message)
            # Retrieve the metagraph
            metagraph: bt.metagraph = subtensor.metagraph(config.netuid)

            # Ensure the wallet is registered
            hotkey, uid = assert_registered(wallet, metagraph)
            logging.info(f"Miner: {hotkey} is registered with uid: {uid}")
            warc_files = fetch_warc_files(hotkey, message, signature)
            logging.info(f"Received {len(warc_files)} warc files")

            if not warc_files:  
                logging.warning("WARC files not found, waiting for 2 hours before retrying...")
                await asyncio.sleep(2 * 3600)  
                continue  

            result_path = f"./result"
            # # Remove result path if it already exists
            if os.path.exists(result_path):
                logging.warning(f"Removing result folder {result_path}")
                remove_result_folder(result_path)
            
            logging.info(f"Refining {len(warc_files)} warc files 📚")
            refiner = DataRefiner(warc_files, result_path, config.total_tasks, config.cpus_per_task, config.limit)
            processing_success = refiner.refine()

            if processing_success:
                logging.info("Data processing completed successfully 🎉")

                hf_repo_hash = upload_dataset(result_path, config.hf_repo)
                
                if hf_repo_hash:
                    while True:
                        try:
                            logging.info(f"Committing dataset to subtensor chain {hf_repo_hash}:{config.hf_repo}")
                            subtensor.commit(wallet, config.netuid, f"{hf_repo_hash}:{config.hf_repo}")
                            logging.info("🎉 Successfully committed dataset to subtensor chain 🎉")
                            break
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            logging.warning(f"Can't commit to subtensor chain now, retrying in 300 seconds..{e}")
                            await asyncio.sleep(300)
                    
                    max_retries = 10
                    retry_count = 0

                    while retry_count < max_retries:
                        try:
                            logging.info(f"Sending finish request for hotkey {hotkey} 📤")
                            message =f"{timestamp}{timezone}"
                            signature = generate_signature(wallet, message)
                            response = send_finish_request(hotkey, message, signature, config.hf_repo)
                            if response:
                                break
                        except Exception as e:
                            logging.warning(f"Can't send finish request now, trying again in 20 seconds {e}")
                            await asyncio.sleep(20)
                            retry_count += 1
            end = time.time() - start
            logging.info(f"Processing time: {end:.2f} seconds 🕒")

            await asyncio.sleep(8 * 3600) 
    except KeyboardInterrupt:
        print("Process interrupted by user.")

if __name__ == "__main__":

    load_dotenv()

    config = get_config()

    logging.info("Starting the mining 🚀")

    asyncio.run(main(config))
