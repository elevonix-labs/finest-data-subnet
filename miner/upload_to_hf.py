import os
import argparse
from dotenv import load_dotenv
import dask.dataframe as dd
from dask.diagnostics import ProgressBar
from datasets import Dataset, DatasetDict
import logging
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HFTokenNotFoundError(Exception):
    """
    Exception raised when the Hugging Face token is not found in the environment variables.
    """
    def __init__(self, message="Hugging Face token not found in environment variables. Please set the HF_TOKEN in your environment."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'

class S3ReadError(Exception):
    """
    Exception raised for errors that occur while reading data from S3.
    """
    def __init__(self, message="An error occurred while reading data from S3. Please check the S3 path and try again."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'

class AWSCredentialsNotFoundError(Exception):
    """
    Exception raised when AWS credentials are not found in the environment variables.
    """
    def __init__(self, message="AWS credentials not found in environment variables. Please set the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your environment."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'

def upload_to_hf(hf_repo: str, bucket_name: str, data_url: str) -> None:
    """
    Uploads a dataset to Hugging Face from an S3 bucket.

    Args:
        hf_repo (str): Hugging Face repository to upload the dataset.
        bucket_name (str): S3 bucket name where the dataset is stored.
        data_url (str): Path of the dataset in the S3 bucket.

    Raises:
        HFTokenNotFoundError: If the Hugging Face token is not found in the environment variables.
        FileNotFoundError: If the specified S3 path does not exist.
        Exception: For any other exceptions during the process.
    """
    try:
        # Load environment variables from the .env file. Ensure HF_TOKEN is set in .env.
        load_dotenv()
        hf_token = os.getenv("HF_TOKEN")
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if not hf_token:
            raise HFTokenNotFoundError("Hugging Face token not found in environment variables.")
        if not aws_access_key_id or not aws_secret_access_key:
            raise AWSCredentialsNotFoundError("AWS credentials not found in environment variables.")
        
        logging.info("Hugging Face token and AWS credentials loaded successfully.")

        # Set up boto3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        # S3 path to the dataset
        s3_path = f's3://{bucket_name}/{data_url}'

        logging.info(f"Reading data from S3 path: {s3_path}")

        try:
            # Read JSON files from S3 bucket
            with ProgressBar():
                df = dd.read_json(s3_path, blocksize=None, compression='gzip')
            if df is None:
                raise S3ReadError("Error occurred while getting data from S3.")
            logging.info("Data read successfully from S3.")
        except Exception as e:
            logging.error(f"Error reading data from S3: {e}")
            raise
        # Compute the Dask DataFrame to get a Pandas DataFrame
        logging.info("Computing Dask DataFrame to Pandas DataFrame.")

        with ProgressBar():
            pandas_df = df.compute()

        logging.info("Dask DataFrame computed to Pandas DataFrame.")

        # Convert Pandas DataFrame to Hugging Face Dataset
        logging.info("Converting Pandas DataFrame to Hugging Face Dataset.")

        with ProgressBar():
            hf_dataset = Dataset.from_pandas(pandas_df)

        logging.info("Pandas DataFrame converted to Hugging Face Dataset.")

        # Create a DatasetDict
        dataset_dict = DatasetDict({"train": hf_dataset})

        logging.info(f"Uploading dataset to Hugging Face repository: {hf_repo}")
        dataset_dict.push_to_hub(hf_repo)
        logging.info(f"Dataset uploaded to Hugging Face repository: {hf_repo}")

        objects_to_delete = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=data_url)
        if 'Contents' in objects_to_delete:
            delete_keys = {'Objects': [{'Key': obj['Key']} for obj in objects_to_delete['Contents']]}
            s3_client.delete_objects(Bucket=bucket_name, Delete=delete_keys)
            logging.info(f"All objects removed from S3 path: {s3_path}")
        else:
            logging.info(f"No objects found at S3 path: {s3_path}")
    except HFTokenNotFoundError as e:
        logging.error(e)
    except AWSCredentialsNotFoundError as e:
        logging.error(e)
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
    except S3ReadError as e:
        logging.error(e)
    except NoCredentialsError as e:
        logging.error(f"AWS credentials error: {e}")
    except PartialCredentialsError as e:
        logging.error(f"Partial AWS credentials error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

def main(bucket_name: str, data_url: str, hf_repo: str) -> None:
    """
    Main function to upload dataset to Hugging Face.

    Args:
        bucket_name (str): S3 bucket name where the dataset is stored.
        data_url (str): Path of the dataset in the S3 bucket.
        hf_repo (str): Hugging Face repository to upload the dataset.
    """
    upload_to_hf(hf_repo, bucket_name, data_url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload dataset to Hugging Face from S3 bucket")
    parser.add_argument('--bucket_name', type=str, required=True, help='Name of the S3 bucket')
    parser.add_argument('--data_url', type=str, required=True, help='Path of the dataset in the S3 bucket')
    parser.add_argument('--hf_repo', type=str, required=True, help='Hugging Face repository to upload the dataset')

    args = parser.parse_args()

    main(bucket_name=args.bucket_name, data_url=args.data_url, hf_repo=args.hf_repo)
