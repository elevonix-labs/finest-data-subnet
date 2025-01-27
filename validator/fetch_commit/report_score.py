import os
import time
import logging
import bittensor as bt
import redis
import json
import utils
import requests

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Outputs to the console
        logging.FileHandler('report_score.log', mode='w')  # Overwrites the log file each time
    ]
)

def report_score(config: bt.config, redis_queue: redis.Redis):
    """
    Async task to fetch commits and put them into the commit queue.

    Args:
        config (bt.config): Configuration object.
    """
    logging.info("Starting report_score")
    while True:
        try:
            result = redis_queue.blpop("report_score", timeout=1)
            if result:
                report_data = json.loads(result[1].decode())  
                task_id = report_data["task_id"]
                score = report_data["score"]
                wallet = bt.wallet(config=config)
                subtensor = bt.subtensor(config=config)
                metagraph: bt.metagraph = subtensor.metagraph(config.netuid)
                hotkey, _ = utils.assert_registered(wallet, metagraph)
                signature = utils.generate_signature(wallet, f"{task_id}")
                print(f"Report score for task_id: {score}")

                max_retries = 10
                retry_count = 0

                while retry_count < max_retries:
                    try:
                        response = requests.post(f"{os.getenv('API_URL')}/subnets/report-score/", 
                                                 json={
                                                     "hotkey": hotkey,
                                                     "task_id": task_id,
                                                     "score": score,
                                                     "signature": signature
                                                 })
                        response.raise_for_status()

                        if response.status_code == 200:
                            logging.info(f"Report submitted successfully for task_id: {task_id}")
                            break
                        else:
                            logging.error(f"Can't report score now, try again in 10 seconds: {response.status_code}", exc_info=True)
                            time.sleep(10)
                    except requests.HTTPError as http_err:
                        if http_err.response.status_code == 404:
                            logging.error(f"{response.json().get('message', 'Unknown error')}", exc_info=True)
                            time.sleep(10)
                        else:
                            logging.error(f"Can't report score now, try again in 10 seconds: {http_err}", exc_info=True)
                            time.sleep(10)
                    retry_count += 1 
                else:
                    logging.error("Max retries reached. Failed to submit report. Going to next task")    
        except Exception as e:
            logging.error(f"Can't report score now, try again in 10 seconds: {e}", exc_info=True)
            time.sleep(10)

if __name__ == "__main__":

    redis_queue = redis.Redis(host='localhost', port=6379, db=0)
    config = utils.get_config()
    report_score(config, redis_queue)
