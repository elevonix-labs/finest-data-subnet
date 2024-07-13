import os
from dotenv import load_dotenv
import dask.dataframe as dd
from dask.diagnostics import ProgressBar
from datasets import Dataset, DatasetDict
import logging

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

def upload_to_hf(hf_repo: str, bucket_name: str, dump_to_process: str) -> None:
    """
    Uploads a dataset to Hugging Face from an S3 bucket.

    Args:
        hf_repo (str): Hugging Face repository to upload the dataset.
        bucket_name (str): S3 bucket name where the dataset is stored.
        dump_to_process (str): Path of the dataset in the S3 bucket.

    Raises:
        HFTokenNotFoundError: If the Hugging Face token is not found in the environment variables.
        FileNotFoundError: If the specified S3 path does not exist.
        Exception: For any other exceptions during the process.
    """
    try:
        # Load environment variables from the .env file. Ensure HF_TOKEN is set in .env.
        load_dotenv()
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise HFTokenNotFoundError("Hugging Face token not found in environment variables.")
        
        logging.info("Hugging Face token loaded successfully.")

        # S3 path to the dataset
        s3_path = f's3://{bucket_name}/minhash/{dump_to_process}/deduped_output/**/*.jsonl.gz'

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

    except HFTokenNotFoundError as e:
        logging.error(e)
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
    except S3ReadError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

def main() -> None:
    """
    Main function to upload dataset to Hugging Face.
    """
    hf_repo = "barney49/test"  # Change this to the path of the file you want to upload
    bucket_name = "data-refine"  # Change this to your repository ID
    dump_to_process = "CC-MAIN-2023-50"  # Change this to the desired path in the repository

    upload_to_hf(hf_repo, bucket_name, dump_to_process)

if __name__ == "__main__":
    main()
