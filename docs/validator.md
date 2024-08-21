# Validator

This script is designed to commit datasets to the Bittensor subtensor chain. It initializes and parses command-line arguments, sets up the wallet and subtensor, and retrieves and processes datasets from the Bittensor metagraph.

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
#### Add Poetry to Your PATH Manually
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
cd validator
poetry install
poetry run pip install flash-attn
```
You need to install specific packages, such as `flash-attn` using the following command:
```bash
poetry run pip install flash-attn
```
## Getting Commit

### 1. Prepare the Environment

Make sure you have the necessary environment setup. You should have a Bittensor wallet and access to the Bittensor subtensor chain.

### 2. Configuration

The script uses command-line arguments for configuration. The main arguments include:
```ini
HF_TOKEN=
```
### 3. Running the Script

You can run the script using the following command:

```bash
poetry run python validator/main.py --netuid your_netuid --wallet.name your_wallet --wallet.hotkey your_wallet_hotkey
```
Example
```bash
poetry run python validator/main.py --netuid 1 --wallet.name validator --wallet.hotkey default
```

## Traning and Evaluating

### 1. Getting model config

```bash
poetry run python validator/config.py --hf-url your_hf_url
```
Example
```bash
poetry run python validator/config.py --hf-url barney49/data-refine
```

### 2. Training model

```bash
CUDA_DEVICE_MAX_CONNECTIONS=1 poetry run torchrun --nproc_per_node=1 validator/train.py --config-file your_config_file
```
Example
```bash
CUDA_DEVICE_MAX_CONNECTIONS=1 poetry run torchrun --nproc_per_node=1 validator/train.py --config-file validator/config.yaml
```

### 3. Evaluating model

```bash
export MASTER_ADDR=localhost
export MASTER_PORT=29500
export WORLD_SIZE=1
export RANK=0
```

```bash
CUDA_DEVICE_MAX_CONNECTIONS=1 poetry run lighteval nanotron --checkpoint-config-path validator/checkpoints/10/config.yaml --lighteval-override validator/template.yaml
```