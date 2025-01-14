import time
import redis
import json
import requests
import os
import numpy as np
from utils import extract_commit
from check_similarity import DataProcessor
from config import generate_training_config
from train import start_training_and_kill
from evaluate import run_lighteval
from calculate import calculate_score

def process_commits(redis_queue: redis.Redis):
    """
    Async task to process commits from the queue.

    """
    redis_queue.delete("commit_queue")

    while True:
        try:
            result = redis_queue.blpop("commit_queue", timeout=1)
            if result:
                commit_data = json.loads(result[1].decode())  
                uid = commit_data['uid']
                current_commit = commit_data['current_commit']
                commit_block = commit_data['commit_block']
                hf_url = extract_commit(current_commit)
                response = requests.post(f"{os.getenv('API_URL')}/subnets/check-task/", json={"uid": int(uid)})
                data = response.json()
                warc_files = data.get('warc_files')
                request_block = data.get('request_block')
                data_processor = DataProcessor(warc_files, hf_url)
                sample_similarities = data_processor.run()
                elapsed_time = (commit_block - request_block) * 12
                if generate_training_config(hf_url):
                    training_success = start_training_and_kill('config.yaml', 1)
                    print(training_success)
                    if training_success:
                        matches = run_lighteval(1)
                        values, stderrs = zip(*[(float(match[1]), float(match[2])) for match in matches if match[0] == 'truthfulqa_mc2'])
                        if values and stderrs:
                            mean_value = np.mean(values)
                            mean_stderr = np.mean(stderrs)
                        else:
                            mean_value = 0.0
                            mean_stderr = 0.0
                        print(mean_value, mean_stderr, elapsed_time)
                        score = calculate_score(elapsed_time, mean_value, mean_stderr, sample_similarities)
                        raw_score = redis_queue.hget("scores", uid)
                        current_score = json.loads(raw_score) if raw_score else 0
                        updated_score = current_score * 0.8 + score * 0.2
                        redis_queue.hset("scores", uid, json.dumps(updated_score))
            else:
                print("No commit found")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(100)

if __name__ == "__main__":

    redis_queue = redis.Redis(host='localhost', port=6379, db=0)
    print("Starting process commits")
    # queue = Queue()
    process_commits(redis_queue)