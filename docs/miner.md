# Miners

We use [DataTrove](https://github.com/huggingface/datatrove), a lightweight yet powerful data refinement library, as the backbone of our data-refine subnet. The miner is responsible for training the data refinement model and submitting it to Huggingface 🤗. You can refer to the training document from the DataTrove repo for the training guideline. We will also provide a detailed training setup here.

## Install Dependencies

### Installing Poetry
#### First, make sure you have Poetry installed. If not, install it using:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```
This installation script should automatically add Poetry to your PATH. If the installation was successful, try running:
```bash
poetry --version
```
#### Or you can add Poetry to Your PATH Manually
- First, locate the Poetry binary:
```bash
echo "$HOME/.local/bin/poetry"
```
- Add the Poetry binary directory to your PATH by editing your shell configuration file `nano ~/.bashrc`, `~/.zshrc`, or `~/.profile`
```bash
export PATH="$HOME/.local/bin:$PATH"
```
- After adding it to your PATH, apply the changes:
```bash
source ~/.bashrc
```
Now, you should be able to run:
```bash
poetry --version
```

### Installing Dependencies

Ensure you have the required dependencies installed. You can use the following command to install them:
```bash
cd miner
poetry install
```
## Making Datasets

### 1. Prepare the Environment
Make sure you have access to an S3 bucket where the data is stored and where the outputs will be saved. Also, ensure you have a Slurm-based HPC system for running the pipeline.
If you are not familiar with Slurm, please refer to [datatrove.md](datatrove.md).
Also make sure you have a `.env` file in the same directory as your script with the following environment variables set:
```ini
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=your_aws_region
```
You can refer to .env.sample
### 2. Prepare the Dataset
The dataset should be stored in an S3 bucket. The data URL should point to the prefix where the WARC files are stored.
You can manage your data efficiently on our site [data-manage.cerebromesh.io](https://data-manage.cerebromesh.io).

### 3. Run the Pipeline
You can run the pipeline using the provided script. Here's an example command to execute the script:
```bash
poetry run python miner/main.py --hf_repo your_hf_repo --wallet.name your_wallet_name --wallet.hotkey your_wallet_hotkey [--total_tasks total_task] [--cpus_per_task your_cpus_number] [--limit limit_per_task]
```
Example:
```bash
poetry run python miner/main.py --hf_repo barney49/original_data --wallet.name miner1 --wallet.hotkey miner1 --total_tasks 4 --cpus_per_task 32 --limit 100
```