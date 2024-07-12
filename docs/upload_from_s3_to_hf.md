# S3 to Hugging Face Dataset Uploader

This project demonstrates how to read JSONL files from an S3 bucket, process them using Dask and Hugging Face's datasets library, and then upload the resulting dataset to the Hugging Face Hub.

## Features

- Read JSONL files from an S3 bucket.
- Process the files using Dask for efficient computation.
- Convert the processed data into a Hugging Face dataset.
- Upload the dataset to the Hugging Face Hub.

## Requirements

- `dask[dataframe]`
- `datasets`
- `s3fs`

Create a virtual environment and install the required Python packages. It's recommended to use a virtual environment.

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

Install the required libraries using pip:

```bash
pip install dask[dataframe] datasets s3fs
```

## Usage

1. Set up huggingface

```bash
pip install huggingface_hub
```
```bash
huggingface-cli login
```

It need access_token for huggingface. 
You can create token following this guide. [security_toekn](https://huggingface.co/docs/hub/en/security-tokens)

You can create a repository from the CLI (skip if you created a repo from the website)

```bash
huggingface-cli repo create repo_name --type {model, dataset, space}
```

2. Set up your S3 bucket and path details:

Make sure you have AWS configured with the necessary credentials. If not, please refer to [datatrove readme](https://github.com/cerebromesh-labs/data-refine-subnet/blob/main/docs/datatrove.md)
```python
BUCKET_NAME = 'hf-datatrove'
DUMP_TO_PROCESS = 'CC-MAIN-2024-10'
```

3. Define the S3 path for the final result:

```python
s3_path = f's3://{BUCKET_NAME}/minhash/{DUMP_TO_PROCESS}/deduped_output/**/*.jsonl.gz'
```

3. Use `s3fs` to interact with the S3 bucket and `dask` to read and process the JSONL files:

```python
import dask.dataframe as dd
from datasets import Dataset, DatasetDict
import s3fs

fs = s3fs.S3FileSystem()

files = fs.glob(s3_path)

df = dd.read_json(s3_path, blocksize=None, compression='gzip')

pandas_df = df.compute()
s3_files = [f's3://{file}' for file in files]
```

4. Convert the processed DataFrame to a Hugging Face dataset:

```python
hf_dataset = Dataset.from_pandas(pandas_df)
```

5. Create a dataset dictionary and push it to the Hugging Face Hub:

```python
dataset_dict = DatasetDict({"train": hf_dataset})

dataset_dict.push_to_hub("your-username/your-dataset-name")
```

Replace `your-username/your-dataset-name` with your Hugging Face username and the desired dataset name.

You can find sample code in [root directory](https://github.com/cerebromesh-labs/data-refine-subnet)
## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

- [Dask](https://dask.org/)
- [Hugging Face Datasets](https://huggingface.co/docs/datasets/)
- [s3fs](https://s3fs.readthedocs.io/en/latest/)