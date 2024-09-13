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

from miner.check_slurm import wait_for_job_completion

def refining(warc_files, result_path, total_tasks, cpus_per_task, limit):
    """Main function to execute the data processing and deduplication pipeline."""
    
    filtering_output_path = f"{result_path}/base_processing"

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
            URLFilter(exclusion_writer=JsonlWriter(f"{filtering_output_path}/removed/1_url")),
            Trafilatura(favour_precision=True, timeout=1),
            LanguageFilter(
                exclusion_writer=JsonlWriter(
                    f"{filtering_output_path}/2_non_english/",
                    output_filename="${language}/" +  "/${rank}.jsonl.gz",
                )
            ),
            GopherRepetitionFilter(
                exclusion_writer=JsonlWriter(f"{filtering_output_path}/removed/3_gopher_rep")
            ),
            GopherQualityFilter(
                exclusion_writer=JsonlWriter(f"{filtering_output_path}/removed/4_gopher_qual")
            ),
            C4QualityFilter(
                filter_no_terminal_punct=False,
                exclusion_writer=JsonlWriter(f"{filtering_output_path}/removed/5_c4"),
            ),
            FineWebQualityFilter(
                exclusion_writer=JsonlWriter(f"{filtering_output_path}/removed/6_fineweb_qual")
            ),
            JsonlWriter(f"{filtering_output_path}/output"),
        ],
        tasks=total_tasks,
        time="10:00:00",
        logging_dir=f"{result_path}/logs/base_processing",
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

    S3_MINHASH_BASE_PATH = f"{result_path}/minhash"
    S3_LOGS_FOLDER = f"{result_path}/logs/minhash"
    LOCAL_LOGS_FOLDER = "logs/minhash"

    INPUT_READER = JsonlReader(
        f"{filtering_output_path}/output"
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
    final_status = wait_for_job_completion(stage4.job_id)


    # Trigger actions based on the status
    if final_status == 'COMPLETED':

        return True
        # Add your post-processing logic here
    elif final_status == 'FAILED':
        print("Job failed, aborting post-processing.")
        # Add your error handling logic here
    else:
        print("Unhandled job status:", final_status)