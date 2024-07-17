import argparse
from datatrove.executor.slurm import SlurmPipelineExecutor
from datatrove.executor.local import LocalPipelineExecutor
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

def main(bucket_name, data_url, total_tasks=4, cpus_per_task=32):
    MAIN_OUTPUT_PATH = f"s3://{bucket_name}"
    FILTERING_OUTPUT_PATH = f"{MAIN_OUTPUT_PATH}/base_processing"

    main_processing_executor = SlurmPipelineExecutor(
        job_name=f"cc_warc",
        pipeline=[
            WarcReader(
                f"s3://{bucket_name}/{data_url}",
                glob_pattern="*.warc.gz",  # we want the warc files
            ),
            URLFilter(exclusion_writer=JsonlWriter(f"{FILTERING_OUTPUT_PATH}/removed/1_url")),
            Trafilatura(favour_precision=True, timeout=1),
            LanguageFilter(
                exclusion_writer=JsonlWriter(
                    f"{FILTERING_OUTPUT_PATH}/2_non_english/",
                    output_filename="${language}/" +  "/${rank}.jsonl.gz",
                    # folder structure: language/dump/file
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
        slurm_logs_folder=f"logs/base_processing/slurm_logs",  # must be local
        randomize_start_duration=180,  # don't hit the bucket all at once with the list requests
        cpus_per_task=cpus_per_task,
        partition="hopper-cpu",
    )

    # you can also change ngrams or the number of buckets and their size here
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

    # stage 1 computes minhash signatures for each task (each task gets a set of files)
    stage1 = SlurmPipelineExecutor(
        job_name=f"mh1_warc",
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
        depends=main_processing_executor,  # only start after the first one completes
    )

    stage2 = SlurmPipelineExecutor(
        job_name=f"mh2_warc",
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
        job_name=f"mh3_warc",
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
        job_name=f"mh4_warc",
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

    # launch dedup pipelines
    stage4.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run data processing and deduplication pipeline")
    parser.add_argument('--bucket_name', type=str, required=True, help='Name of the S3 bucket')
    parser.add_argument('--data_url', type=str, required=True, help='Destination prefix in the S3 bucket')
    parser.add_argument('--total_tasks', type=int, default=4, help='Total number of tasks')
    parser.add_argument('--cpus_per_task', type=int, default=32, help='Number of CPUs per task')

    args = parser.parse_args()

    main(
        bucket_name=args.bucket_name,
        data_url=args.data_url,
        total_tasks=args.total_tasks,
        cpus_per_task=args.cpus_per_task,
    )
