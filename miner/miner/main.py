"""Data Processing and Deduplication Pipeline Script.

This script processes data from a given S3 bucket, applies several filters,
and performs deduplication using Minhash.

Usage:
    python main.py --hf_repo <HF account repo> --data_url <data URL> --total_tasks <number of tasks> --cpus_per_task <number of CPUs per task> --limit <optional limit>

Example:
    python main.py --hf_repo barney49/original_data --total_tasks 4 --cpus_per_task 32 --limit 1000
"""

import sys
import argparse
from dotenv import load_dotenv
import os
import bittensor as bt
import nltk
import requests
from datatrove.executor.slurm import SlurmPipelineExecutor
from datatrove.pipeline.dedup import MinhashDedupCluster, MinhashDedupFilter, MinhashDedupSignature
from datatrove.pipeline.dedup.minhash import MinhashConfig, MinhashDedupBuckets
from datatrove.pipeline.extractors import Trafilatura
from datatrove.pipeline.filters import (
    C4QualityFilter,
    FineWebQualityFilter,
    GopherQualityFilter,
    GopherRepetitionFilter,
    LanguageFilter,
    URLFilter,
)
from datatrove.pipeline.formatters import PIIFormatter
from datatrove.pipeline.readers import JsonlReader, WarcReader
from datatrove.pipeline.tokens import TokensCounter
from datatrove.pipeline.writers.jsonl import JsonlWriter
import tempfile
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from utilities import utils

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
    parser.add_argument("--hf_repo", type=str,  help="The Hugging Face repository to upload the dataset.")
    parser.add_argument("--netuid", type=str, default=204, help="The unique identifier for the network.")
    parser.add_argument('--total_tasks', type=int, default=4, help='Total number of tasks')
    parser.add_argument('--cpus_per_task', type=int, default=32, help='Number of CPUs per task')
    parser.add_argument('--limit', type=int, default=-1, help='Number of records to process in WarcReader')

    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config

def fetch_warc_files(hotkey):
    """Fetches warc file paths from the API."""
    try:
        api_url = os.getenv("API_URL")
        response = requests.post(f"{api_url}/get-task/",
                                 json={
                                     "hotkey": hotkey,
                                 })
        response.raise_for_status()  # Raise an error for bad responses
        warc_files = response.json().get('warc_paths')  # Assuming the API returns a JSON array of file paths
        return warc_files
    except requests.RequestException as e:
        print(f"Error fetching WARC files: {e}")
        return []

