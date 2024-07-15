import boto3

# Initialize the S3 client
s3 = boto3.client('s3')

# Define source and destination buckets
source_bucket = 'commoncrawl'
source_prefix = 'crawl-data/CC-MAIN-2023-50/segments/1700679099281.67/warc'
destination_bucket = 'data-refine'
destination_prefix = 'split-data/1/warc/'

# List objects in the source bucket
response = s3.list_objects_v2(Bucket=source_bucket, Prefix=source_prefix)

# Get the first four files
files = [content['Key'] for content in response.get('Contents', [])[:4]]

# Copy the files to the destination bucket
for file in files:
    copy_source = {'Bucket': source_bucket, 'Key': file}
    destination_key = destination_prefix + file.split('/')[-1]
    s3.copy(copy_source, destination_bucket, destination_key)
    print(f"Copied {file} to {destination_bucket}/{destination_key}")

print("Copying completed.")