import os
import requests

def fetch_warc_files(hotkey):
    """Fetches warc file paths from the API."""
    try:
        api_url = os.getenv("API_URL")
        response = requests.post(f"{api_url}/subnets/get-task/",
                                 json={
                                     "hotkey": hotkey,
                                 })
        response.raise_for_status()  # Raise an error for bad responses
        warc_files = response.json().get('warc_paths')  # Assuming the API returns a JSON array of file paths
        return warc_files
    except requests.HTTPError as http_err:
        if response.status_code in [400, 404]:
            # Extract the 'detail' from the error response
            error_detail = response.json().get('detail', 'Unknown error')
            print(f"Error fetching WARC files: {error_detail}")
        else:
            print(f"HTTP error occurred: {http_err}")
        return []
    except requests.RequestException as req_err:
        print(f"Error fetching WARC files: {str(req_err)}")
        return []

def send_finish_request(hotkey):
    api_url = os.getenv("API_URL")
    response = requests.post(f"{api_url}/subnets/finish-task/", json={"hotkey": hotkey})
    response.raise_for_status()
    if response.status_code == 200:
        print(f"Finished task for hotkey: {hotkey}")
        return True
    else:
        print(f"Failed to finish task for hotkey: {hotkey}")
        return False
