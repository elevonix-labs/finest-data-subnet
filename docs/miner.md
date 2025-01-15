# Miners

We use [DataTrove](https://github.com/huggingface/datatrove), a lightweight yet powerful data refinement library, as the backbone of our **FineWeb τ** subnet. The miner is responsible for training the data refinement model and submitting it to Huggingface 🤗. You can refer to the training document from the DataTrove repo for the training guideline. We will also provide a detailed training setup here.

## System and Hardware Requirements

### 1. **Hardware Requirements**

#### Recommended Hardware

- **CPU**: As many as possible( 40-core processor or higher recommended)
- **RAM**: 128 GB or higher
- **Storage**: 256 GB free disk space for dataset storage and processing

### 2. **Software Requirements**

- **Operating System** (Ubuntu 22.04.04+ recommended)
- **Python Version** (Python 3.10 + recommended)
- **Poetry**: For managing project dependencies and running scripts. (Refer to the [Installation Guide](#installing-poetry))
- **Git**: Version control system for managing code repositories.

## Install Dependencies

### Installing Poetry

#### First, make sure you have Poetry installed. If not, install it using

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

### AWS Credentials

You will need to have AWS credentials in the following file:

```bash
~/.aws/credentials
```

```bash
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

### Installing Dependencies

Ensure you have the required dependencies installed. You can use the following command to install them:

```bash
cd miner
poetry install
```

## Making Datasets

### 1. Prepare the Environment

Ensure you have a Slurm-based HPC system for running the pipeline.
If you are not familiar with Slurm, please refer to [datatrove.md](datatrove.md).

### 2. Run the Pipeline

You can run the pipeline using the provided script. Here's an example command to execute the script:

```bash
poetry run python miner/main.py --hf_repo your_hf_repo --wallet.name your_wallet_name --wallet.hotkey your_wallet_hotkey [--total_tasks total_task] [--cpus_per_task your_cpus_number]
```

Example:

```bash
poetry run python miner/main.py --hf_repo barney49/original_data --wallet.name test-miner --wallet.hotkey h1 --total_tasks 4 --cpus_per_task 32 --subtensor.network test
```
