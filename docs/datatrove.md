# FineWeb Dataset Processing Script

This repository contains the code used to process and create the FineWeb dataset. The dataset processing involves multiple stages including reading, filtering, deduplication, and writing the output to specified locations. Below are the steps and configurations required to run the script.

## Prerequisites

Before running the script, ensure you have the necessary packages and configurations set up.

### AWS Configuration

Make sure you have AWS configured with the necessary credentials. Update or create the following files:

#### `~/.aws/config`

```
[default]
region = us-west-2
output = json
```

#### `~/.aws/credentials`

```
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

### Install SLURMDBD and configuration

- Install Required Dependencies
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install mariadb-server
```
- Configure mariadb
```bash
sudo systemctl start mariadb
sudo systemctl enable mariadb
sudo mysql_secure_installation
```
- Create SLURM database and User
```bash
sudo mysql -u root -p

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
sudo systemctl status slurmdbd
```

### Install SLURM and configuration

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
```bash
sudo hostnamectl set-hostname <head>
```
```bash
sudo nano /etc/hosts
```
Add line for host `127.0.0.1 head`

- Configure slurm

```bash
sudo nano /etc/slurm/slurm.conf
```
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

```bash
sudo systemctl enable slurmd
sudo systemctl start slurmd
sudo systemctl enable slurmctld
sudo systemctl start slurmctld
```
If you change slurm conf in the future, you should reconfigure and restart slurmd
```bash
slurmd reconfigure
sudo systemctl restart slurmd
sudo systemctl restart slurmctld
```
```bash
scontrol update node=head state=RESUME
```

**Note: You need to check your server specifications using the `lscpu` command.**

### Python Dependencies

Ensure you have Python 3.12 or higher installed. You can check your Python version with:

```bash
python3 --version
```

If necessary, install Python 3.12 or higher:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y cmake build-essential libboost-all-dev
sudo apt install -y python3.12 python3.12-venv python3.12-dev

```

Create a virtual environment and install the required Python packages. It's recommended to use a virtual environment.

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install 'datatrove[all]'@git+https://github.com/huggingface/datatrove
```
You should download the resource manually by running the following python script in your Python environment:
```python
# punkt_download.py
import nltk
nltk.download('punkt')
```
```bash
python punkt_download.py
```

## Updating script

- Should remove `use_64bit_hashes` from MinhashConfig
- Also should modify tasks in each stage

## Running the Script

After setting up the configurations and installing the required packages, you can run the script as follows:

```bash
python fineweb.py
```
**NOTE: You can monitoring status using command `squeue` and `sacct`**

## Pipeline Description

The script processes data in multiple stages:

1. **Reading WARC files**: Reads WARC files from Common Crawl using the specified dump.
2. **Filtering**: Applies multiple filters including URL filtering, language filtering, and quality filtering.
3. **Deduplication**: Uses Minhash for deduplication in multiple stages:
   - Computing Minhash signatures
   - Creating Minhash buckets
   - Clustering for deduplication
   - Filtering duplicates
4. **Writing Output**: Writes the processed and deduplicated data to the specified S3 bucket.

### SLURM Jobs

The script uses SLURM to manage the execution of different stages of the pipeline. Each stage is defined as a separate SLURM job with dependencies to ensure correct execution order.

## Logging

The script logs the processing steps and outputs logs to the specified S3 bucket and local directories. Ensure you have the necessary permissions to write to the specified S3 bucket.

## Notes

- Modify the `DUMP_TO_PROCESS` variable to change the Common Crawl dump being processed.
- Adjust the SLURM configuration and resource allocation as per your cluster specifications and requirements.

By following the above steps and configurations, you should be able to process the FineWeb dataset successfully.
