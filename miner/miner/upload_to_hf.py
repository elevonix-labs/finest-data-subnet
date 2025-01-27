from huggingface_hub import delete_repo, HfApi
import os
import gzip
import json
import shutil
from datetime import datetime
from datasets import Dataset, DatasetDict

def read_datasets(dataset_path):
    all_datasets = []
    for file_name in os.listdir(dataset_path):
        if file_name.endswith('.jsonl.gz'):
            file_path = os.path.join(dataset_path, file_name)
            
            with gzip.open(file_path, 'rt') as f:
                dataset = [json.loads(line) for line in f]
                all_datasets.extend(dataset)  # Combine all datasets into a single list
    return all_datasets

def create_hf_dataset(data):
    hf_dataset = Dataset.from_list(data)
    dataset_dict = DatasetDict({'train': hf_dataset})
    return dataset_dict

def upload_to_hf(dataset_dict, repo_name, hf_token):
    """
    Upload dataset to Hugging Face.
    """
    try:
        dataset_dict.push_to_hub(repo_name, token=hf_token)
        print(f"Dataset successfully uploaded to Hugging Face: {repo_name}")
        return True
    except Exception as e:
        print(f"Failed to upload dataset: {e}")
        return False

def remove_result_folder(folder_path):
    shutil.rmtree(folder_path)
    print(f"Folder '{folder_path}' removed successfully.")

def upload_dataset(result_path, hf_repo):
    hf_token = os.getenv("HF_TOKEN")

    print("Reading datasets from local path...")
    all_datasets = read_datasets(f'{result_path}/minhash/deduped_output')

    print("Converting data to Hugging Face Dataset format...")
    dataset_dict = create_hf_dataset(all_datasets)

    print("Uploading dataset to Hugging Face...")

    current_timestamp = datetime.now()

    formatted_timestamp = current_timestamp.strftime("%Y_%m_%d_%H")

    repo_name= f"{hf_repo}_{formatted_timestamp}"

    if upload_to_hf(dataset_dict, repo_name, hf_token):

        remove_result_folder(result_path)

        return repo_name
    else:
        return False

if __name__ == "__main__":
    # Replace these with actual parameters or environment variables
    result_path = "./result"
    hf_repo = "barneylogo/prefix"
    result = upload_dataset(result_path, hf_repo)