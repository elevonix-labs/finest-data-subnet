import time
import redis
import json
import requests
import os
import numpy as np
import logging
from utils import extract_commit
from check_similarity import DataProcessor
from config import generate_training_config
from train import start_training_and_kill
from evaluate import run_lighteval
from calculate import calculate_score

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Outputs to the console
        logging.FileHandler('commit_processing.log', mode='w')  # Logs to a file
    ],
)

def process_commits(redis_queue: redis.Redis):
    """
    Async task to process commits from the queue with logging.
    """
    redis_queue.delete("commit_queue")

    while True:
        try:
            result = redis_queue.blpop("commit_queue", timeout=1)
            if result:
                start_time = time.time()
                commit_data = json.loads(result[1].decode())  
                uid = commit_data['uid']
                current_commit = commit_data['current_commit']
                commit_block = commit_data['commit_block']
                logging.info(f"Processing commit {current_commit} for UID {uid}")

                hf_url = extract_commit(current_commit)
                logging.info(f"Extracted commit URL: {hf_url}")

                while True:
                    try:
                        response = requests.post(f"{os.getenv('API_URL')}/subnets/check-task/", json={"uid": int(uid)})
                        data = response.json()
                        warc_files = data.get('warc_files')
                        request_block = data.get('request_block')
                        break
                    except Exception as e:
                        logging.error(f"Error occurred: {e}", exc_info=True)
                        time.sleep(10)

                logging.info(f"Received API response, warc_files: {warc_files}, request_block: {request_block}")

                # Data processing
                data_processor = DataProcessor(warc_files, hf_url)
                sample_similarities = data_processor.run()
                logging.info(f"Data processing completed with {len(sample_similarities)} similarities found.")

                elapsed_time = (commit_block - request_block) * 12
                logging.info(f"Elapsed time between commit block and request block: {elapsed_time}")

                # Training phase
                training_start_time = time.time()
                if generate_training_config(hf_url):
                    training_success = start_training_and_kill('config.yaml', 1)
                    logging.info(f"Training success: {training_success}")
                    if training_success:
                        training_time = time.time() - training_start_time
                        logging.info(f"Training completed in {training_time:.2f} seconds")

                        # Evaluation phase
                        evaluation_start_time = time.time()
                        matches = run_lighteval(1)
                        evaluation_time = time.time() - evaluation_start_time
                        logging.info(f"Evaluation completed in {evaluation_time:.2f} seconds")

                        values, stderrs = zip(*[(float(match[1]), float(match[2])) for match in matches if match[0] == 'truthfulqa_mc2'])
                        if values and stderrs:
                            mean_value = np.mean(values)
                            mean_stderr = np.mean(stderrs)
                        else:
                            mean_value = 0.0
                            mean_stderr = 0.0
                        logging.info(f"Evaluation results: mean_value={mean_value}, mean_stderr={mean_stderr}, elapsed_time={elapsed_time}")

                        # Score calculation
                        score = calculate_score(elapsed_time, mean_value, mean_stderr, sample_similarities)
                        raw_score = redis_queue.hget("scores", uid)
                        current_score = json.loads(raw_score) if raw_score else 0
                        updated_score = current_score * 0.8 + score * 0.2
                        redis_queue.hset("scores", uid, json.dumps(updated_score))
                        logging.info(f"Updated score for UID {uid}: {updated_score}")
                logging.info(f"Total time taken: {time.time() - start_time}")
            else:
                logging.info("No commit found in the queue")
        except Exception as e:
            logging.error(f"Error occurred: {e}", exc_info=True)
        time.sleep(5)

if __name__ == "__main__":
    redis_queue = redis.Redis(host='localhost', port=6379, db=0)
    logging.info("Starting process commits")
    process_commits(redis_queue)
