import time
import redis
import json
import requests
import os
from utils import extract_commit
from check_similarity import DataProcessor
from config import generate_training_config
from training import start_training_and_kill

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
                print(hf_url)
                response = requests.post(f"{os.getenv('API_URL')}/subnets/check-task/", json={"uid": int(uid)})
                data = response.json()
                warc_files = data.get('warc_files')
                request_block = data.get('request_block')
                data_processor = DataProcessor(warc_files, hf_url)
                sample_similarities = data_processor.run()
                if generate_training_config(hf_url):
                        training_success = start_training_and_kill('config.yaml', 1)
                        print(training_success)
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