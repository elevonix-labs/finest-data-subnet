import sys
import os
import bittensor as bt
import asyncio
import traceback
import time
import argparse
from dotenv import load_dotenv
import dask.dataframe as dd
from dask.diagnostics import ProgressBar
from datasets import Dataset, DatasetDict
import logging
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from utilities import utils

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HFTokenNotFoundError(Exception):
    """Exception raised when the Hugging Face token is not found in the environment variables."""
    def __init__(self, message="Hugging Face token not found in environment variables. Please set the HF_TOKEN in your environment."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'

class S3ReadError(Exception):
    """Exception raised for errors that occur while reading data from S3."""
    def __init__(self, message="An error occurred while reading data from S3. Please check the S3 path and try again."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'

class AWSCredentialsNotFoundError(Exception):
    """Exception raised when AWS credentials are not found in the environment variables."""
    def __init__(self, message="AWS credentials not found in environment variables. Please set the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your environment."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'

def upload_to_hf(hf_repo: str, bucket_name: str, data_url: str) -> bool:
    """
    Uploads a dataset to Hugging Face from an S3 bucket.

    Args:
        hf_repo (str): Hugging Face repository to upload the dataset.
        bucket_name (str): S3 bucket name where the dataset is stored.
        data_url (str): Path of the dataset in the S3 bucket.

    Returns:
        bool: True if the upload was successful, False otherwise.

    Raises:
        HFTokenNotFoundError: If the Hugging Face token is not found in the environment variables.
        AWSCredentialsNotFoundError: If AWS credentials are not found in the environment variables.
        S3ReadError: If there is an error reading data from S3.
        NoCredentialsError: If AWS credentials are incorrect or missing.
        PartialCredentialsError: If some AWS credentials are missing.
    """
    try:
        # Load environment variables from the .env file
        load_dotenv()
        hf_token = os.getenv("HF_TOKEN")
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not hf_token:
            raise HFTokenNotFoundError()
        if not aws_access_key_id or not aws_secret_access_key:
            raise AWSCredentialsNotFoundError()

        logging.info("Hugging Face token and AWS credentials loaded successfully.")

        # Set up boto3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        # S3 path to the dataset
        s3_path = f's3://{bucket_name}/{data_url}/**/*.jsonl.gz'
        logging.info(f"Reading data from S3 path: {s3_path}")

        try:
            # Read JSON files from S3 bucket
            with ProgressBar():
                df = dd.read_json(s3_path, blocksize=None, compression='gzip')
            if df is None:
                raise S3ReadError()
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

        # Delete objects from S3
        objects_to_delete = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=data_url)
        if 'Contents' in objects_to_delete:
            delete_keys = {'Objects': [{'Key': obj['Key']} for obj in objects_to_delete['Contents']]}
            s3_client.delete_objects(Bucket=bucket_name, Delete=delete_keys)
            logging.info(f"All objects removed from S3 path: {s3_path}")
        else:
            logging.info(f"No objects found at S3 path: {s3_path}")

        return True
    except HFTokenNotFoundError as e:
        logging.error(e)
    except AWSCredentialsNotFoundError as e:
        logging.error(e)
    except S3ReadError as e:
        logging.error(e)
    except NoCredentialsError as e:
        logging.error(f"AWS credentials error: {e}")
    except PartialCredentialsError as e:
        logging.error(f"Partial AWS credentials error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    return False

def get_config() -> bt.config:
    """
    Initialize and parse command-line arguments and add Bittensor-specific arguments.

    Returns:
        bt.Config: Parsed configuration.
    """
    parser = argparse.ArgumentParser(description="Upload dataset to Hugging Face and commit dataset URL to Bittensor subtensor chain.")
    parser.add_argument("--netuid", type=str, default="204", help="The unique identifier for the network.")
    parser.add_argument("--hf_repo", type=str,  help="The Hugging Face repository to upload the dataset.")
    parser.add_argument('--bucket_name', type=str,  help='Name of the S3 bucket.')
    parser.add_argument('--data_url', type=str, help='Path of the dataset in the S3 bucket.')

    # Add Bittensor-specific arguments
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config

async def main(config: bt.config):
    """
    Main function to commit dataset to Bittensor subtensor chain.

    Args:
        config (bt.Config): Configuration object.
    """
    # Initialize logging
    bt.logging(config=config)

    # Initialize wallet and subtensor
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)

    # Retrieve the metagraph
    metagraph: bt.metagraph = subtensor.metagraph(config.netuid)

    # Ensure the wallet is registered
    utils.assert_registered(wallet, metagraph)

    # Generate a unique hash for the dataset
    hf_url_hash = utils.get_hash_of_two_strings(config.hf_repo, wallet.hotkey.ss58_address)

    # Loop to commit dataset to the subtensor chain, with retry on failure
    while True:
        try:
            subtensor.commit(wallet, config.netuid, f"{hf_url_hash}:{config.hf_repo}")
            bt.logging.success("🎉 Successfully committed dataset to subtensor chain")
            break
        except Exception as e:
            traceback.print_exc()
            bt.logging.error(f"Error while committing to subtensor chain: {e}, retrying in 300 seconds...")
            time.sleep(300)

if __name__ == "__main__":
    # Parse and print configuration
    config = get_config()

    # if upload_to_hf(config.hf_repo, config.bucket_name, config.data_url):
        # Run the main function asynchronously
    asyncio.run(main(config))
