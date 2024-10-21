# FineWeb Dataset Processing Script

This repository contains the code used to process and create the FineWeb dataset. The dataset processing involves multiple stages including reading, filtering, deduplication, and writing the output to specified locations. Below are the steps and configurations required to run the script.

## Prerequisites

Before running the script, ensure you have the necessary packages and configurations set up.

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
sudo hostnamectl set-hostname head
```
```bash
sudo nano /etc/hosts
```
Add line for host `127.0.0.1 head`

- Configure slurm

```bash
sudo nano /etc/slurm/slurm.conf
```
**Note: You need to check your server specifications using the `lscpu` and `free -m` command.**


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
For `RealMemory` input the total value of `free -m` command.
From `lscpu`, You can get the values `CPU(s):`, `Core(s) per socket:`, ` Thread(s) per core`, `Socket(s):`
```bash
sudo systemctl enable slurmd
sudo systemctl start slurmd
sudo systemctl enable slurmctld
sudo systemctl start slurmctld
```
```bash
sudo apt update
sudo apt install slurm-client
```
Check slurm using `scontol show nodes`
If state of node is drained or downed, run  `scontrol update node=head state=RESUME`

Also if you change slurm conf in the future, you should reconfigure and restart slurmd
```bash
slurmd reconfigure
sudo systemctl restart slurmd
sudo systemctl restart slurmctld
```


### Python Dependencies

Ensure you have Python 3.10. You can check your Python version with:

```bash
python3 --version

sudo apt update
sudo apt install -y cmake build-essential libboost-all-dev
sudo apt install python3 python3.10-venv
```

## Running the Script

After setting up the configurations and installing the required packages, you can run fineweb.py script in miner as follows:

### Usage
To run the script, use the following command:

```bash
poetry run python miner/fineweb.py --bucket_name BUCKET_NAME --data_url DATA_URL [--total_tasks TOTAL_TASKS] [--cpus_per_task CPUS_PER_TASK] [--limit LIMIT]

```
### Arguments

Arguments
--bucket_name: Name of the S3 bucket where the data is stored and processed.
--data_url: Destination prefix in the S3 bucket where the WARC files are located.
--total_tasks (optional): Total number of tasks to run. Default is 4.
--cpus_per_task (optional): Number of CPUs per task. Default is 32.
--limit (optional): Number of limit in WarcReader. Default is None.

**NOTE: You can monitoring status using command `squeue` and `sacct`**

## Pipeline Description

The script processes data in multiple stages:

1. **Reading WARC files**: Reads WARC files from sub_data using the specified dump.
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
