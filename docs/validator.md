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
```
You need to install specific packages, such as `flash-attn` using the following command:
```bash
poetry run pip install flash-attn
```
## Getting Commit

### 1. Prepare the Environment

Make sure you have the necessary environment setup. You should have a Bittensor wallet and access to the Bittensor subtensor chain.

### 2. Running the Script

You can run the script using the following command:

```bash
poetry run python validator/main.py --netuid netuid --wallet.name your_wallet_name --wallet.hotkey wallet_hotkey --subtensor.network test [--world_size gpu_count]
```
Example
```bash
poetry run python validator/main.py --netuid 204 --wallet.name validator1 --wallet.hotkey validator1 --subtensor.network test
```