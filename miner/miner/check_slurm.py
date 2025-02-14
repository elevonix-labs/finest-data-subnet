import subprocess
import time
import os
from miner.logger_config import logger

def terminate_slurm_jobs():
    """
    Function to terminate all running SLURM jobs.
    """
    try:
        # Assuming you have a command to cancel all SLURM jobs
        os.system("scancel -u $USER")
        logger.info("All SLURM jobs have been terminated.")
    except Exception as e:
        logger.error(f"Failed to terminate SLURM jobs: {e}")


def check_slurm_job_status(job_id):
    """
    Check the status of a Slurm job using the job ID.

    Args:
        job_id (int): Slurm job ID.

    Returns:
        str: Status of the job ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', etc.)
    """
    try:
        # Run the `sacct` command to get the job status
        result = subprocess.run(
            ["sacct", "-j", str(job_id), "--format=State", "--noheader"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Check if the command was successful
        if result.returncode != 0:
            print(f"Error checking job status: {result.stderr.strip()}")
            return "UNKNOWN"

        # Get the status from the command output
        job_status = (
            result.stdout.strip().split()[0] if result.stdout.strip() else "UNKNOWN"
        )
        return job_status

    except Exception as e:
        print(f"Error checking job status: {e}")
        return "UNKNOWN"


def wait_for_job_completion(job_id, check_interval=30, timeout=24 * 60 * 60):
    """
    Wait for a Slurm job to complete.

    Args:
        job_id (int): Slurm job ID.
        check_interval (int): Time interval (in seconds) to check the job status.
        timeout (int): Time to wait for the job to complete (in seconds).
    """
    start_time = time.time()

    while True:
        status = check_slurm_job_status(job_id)
        print(f"Job {job_id} status: {status}")

        if status == "COMPLETED":
            logger.info(f"Job {job_id} has completed.")
            return status
        elif status == "FAILED":
            logger.error(f"Job {job_id} has failed.")
            return status
        elif time.time() - start_time > timeout:
            logger.error(f"Job {job_id} did not complete within 1 day, aborting.")
            terminate_slurm_jobs()
            logger.info("All jobs have been cancelled.")
            return False
        # Wait for the next check
        time.sleep(check_interval)
