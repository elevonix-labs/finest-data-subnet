"""Data Processing and Deduplication Pipeline Script.

This script processes data from a given S3 bucket, applies several filters,
and performs deduplication using Minhash.

Usage:
    python main.py --bucket_name <S3 bucket name> --data_url <data URL> --total_tasks <number of tasks> --cpus_per_task <number of CPUs per task> --limit <optional limit>

Example:
    python main.py --bucket_name my-bucket --data_url data/ --total_tasks 4 --cpus_per_task 32 --limit 1000
"""

import argparse
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

def main(bucket_name, data_url, total_tasks=4, cpus_per_task=32, limit=None):
    """Main function to execute the data processing and deduplication pipeline."""
    
    MAIN_OUTPUT_PATH = f"s3://{bucket_name}"
    FILTERING_OUTPUT_PATH = f"{MAIN_OUTPUT_PATH}/base_processing"

    # Initial processing executor
    main_processing_executor = SlurmPipelineExecutor(
        job_name="cc_warc",
        pipeline=[
            WarcReader(
                f"s3://{bucket_name}/{data_url}",
                glob_pattern="*.warc.gz",
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run data processing and deduplication pipeline")
    parser.add_argument('--bucket_name', type=str, required=True, help='Name of the S3 bucket')
    parser.add_argument('--data_url', type=str, required=True, help='Destination prefix in the S3 bucket')
    parser.add_argument('--total_tasks', type=int, default=4, help='Total number of tasks')
    parser.add_argument('--cpus_per_task', type=int, default=32, help='Number of CPUs per task')
    parser.add_argument('--limit', type=int, default=None, help='Number of records to process in WarcReader')

    args = parser.parse_args()

    main(
        bucket_name=args.bucket_name,
        data_url=args.data_url,
        total_tasks=args.total_tasks,
        cpus_per_task=args.cpus_per_task,
        limit=args.limit,
    )