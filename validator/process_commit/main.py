import time
import redis
import json
import requests
import os
import numpy as np
import logging
import argparse
from utils import extract_commit
from check_similarity import DataProcessor
from config import generate_training_config
from train import start_training_and_kill
from evaluate import run_lighteval
from calculate import calculate_score

from colorama import init, Fore

# Initialize colorama
init(autoreset=True)


# Custom logging formatter to add colors and emojis
class ColoredFormatter(logging.Formatter):
    COLORS = {
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    def format(self, record):
        log_level = record.levelname
        color = self.COLORS.get(log_level, Fore.WHITE)
        message = super().format(record)
        return f"{color} {message}"


# Configure logging with color logging for console output
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Outputs to the console
        logging.FileHandler("commit_processing.log", mode="w"),  # Logs to a file
    ],
)

logger = logging.getLogger()

console_handler = logging.StreamHandler()
console_handler.setFormatter(
    ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.handlers[0] = (
    console_handler  # Replace the default stream handler with our colored one
)


def get_world_size():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--world_size", type=int, default=1, help="The number of GPUs to use"
    )
    args = parser.parse_args()
    return args.world_size


def process_commits(redis_queue: redis.Redis, world_size: int):
    """
    Async task to process commits from the queue with logging.
    """
    redis_queue.delete("commit_queue")
    redis_queue.delete("report_score")
    redis_queue.delete("scores")

    while True:
        try:
            result = redis_queue.blpop("commit_queue", timeout=1)
            if result:
                start_time = time.time()
                commit_data = json.loads(result[1].decode())
                uid = commit_data["uid"]
                current_commit = commit_data["current_commit"]
                commit_block = commit_data["commit_block"]
                logging.info(f"Processing commit {current_commit} for UID {uid}")

                max_retries = 5
                retry_count = 0
                warc_files = None
                request_block = None
                while retry_count < max_retries:
                    try:
                        response = requests.post(
                            f"{os.getenv('API_URL')}/subnets/check-task/",
                            json={"uid": int(uid)},
                        )
                        if response.status_code == 200:
                            data = response.json()
                            task_id = data.get("task_id")
                            warc_files = data.get("warc_files")
                            request_block = data.get("request_block")
                            break
                        elif response.status_code == 404:
                            break
                        else:
                            logging.error(
                                f"Can't get warc files now, trying again in 10 seconds {response.status_code}",
                                exc_info=True,
                            )
                            time.sleep(10)
                            retry_count += 1
                    except Exception as e:
                        logging.error(
                            f"Can't get warc files now, trying again in 10 seconds {e}",
                            exc_info=True,
                        )
                        time.sleep(10)
                        retry_count += 1

                if not warc_files or not request_block:
                    logging.error(
                        f"Cannot find the latest task record of Miner-{uid}, skipping this commit..."
                    )
                    continue

                logging.info(
                    f"Received API response, warc_files: {warc_files}, request_block: {request_block}"
                )

                # Data processing
                logging.info("Starting check similarity process")
                data_processor = DataProcessor(warc_files, current_commit)

                sample_similarities = data_processor.run()

                logging.info(
                    f"Data processing completed with {len(sample_similarities)} similarities found. 📊"
                )

                elapsed_time = (commit_block - request_block) * 12
                # Training phase
                if generate_training_config(current_commit):
                    training_success = start_training_and_kill(
                        "config.yaml", world_size
                    )
                    logging.info(f"Training success: {training_success}")
                    if training_success:
                        # Evaluation phase
                        matches = run_lighteval(world_size)

                        values, stderrs = zip(
                            *[
                                (float(match[1]), float(match[2]))
                                for match in matches
                                if match[0] == "truthfulqa_mc2"
                            ]
                        )
                        if values and stderrs:
                            mean_value = np.mean(values)
                            mean_stderr = np.mean(stderrs)
                        else:
                            mean_value = 0.0
                            mean_stderr = 0.0

                        # Score calculation
                        score = calculate_score(
                            elapsed_time, mean_value, mean_stderr, sample_similarities
                        )
                        raw_score = redis_queue.hget("scores", uid)
                        current_score = json.loads(raw_score) if raw_score else 0
                        report_data = {"task_id": task_id, "score": score}
                        logging.info(f"Previous Score: {current_score}")
                        logging.info(f"New Score: {score}")
                        logging.info(f"Calculated score for UID {uid}: {score}")
                        updated_score = current_score * 0.8 + score * 0.2
                        redis_queue.rpush("report_score", json.dumps(report_data))
                        redis_queue.hset("scores", int(uid), json.dumps(updated_score))
                logging.info(f"Total time taken: {time.time() - start_time}")
            else:
                print(f"No commit data found in commit queue...")
                time.sleep(10)
        except Exception as e:
            logging.warning(f"Can't process commit now, try again in 10 seconds {e}")
            time.sleep(10)


if __name__ == "__main__":

    redis_queue = redis.Redis(host="localhost", port=6379, db=0)
    logging.info("Starting process commits 🚀")
    world_size = get_world_size()
    process_commits(redis_queue, world_size)
