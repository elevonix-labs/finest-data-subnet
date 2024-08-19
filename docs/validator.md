# Validator

This script is designed to commit datasets to the Bittensor subtensor chain. It initializes and parses command-line arguments, sets up the wallet and subtensor, and retrieves and processes datasets from the Bittensor metagraph.

## Getting Commit

### 1. Install Dependencies

Ensure you have the required dependencies installed. You can use the following command to install them:

```bash
pip install -r requirements.txt
```

### 2. Prepare the Environment

Make sure you have the necessary environment setup. You should have a Bittensor wallet and access to the Bittensor subtensor chain.

### 3. Configuration

The script uses command-line arguments for configuration. The main arguments include:
```ini
HF_TOKEN=
```
### 4. Running the Script

You can run the script using the following command:

```bash
python validator/main.py --netuid your_netuid --wallet.name your_wallet --wallet.hotkey your_wallet_hotkey
```
Example
```bash
python validator/main.py --netuid 1 --wallet.name validator --wallet.hotkey default
```

## Traning and Evaluating

### 1. Install Dependencies

Ensure you have the required dependencies installed. You can use the following command to install them:

```bash
pip install -r validator/requirements.txt
pip install --upgrade pip
```

### 2. Getting model config

```bash
python validator/config.py --hf-url your_hf_url
```
Example
```bash
python validator/config.py --hf-url barney49/data-refine
```

### 3. Training model

```bash
CUDA_DEVICE_MAX_CONNECTIONS=1 torchrun --nproc_per_node=1 validator/train.py --config-file your_config_file
```
Example
```bash
CUDA_DEVICE_MAX_CONNECTIONS=1 torchrun --nproc_per_node=1 validator/train.py --config-file validator/config.yaml
```

### 4. Evaluating model

```bash
export MASTER_ADDR=localhost
export MASTER_PORT=29500
export WORLD_SIZE=1
export RANK=0
```

```bash
lighteval nanotron --checkpoint-config-path validator/checkpoints/10/config.yaml --lighteval-override validator/template.yaml
```