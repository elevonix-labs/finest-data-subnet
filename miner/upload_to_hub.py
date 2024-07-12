import dask.dataframe as dd
from datasets import Dataset, DatasetDict
import s3fs

BUCKET_NAME = 'datatrove-tmp'
DUMP_TO_PROCESS = 'CC-MAIN-2023-50'

# This is path for final result
s3_path = f's3://{BUCKET_NAME}/minhash/{DUMP_TO_PROCESS}/deduped_output/**/*.jsonl.gz'

fs = s3fs.S3FileSystem()

files = fs.glob(s3_path)

df = dd.read_json(s3_path, blocksize=None, compression='gzip')

pandas_df = df.compute()
s3_files = [f's3://{file}' for file in files]

hf_dataset = Dataset.from_pandas(pandas_df)

dataset_dict = DatasetDict({"train": hf_dataset})

dataset_dict.push_to_hub("barney49/test")
