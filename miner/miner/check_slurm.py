import subprocess
import time
import os

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


def wait_for_job_completion(job_id, check_interval=30):
    """
    Wait for a Slurm job to complete.

    Args:
        job_id (int): Slurm job ID.
        check_interval (int): Time interval (in seconds) to check the job status.
    """
    timeout = 8 * 60 * 60
    start_time = time.time()

    while True:
        status = check_slurm_job_status(job_id)
        print(f"Job {job_id} status: {status}")

        if status == "COMPLETED":
            print(f"Job {job_id} has completed.")
            return status
        elif status == "FAILED":
            print(f"Job {job_id} has failed.")
            return status
        elif time.time() - start_time > timeout:
            print(f"Job {job_id} did not complete within 1 day, aborting.")
            try:
                os.system("scancel -u $USER")
                print("All jobs have been cancelled.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to cancel jobs: {e}")
            return False
        # Wait for the next check
        time.sleep(check_interval)
