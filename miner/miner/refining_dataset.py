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
from s3fs import S3FileSystem
from datatrove.io import DataFolder
from miner.check_slurm import wait_for_job_completion

class DataRefiner:
    def __init__(self, warc_files, result_path, total_tasks, cpus_per_task, limit):
        self.warc_files = warc_files
        self.result_path = result_path
        self.total_tasks = total_tasks
        self.cpus_per_task = cpus_per_task
        self.limit = limit
        self.filtering_output_path = f"{result_path}/base_processing"
        self.minhash_config = MinhashConfig(
            
            num_buckets=14,
            hashes_per_bucket=8,
            n_grams=5,
        )
        self.s3_minhash_base_path = f"{result_path}/minhash"
        self.s3_logs_folder = f"{result_path}/logs/minhash"
        self.local_logs_folder = "logs/minhash"

    def _create_warc_files_path(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            for path in self.warc_files:
                temp_file.write(f"{path}\n")
            return temp_file.name

    def _create_main_processing_executor(self, warc_files_path):
        return SlurmPipelineExecutor(
            job_name="cc_warc",
            pipeline=[
                WarcReader(
                    data_folder=DataFolder(
                        path="s3://commoncrawl",
                        fs=S3FileSystem(
                            client_kwargs={
                                "region_name": "us-east-1"
                            }
                        )
                    ),
                    paths_file=warc_files_path,
                    file_progress=True,
                    doc_progress=True,
                    limit=self.limit,
                ),
                URLFilter(exclusion_writer=JsonlWriter(f"{self.filtering_output_path}/removed/1_url")),
                Trafilatura(favour_precision=True, timeout=1),
                LanguageFilter(
                    exclusion_writer=JsonlWriter(
                        f"{self.filtering_output_path}/2_non_english/",
                        output_filename="${language}/" + "/${rank}.jsonl.gz",
                    )
                ),
                GopherRepetitionFilter(
                    exclusion_writer=JsonlWriter(f"{self.filtering_output_path}/removed/3_gopher_rep")
                ),
                GopherQualityFilter(
                    exclusion_writer=JsonlWriter(f"{self.filtering_output_path}/removed/4_gopher_qual")
                ),
                C4QualityFilter(
                    filter_no_terminal_punct=False,
                    exclusion_writer=JsonlWriter(f"{self.filtering_output_path}/removed/5_c4"),
                ),
                FineWebQualityFilter(
                    exclusion_writer=JsonlWriter(f"{self.filtering_output_path}/removed/6_fineweb_qual")
                ),
                JsonlWriter(f"{self.filtering_output_path}/output"),
            ],
            tasks=self.total_tasks,
            time="10:00:00",
            logging_dir=f"{self.result_path}/logs/base_processing",
            slurm_logs_folder="logs/base_processing/slurm_logs",
            randomize_start_duration=180,
            cpus_per_task=self.cpus_per_task,
            partition="hopper-cpu",
        )

    def _create_deduplication_stages(self, main_processing_executor):
        input_reader = JsonlReader(f"{self.filtering_output_path}/output")

        stage1 = SlurmPipelineExecutor(
            job_name="mh1_warc",
            pipeline=[
                input_reader,
                MinhashDedupSignature(
                    output_folder=f"{self.s3_minhash_base_path}/signatures",
                    config=self.minhash_config
                ),
            ],
            tasks=self.total_tasks,
            time="5:00:00",
            partition="hopper-cpu",
            logging_dir=f"{self.s3_logs_folder}/signatures",
            slurm_logs_folder=f"{self.local_logs_folder}/signatures/slurm_logs",
            cpus_per_task=self.cpus_per_task,
            randomize_start_duration=180,
            depends=main_processing_executor,
        )

        stage2 = SlurmPipelineExecutor(
            job_name="mh2_warc",
            pipeline=[
                MinhashDedupBuckets(
                    input_folder=f"{self.s3_minhash_base_path}/signatures",
                    output_folder=f"{self.s3_minhash_base_path}/buckets",
                    config=self.minhash_config,
                ),
            ],
            tasks=self.minhash_config.num_buckets,
            randomize_start_duration=180,
            logging_dir=f"{self.s3_logs_folder}/buckets",
            partition="hopper-cpu",
            time="02:00:00",
            mem_per_cpu_gb=4,
            cpus_per_task=self.cpus_per_task,
            depends=stage1,
        )

        stage3 = SlurmPipelineExecutor(
            job_name="mh3_warc",
            pipeline=[
                MinhashDedupCluster(
                    input_folder=f"{self.s3_minhash_base_path}/buckets",
                    output_folder=f"{self.s3_minhash_base_path}/remove_ids",
                    config=self.minhash_config,
                ),
            ],
            tasks=1,
            logging_dir=f"{self.s3_logs_folder}/clustering",
            partition="hopper-cpu",
            time="30:00:00",
            mem_per_cpu_gb=25,
            cpus_per_task=self.cpus_per_task,
            depends=stage2,
        )

        stage4 = SlurmPipelineExecutor(
            job_name="mh4_warc",
            pipeline=[
                input_reader,
                TokensCounter(),
                MinhashDedupFilter(input_folder=f"{self.s3_minhash_base_path}/remove_ids"),
                PIIFormatter(),
                JsonlWriter(f"{self.s3_minhash_base_path}/deduped_output"),
            ],
            tasks=self.total_tasks,
            logging_dir=f"{self.s3_logs_folder}/filtering",
            partition="hopper-cpu",
            time="5:00:00",
            cpus_per_task=self.cpus_per_task,
            mem_per_cpu_gb=4,
            depends=stage3,
        )

        return stage4

    def refine(self):
        """Main method to execute the data processing and deduplication pipeline."""
        # print(self.warc_files, self.total_tasks, self.cpus_per_task, self.limit)
        
        if not self.warc_files:
            print("No WARC files fetched from API. Exiting.")
            return False

        warc_files_path = self._create_warc_files_path()
        print(warc_files_path)
        main_processing_executor = self._create_main_processing_executor(warc_files_path)
        stage4 = self._create_deduplication_stages(main_processing_executor)

        # Launch deduplication pipeline
        stage4.run()
        final_status = wait_for_job_completion(stage4.job_id)

        if final_status == 'COMPLETED':
            return True
        elif final_status == 'FAILED':
            print("Job failed, aborting post-processing.")
            return False
        else:
            print("Unhandled job status:", final_status)
            return False

if __name__ == "__main__":
    warc_files = ['crawl-data/CC-MAIN-2024-42/segments/1727944253654.26/warc/CC-MAIN-20241009211335-20241010001335-00661.warc.gz', 'crawl-data/CC-MAIN-2024-42/segments/1727944253824.62/warc/CC-MAIN-20241011164904-20241011194904-00184.warc.gz', 'crawl-data/CC-MAIN-2024-42/segments/1727944253951.2/warc/CC-MAIN-20241012082236-20241012112236-00328.warc.gz', 'crawl-data/CC-MAIN-2024-42/segments/1727944255020.72/warc/CC-MAIN-20241012235949-20241013025949-00027.warc.gz']
    result_path = "./result"
    total_tasks = 4
    cpus_per_task = 20
    limit = 10
    refiner = DataRefiner(warc_files, result_path, total_tasks, cpus_per_task, limit)
    refiner.refine()