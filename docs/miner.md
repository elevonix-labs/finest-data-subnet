# Miner

We use DataTrove, a lightweight yet powerful data refinement library, as the backbone of our data-refine subnet. The miner is responsible for training the data refinement model and submitting it to Huggingface 🤗. You can refer to the training document from the DataTrove repo for the training guideline. We will also provide a detailed training setup here.

## Making Datasets

### 1. Install Dependencies
Ensure you have the required dependencies installed. You can use the following command to install them:
```bash
pip install -r requirements.txt
```

### 2. Prepare the Environment
Make sure you have access to an S3 bucket where the data is stored and where the outputs will be saved. Also, ensure you have a Slurm-based HPC system for running the pipeline.
If you are not familiar with Slurm, please refer to [datatrove.md](datatrove.md).
Also make sure you have a `.env` file in the same directory as your script with the following environment variables set:
```ini
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=your_aws_region
```
You can refer to .env.sample
### 3. Prepare the Dataset
The dataset should be stored in an S3 bucket. The data URL should point to the prefix where the WARC files are stored.
You can manage your data efficiently on our site [data-manage.cerebromesh.io](https://data-manage.cerebromesh.io).

### 4. Run the Pipeline
You can run the pipeline using the provided script. Here's an example command to execute the script:
```bash
python miner/main.py --bucket_name your_bucket_name --data_url your_data_url [--total_tasks total_task] [--cpus_per_task your_cpus_number] [--limit limit_per_task]
```
Example:
```bash
python miner/main.py --bucket_name data-refine --data_url split-data/1/warc --total_tasks 4 --cpus_per_task 32 --limit 100
```


## Uploading Dataset to Hugging Face
We have a script that uploads datasets from an S3 bucket to Hugging Face.

### Prepare the Environment
Make sure you have a `.env` file in the same directory as your script with the following environment variables set:
```ini
HF_TOKEN=your_huggingface_token
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
```
### Run the Script
You can run the script using the following command:

```bash
python miner/upload_to_hf.py --bucket_name your_bucket_name --data_url your_data_url --hf_repo your_hf_repo
```
Example:
```bash
python miner/upload_to_hf.py --bucket_name data-refine --data_url minhash/deduped_output --hf_repo cerebromesh/data-refine
```

## Committing Dataset to Bittensor Subtensor Chain
We have a script that commits datasets to the Bittensor subtensor chain.

### Prepare the Environment
Make sure you have the required Bittensor dependencies installed and properly configured.

### Run the Script
You can run the script using the following command:

```bash
python commit_dataset.py --netuid your_netuid --hf_url your_hf_url --wallet.name your_wallet_name --wallet.hotkey wallet_hotkey_name
```
Example:
```bash
python commit_dataset.py --netuid 1 --hf_url https://huggingface.co/gpt2 --wallet.name miner --wallet.hotkey default
```