def proceed(warc_files, total_tasks, cpus_per_task, limit):
    """Main function to execute the data processing and deduplication pipeline."""
    
    MAIN_OUTPUT_PATH = f"./result"
    # MAIN_OUTPUT_PATH = f"s3://{bucket_name}"
    FILTERING_OUTPUT_PATH = f"{MAIN_OUTPUT_PATH}/base_processing"

    print(warc_files, total_tasks, cpus_per_task, limit)    
    if not warc_files:
        print("No WARC files fetched from API. Exiting.")
        return
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write('\n'.join(f"commoncrawl/{path}" for path in warc_files))
            warc_files_path = temp_file.name
    # Initial processing executor
    main_processing_executor = SlurmPipelineExecutor(
        job_name="cc_warc",
        pipeline=[
            WarcReader(
                data_folder="s3://",
                paths_file = warc_files_path,
                limit=limit,
            ),
            URLFilter(exclusion_writer=JsonlWriter(f"{FILTERING_OUTPUT_PATH}/removed/1_url")),
            Trafilatura(favour_precision=True, timeout=1),
            LanguageFilter(
                exclusion_writer=JsonlWriter(
                    f"{FILTERING_OUTPUT_PATH}/2_non_english/",
                    output_filename="${language}/" +  "/${rank}.jsonl.gz",
                )
            ),
            GopherRepetitionFilter(
                exclusion_writer=JsonlWriter(f"{FILTERING_OUTPUT_PATH}/removed/3_gopher_rep")
            ),
            GopherQualityFilter(
                exclusion_writer=JsonlWriter(f"{FILTERING_OUTPUT_PATH}/removed/4_gopher_qual")
            ),
            C4QualityFilter(
                filter_no_terminal_punct=False,
                exclusion_writer=JsonlWriter(f"{FILTERING_OUTPUT_PATH}/removed/5_c4"),
            ),
            FineWebQualityFilter(
                exclusion_writer=JsonlWriter(f"{FILTERING_OUTPUT_PATH}/removed/6_fineweb_qual")
            ),
            JsonlWriter(f"{FILTERING_OUTPUT_PATH}/output"),
        ],
        tasks=total_tasks,
        time="10:00:00",
        logging_dir=f"{MAIN_OUTPUT_PATH}/logs/base_processing",
        slurm_logs_folder="logs/base_processing/slurm_logs",
        randomize_start_duration=180,
        cpus_per_task=cpus_per_task,
        partition="hopper-cpu",
    )

    minhash_config = MinhashConfig(
        num_buckets=14,
        hashes_per_bucket=8,
        n_grams=5,
    )

    S3_MINHASH_BASE_PATH = f"{MAIN_OUTPUT_PATH}/minhash"
    S3_LOGS_FOLDER = f"{MAIN_OUTPUT_PATH}/logs/minhash"
    LOCAL_LOGS_FOLDER = "logs/minhash"

    INPUT_READER = JsonlReader(
        f"{FILTERING_OUTPUT_PATH}/output"
    )

    stage1 = SlurmPipelineExecutor(
        job_name="mh1_warc",
        pipeline=[
            INPUT_READER,
            MinhashDedupSignature(
                output_folder=f"{S3_MINHASH_BASE_PATH}/signatures", config=minhash_config
            ),
        ],
        tasks=total_tasks,
        time="5:00:00",
        partition="hopper-cpu",
        logging_dir=f"{S3_LOGS_FOLDER}/signatures",
        slurm_logs_folder=f"{LOCAL_LOGS_FOLDER}/signatures/slurm_logs",
        cpus_per_task=cpus_per_task,
        randomize_start_duration=180,
        depends=main_processing_executor,
    )

    stage2 = SlurmPipelineExecutor(
        job_name="mh2_warc",
        pipeline=[
            MinhashDedupBuckets(
                input_folder=f"{S3_MINHASH_BASE_PATH}/signatures",
                output_folder=f"{S3_MINHASH_BASE_PATH}/buckets",
                config=minhash_config,
            ),
        ],
        tasks=minhash_config.num_buckets * 2,
        randomize_start_duration=180,
        logging_dir=f"{S3_LOGS_FOLDER}/buckets",
        partition="hopper-cpu",
        time="02:00:00",
        mem_per_cpu_gb=4,
        cpus_per_task=cpus_per_task,
        depends=stage1,
    )

    stage3 = SlurmPipelineExecutor(
        job_name="mh3_warc",
        pipeline=[
            MinhashDedupCluster(
                input_folder=f"{S3_MINHASH_BASE_PATH}/buckets",
                output_folder=f"{S3_MINHASH_BASE_PATH}/remove_ids",
                config=minhash_config,
            ),
        ],
        tasks=1,
        logging_dir=f"{S3_LOGS_FOLDER}/clustering",
        partition="hopper-cpu",
        time="30:00:00",
        mem_per_cpu_gb=25,
        cpus_per_task=cpus_per_task,
        depends=stage2,
    )

    stage4 = SlurmPipelineExecutor(
        job_name="mh4_warc",
        pipeline=[
            INPUT_READER,
            TokensCounter(),
            MinhashDedupFilter(input_folder=f"{S3_MINHASH_BASE_PATH}/remove_ids"),
            PIIFormatter(),
            JsonlWriter(f"{S3_MINHASH_BASE_PATH}/deduped_output"),
        ],
        tasks=total_tasks,
        logging_dir=f"{S3_LOGS_FOLDER}/filtering",
        partition="hopper-cpu",
        time="5:00:00",
        cpus_per_task=cpus_per_task,
        mem_per_cpu_gb=4,
        depends=stage3,
    )

    # Launch deduplication pipeline
    stage4.run()

async def main(config: bt.config):
    """
    Main function to commit dataset to Bittensor subtensor chain.

    Args:
        config (bt.Config): Configuration object.
    """
    # Initialize logging
    bt.logging(config=config)

    # Initialize wallet and subtensor
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)

    # Retrieve the metagraph
    metagraph: bt.metagraph = subtensor.metagraph(config.netuid)

    # Ensure the wallet is registered
    hotkey, uid  = utils.assert_registered(wallet, metagraph)

    warc_files = fetch_warc_files(hotkey)
    
    proceed(warc_files, config.total_tasks, config.cpus_per_task, config.limit )

if __name__ == "__main__":

    load_dotenv()

    config = get_config()

    asyncio.run(main(config))
