import re
import csv
import os
import pty
import subprocess
import select
import socket
from contextlib import closing

def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def run_lighteval(world_size: int = 1):
    env = os.environ.copy()
    env["CUDA_DEVICE_MAX_CONNECTIONS"] = "1"
    env['MASTER_ADDR'] = os.environ.get('MASTER_ADDR', 'localhost')
    env['MASTER_PORT'] = str(find_free_port())
    env['WORLD_SIZE'] = str(world_size)
    env['RANK'] = str(os.environ.get('RANK', 0))
    
    command = [
        "poetry", "run", "lighteval", "nanotron",
        "--checkpoint-config-path", "validator/checkpoints/10/config.yaml",
        "--lighteval-override", "validator/template.yaml",
    ]
    
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(command, env=env, stdout=slave_fd, stderr=slave_fd, close_fds=True, text=True)

    log_output = ""
    try:
        while True:
            rlist, _, _ = select.select([master_fd], [], [], 1.0)
            if rlist:
                output = os.read(master_fd, 1024).decode('utf-8')
                if output:
                    print(output, end='')  # Optionally print to console
                    log_output += output

            if process.poll() is not None:
                print("Process completed.")
                break
    except OSError as e:
        print(f"Error reading output: {e}")
    finally:
        os.close(master_fd)
        os.close(slave_fd)

    try:
        return_code = process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print("Process timeout; terminating...")
        process.terminate()
        try:
            return_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Process failed to terminate; killing...")
            process.kill()
            return_code = process.wait()

    if return_code == 0:
        try:
            result = get_result(log_output)
            print("Command executed successfully")
            return result
        except Exception as e:
            print(f"Error processing log output: {e}")
            return []
    else:
        print(f"Command failed with return code {return_code}")
        return []


def get_result(log_output: str) -> list:
    """
    Extract relevant information from the log output.

    Args:
        log_output (str): The log output from the command.

    Returns:
        list: Extracted metrics, values, and stderr.
    """
    pattern = r"\|\s*(truthfulqa_mc\d)\s*\|(\d\.\d{3,4})\|\±\s*\|(\d\.\d{3,4})"

    try:
        matches = re.findall(pattern, log_output)
        return matches
    except re.error as e:
        print(f"Error processing log output with regex: {e}")
        return []

if __name__ == "__main__":
    run_lighteval()
