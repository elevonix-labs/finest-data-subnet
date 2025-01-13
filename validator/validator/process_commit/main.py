import time
import redis
import json
import requests
import os
from utils import extract_commit
def process_commits(redis_queue: redis.Redis):
    """
    Async task to process commits from the queue.

    """

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
                response = requests.post(f"{os.getenv('API_URL')}/check-dataset/", json={"uid": int(uid)})
                print(response)
            else:
                print("No commit found")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(10)

if __name__ == "__main__":

    redis_queue = redis.Redis(host='localhost', port=6379, db=0)
    print("Starting process commits")
    # queue = Queue()
    process_commits(redis_queue)