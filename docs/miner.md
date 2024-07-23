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

### 3. Prepare the Dataset
The dataset should be stored in an S3 bucket. The data URL should point to the prefix where the WARC files are stored.
You can manage your data efficiently on our site [data-manage.cerebromesh.io](https://data-manage.cerebromesh.io).

### 4. Run the Pipeline
You can run the pipeline using the provided script. Here's an example command to execute the script:
```bash
python miner/pipeline_script.py --bucket_name your_bucket_name --data_url your_data_url [--total_tasks 4] [--cpus_per_task 32] [--limit 1000]
```

