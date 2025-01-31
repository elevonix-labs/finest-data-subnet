# Miners

We use [DataTrove](https://github.com/huggingface/datatrove), a lightweight yet powerful data refinement library, as the backbone of our **Finesτ Daτa** subnet. The miner is responsible for training the data refinement model and submitting it to Huggingface 🤗. You can refer to the training document from the DataTrove repo for the training guideline. We will also provide a detailed training setup here.

## Prerequisites

Before you go to miner, ensure you have the necessary packages and configurations set up.

## System and Hardware Requirements

### 1. **Hardware Requirements**

#### Recommended Hardware

- **CPU**: As many as possible( 40-core processor or higher recommended)
- **RAM**: 32 GB or higher
- **Storage**: 128 GB free disk space for dataset storage and processing

### 2. **Slurm Configuration**

**slurmdbd**, **slurmctld**, **slurmd**, **munge**

#### Install SLURMDBD and configuration

- Install Required Dependencies

If you didn't install sudo, you can use this command to install it
```bash
sudo apt install sudo
```

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install mariadb-server
```

- Configure mariadb

```bash
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

If you need to set up the root password and other security settings, please follow this [docs](https://mariadb.com/kb/en/mysql_secure_installation/).


- Create SLURM database and User

```bash
sudo mysql -u root -p
```
After that in mysql client, run below commands

```bash
CREATE DATABASE slurm_acct_db;
CREATE USER 'slurm'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON slurm_acct_db.* TO 'slurm'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

```bash
sudo apt install slurmdbd slurm-wlm
```

```bash
sudo nano /etc/slurm/slurmdbd.conf
```

Use below configuration for slurmdbd as a reference.

```ini
# slurmdbd.conf
DbdHost=localhost
DbdPort=6819
SlurmUser=root
StorageType=accounting_storage/mysql
StorageUser=slurm
StoragePass=password
StorageHost=localhost
StoragePort=3306
StorageLoc=slurm_acct_db
```

```bash
sudo chmod 600 /etc/slurm/slurmdbd.conf
sudo systemctl enable slurmdbd
sudo systemctl start slurmdbd
```

- Verify the slurmdbd installation

```bash
sudo service slurmdbd status
```

Refer to this image for more details.
![Slurmdbd Status](./docs/slurmdbd_status.png)

#### Install SLURM and configuration

- Install SLURM on your system to manage and execute the pipeline.

```bash
sudo apt update
sudo apt install slurm slurmd slurmctld slurm-client
```

- Configure munge

```bash
sudo apt install build-essential munge libmunge-dev libmunge2 libssl-dev

sudo dd if=/dev/urandom bs=1 count=1024 of=/etc/munge/munge.key
sudo chown munge:munge /etc/munge/munge.key
sudo chmod 400 /etc/munge/munge.key
sudo systemctl enable munge
sudo systemctl start munge
```

- Set hostname

1. if you can use hostnamectl, you will be able to use this command to set hostname

```bash
sudo hostnamectl set-hostname head
```
2. Or if you can't use hostnamectl, you can add it manually in /etc/hosts

```bash
sudo nano /etc/hosts
```
Add line for host `127.0.0.1 head`

If you haven't already updated the /etc/hostname file with the hostname head, you can do so:

```bash
sudo nano /etc/hostname
```



Make sure that the file contains just the hostname:

```bash
head
```
Plz use below command to check hostname
```bash
hostname
```

- Configure slurm

**Note: You need to check your server specifications using the `lscpu` and `free -m` command.**

For `RealMemory` input the total value of `free -m` command.
From `lscpu`, You can get the values `CPU(s):`, `Core(s) per socket:`, `Thread(s) per core`, `Socket(s):`,


```bash
sudo nano /etc/slurm/slurm.conf
```

Use below configuration as a reference. Update the values `CPU(s):`, `Core(s) per socket:`, `Thread(s) per core`, `Socket(s):`, `RealMemory` with your server specifications.
```ini
# slurm.conf
ClusterName=my_cluster
ControlMachine=head

#ACCOUNTING
JobAcctGatherType=jobacct_gather/linux
AccountingStorageType=accounting_storage/slurmdbd
AccountingStorageHost=127.0.0.1

AuthType=auth/munge
ProctrackType=proctrack/linuxproc

# Nodes Configuration
NodeName=head CPUs=32 Sockets=1 CoresPerSocket=16 ThreadsPerCore=2 RealMemory=10000 State=UNKNOWN

# Partitions Configuration
PartitionName=hopper-cpu Nodes=head Default=YES MaxTime=INFINITE State=UP OverSubscribe=Force
```

### Explanation of Parameters:

- **CPUs**: The total number of logical CPUs (or threads) available on the node. More CPUs allow for more parallel processing, which can speed up data processing tasks. This is particularly beneficial for tasks that can be parallelized, such as data preprocessing, model training, or simulations. Faster processing can lead to quicker iterations and potentially higher data quality as more complex models or larger datasets can be handled efficiently.

- **Sockets**: The number of physical CPU sockets. While this doesn't directly affect performance, it indicates the physical layout of the CPUs. A single socket with multiple cores can be efficient for tasks that require high inter-core communication.

- **CoresPerSocket**: The number of physical cores per socket. More cores mean more tasks can be executed simultaneously, improving throughput and reducing the time required for data processing. This can enhance data quality by allowing more comprehensive data checks or more complex models to be run within a given time frame.

- **ThreadsPerCore**: This indicates hyper-threading, where each core can handle two threads. Hyper-threading can improve performance for multi-threaded applications by better utilizing CPU resources, leading to faster data processing and potentially better data quality through more thorough analysis.


- **RealMemory**: The amount of RAM available on the node, measured in megabytes. Sufficient memory is crucial for handling large datasets and complex computations. Insufficient memory can lead to swapping (using disk space as virtual memory), which significantly slows down processing and can degrade data quality if processes are terminated prematurely due to memory constraints.


### Usage

This configuration is crucial for SLURM to effectively manage and allocate resources across the cluster. It ensures that jobs are scheduled on nodes with the appropriate hardware capabilities, optimizing performance and resource utilization.

For more detailed information on configuring SLURM nodes, refer to the [SLURM documentation](https://slurm.schedmd.com/slurm.conf.html).


```bash
sudo chmod 600 /etc/slurm/slurm.conf
sudo systemctl enable slurmd
sudo systemctl start slurmd
sudo systemctl enable slurmctld
sudo systemctl start slurmctld
```

```bash
sudo apt update
sudo apt install slurm-client
```

Check slurm using `scontrol show nodes`
If state of node is drained or downed, run  `scontrol update node=head state=RESUME`

Also if you change slurm conf in the future, you should reconfigure and restart slurmd

```bash
slurmd reconfigure
sudo systemctl restart slurmd
sudo systemctl restart slurmctld
```

### 3. **Software Requirements**

- **Operating System** (Ubuntu 22.04.04+ recommended)
- **Python Version** (Python 3.10 + recommended)
- **Poetry**: For managing project dependencies and running scripts. (Refer to the [Installation Guide](#installing-poetry))
- **Git**: Version control system for managing code repositories.


## Install Dependencies

### Python Dependencies

Ensure you have Python 3.10. You can check your Python version with:

```bash
python3 --version

sudo apt update
sudo apt install -y cmake build-essential libboost-all-dev

```

### Installing Poetry

#### First, make sure you have Poetry installed. If not, install it using

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

This installation script should automatically add Poetry to your PATH. If the installation was successful, try running:

```bash
poetry --version
```
If you can't find poetry, you can add Poetry to Your PATH Manually

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

### Getting code

```bash
git clone https://github.com/elevonix-labs/finest-data-subnet.git
```


### AWS Credentials

You will need to have AWS config and credentials in the following file:

~/.aws/config

```bash
[default]
region = us-east-1
output = json
```

~/.aws/credentials

```bash
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

Or you can add it in .env file
Plz check .env.sample file for more details.

### Huggingface Token

You will need to have a Huggingface token to push the dataset to Huggingface. You can get it from [here](https://huggingface.co/settings/tokens).
You can add it in .env file. Plz check .env.sample file for more details.
```bash
HF_TOKEN=YOUR_HUGGINGFACE_TOKEN
```
Or you can set it using huggingface-cli.
```bash
huggingface-cli login
```

### Adding .env file

```bash
cp .env.sample .env
```

### Adding API_URL

You need to add API_URL in .env file.

```bash
API_URL=https://finest-data-api.elevonix.io/api
```

### Installing Dependencies

Ensure you have the required dependencies installed. You can use the following command to install them:

```bash
cd miner
poetry install
```

### Creating Bittensor wallet.

You can active poetry venv for creating wallet.

```bash
source .venv/bin/activate
```

- Creating a coldkey using `btcli`

`btcli wallet new_coldkey --wallet.name <my_coldkey>`
For example,
`btcli wallet new_coldkey --wallet.name test-coldkey`

- Creating a hotkey using `btcli`

`btcli wallet new_hotkey --wallet.name <my_coldkey> --wallet.hotkey <my_hotkey>`
For example,
`btcli wallet new_hotkey --wallet.name test-coldkey --wallet.hotkey test-hotkey`

You can check more about it in [bittensor docs](https://docs.bittensor.com/working-with-keys)


## Running miner

You can run the pipeline using the provided script. Here's an example command to execute the script:

- Mainnet
```bash
poetry run python miner/main.py --hf_repo your_hf_repo --wallet.name your_wallet_name --wallet.hotkey your_wallet_hotkey [--total_tasks total_task] [--cpus_per_task your_cpus_number]
```
Example:
```bash
poetry run python miner/main.py --hf_repo tobiashomie/finest_dataset --wallet.name miner --wallet.hotkey h1 --total_tasks 4 --cpus_per_task 32
```
Or run with pm2
```bash
pm2 start miner/main.py --name miner --interpreter .venv/bin/python -- --hf_repo tobiashomie/finest_dataset --wallet.name miner --wallet.hotkey h1 --total_tasks 4 --cpus_per_task 32
```



- Testnet
```bash
poetry run python miner/main.py --netuid 250 --subtensor.network test --hf_repo your_hf_repo --wallet.name your_wallet_name --wallet.hotkey your_wallet_hotkey [--total_tasks total_task] [--cpus_per_task your_cpus_number]
```
Example:
```bash
poetry run python miner/main.py --netuid 250 --subtensor.network test --hf_repo tobiashomie/finest_dataset --wallet.name test-miner --wallet.hotkey h1 --total_tasks 4 --cpus_per_task 32
```
Or run with pm2
```bash
pm2 start miner/main.py --name test-miner --interpreter .venv/bin/python -- --netuid 250 --subtensor.network test --hf_repo tobiashomie/finest_dataset --wallet.name test-miner --wallet.hotkey h1 --total_tasks 4 --cpus_per_task 32
```

**Explanation of the arguments:**
- **--netuid**, **--subtensor_network, **--wallet_name**, **--wallet_hotkey****: These arguments are used to specify the wallet name, hotkey, bittensor network. Please check (bittensor docs)[https://docs.bittensor.com/] for more details.
- **--total_tasks**: This argument sets the total number of tasks to be processed. It can reflect distribute tasks across resources.
- **--cpus_per_task**: This argument sets the number of CPUs per task. This is likely used to allocate CPU resources for each task

