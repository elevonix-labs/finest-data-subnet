import os
import requests

def fetch_warc_files(hotkey):
    """Fetches warc file paths from the API."""
    try:
        api_url = os.getenv("API_URL")
        response = requests.post(f"{api_url}/get-task/",
                                 json={
                                     "hotkey": hotkey,
                                 })
        response.raise_for_status()  # Raise an error for bad responses
        warc_files = response.json().get('warc_paths')  # Assuming the API returns a JSON array of file paths
        return warc_files
    except requests.RequestException as e:
        print(f"Error fetching WARC files: {e}")
        return []