import boto3
from itertools import islice
DUMP_TO_PROCESS = "CC-MAIN-2023-50" 
# Configuration
bucket_name = "commoncrawl"
prefix = f"crawl-data/{DUMP_TO_PROCESS}/segments/"
subset_size = 100  # Number of files per subset

# Initialize S3 client
s3 = boto3.client('s3')

# List all files in the S3 bucket
def list_s3_files(bucket, prefix):
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    for page in pages:
        for obj in page.get('Contents', []):
            yield obj['Key']

# Split files into smaller subsets
def split_list(iterable, size):
    iterable = iter(iterable)
    return iter(lambda: list(islice(iterable, size)), [])

# Get all files and split into subsets
all_files = list_s3_files(bucket_name, prefix)
subsets = list(split_list(all_files, subset_size))

# Print subsets for verification
for i, subset in enumerate(subsets):
    print(f"Subset {i+1}: {len(subset)} files")





