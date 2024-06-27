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

### Install SLURM

Install SLURM on your system to manage and execute the pipeline.

```bash
apt update
apt install slurm-client
apt install slurmctld
apt install slurmd
```

### SLURM Configuration

Create and configure the SLURM configuration file `/etc/slurm/slurm.conf` with the following content:

```
ClusterName=my_cluster
ControlMachine=<ipaddress>.ptr
PartitionName=hopper-cpu Nodes=<ipaddress> Default=YES MaxTime=1-00:00:00 State=UP
NodeName=<ipaddress> CPUs=32 Sockets=1 CoresPerSocket=16 ThreadsPerCore=2 RealMemory=128000 State=UNKNOWN
```

**Note: You need to check your server specifications using the `lscpu` command.**

### Python Dependencies

Ensure you have Python 3.12 or higher installed. You can check your Python version with:

```bash
python3 --version
```

If necessary, install Python 3.12 or higher:

```bash
apt update
apt install python3.12 python3.12-venv python3.12-dev
```

Create a virtual environment and install the required Python packages. It's recommended to use a virtual environment.

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `requirements.txt` file with the necessary dependencies:

```
datatrove[all]
```

## Running the Script

After setting up the configurations and installing the required packages, you can run the script as follows:

```bash
python fineweb.py
```

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
