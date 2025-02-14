import os
import requests
from miner.logger_config import logger

def fetch_warc_files(hotkey, message, signature):
    """Fetches warc file paths from the API."""
    try:
        api_url = os.getenv("API_URL")
        response = requests.post(
            f"{api_url}/subnets/get-task/",
            json={"hotkey": hotkey, "message": message, "signature": signature},
        )
        response.raise_for_status()  # Raise an error for bad responses
        warc_files = response.json().get(
            "warc_paths"
        )  # Assuming the API returns a JSON array of file paths
        return warc_files
    except requests.HTTPError as http_err:
        if response.status_code == 404:
            logger.error(f"{response.json().get('message', 'Unknown error')}")
        else:
            logger.error(f"HTTP error occurred: {http_err}")
        return []
    except requests.RequestException as req_err:
        logger.error(f"Error fetching WARC files: {str(req_err)}")
        return []


def send_finish_request(hotkey, message, signature, hf_repo):
    """Sends a finish request to the API."""
    try:
        api_url = os.getenv("API_URL")
        response = requests.post(
            f"{api_url}/subnets/finish-task/",
            json={
                "hotkey": hotkey,
                "message": message,
                "signature": signature,
                "hf_repo": hf_repo,
            },
        )
        response.raise_for_status()
        if response.status_code == 200:
            print(f"Finished task for hotkey: {hotkey}")
            return True
        else:
            print(f"Failed to finish task for hotkey: {hotkey}")
            return False
    except requests.HTTPError as http_err:
        if response.status_code == 404:
            print(f"{response.json().get('message', 'Unknown error')}")
        else:
            print(f"Error sending finish request: {str(http_err)}")
        return False
