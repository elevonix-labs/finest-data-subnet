import os
import re
import pty
import subprocess
import select
import socket
from contextlib import closing


def find_free_port() -> int:
    """
    Locate and return an available port number.

    Returns:
        int: An available port number.
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def run_lighteval(world_size: int = 1) -> list:
    """
    Execute the lighteval command and retrieve the results.

    Args:
        world_size (int): The number of processes, typically matching the number of GPUs.

    Returns:
        list: Extracted metrics, values, and stderr from the log output.
    """
    env = setup_environment(world_size)

    command = "bash -c 'source .venv/bin/activate && lighteval nanotron --checkpoint-config-path checkpoints/10/config.yaml --lighteval-override template.yaml'"

    log_output = run_process(command, env)

    if log_output:
        return parse_log_output(log_output)
    else:
        print("No log output captured.")
        return []


def setup_environment(world_size: int) -> dict:
    """
    Configure and return the environment variables for the process.

    Args:
        world_size (int): The number of processes, typically matching the number of GPUs.

    Returns:
        dict: Environment variables.
    """
    env = os.environ.copy()
    env["CUDA_DEVICE_MAX_CONNECTIONS"] = "1"
    env["MASTER_ADDR"] = os.environ.get("MASTER_ADDR", "localhost")
    env["MASTER_PORT"] = str(find_free_port())
    env["WORLD_SIZE"] = str(world_size)
    env["RANK"] = str(os.environ.get("RANK", 0))
    return env


def run_process(command: list, env: dict) -> str:
    """
    Execute the specified command and capture its output.

    Args:
        command (list): The command to execute.
        env (dict): The environment variables for the command.

    Returns:
        str: The captured log output.
    """
    master_fd, slave_fd = pty.openpty()
    process_commit_path = os.path.dirname(os.path.abspath(__file__))

    process = subprocess.Popen(
        command,
        env=env,
        shell=True,
        cwd=process_commit_path,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        text=True,
    )

    log_output = ""
    try:
        while True:
            rlist, _, _ = select.select([master_fd], [], [], 1.0)
            if rlist:
                output = os.read(master_fd, 1024).decode("utf-8")
                if output:
                    print(output, end="")  # Optionally print to console
                    log_output += output

            if process.poll() is not None:
                print("Process completed.")
                break
    except OSError as e:
        print(f"Error reading output: {e}")
    finally:
        os.close(master_fd)
        os.close(slave_fd)

    return_code = handle_process_termination(process)

    if return_code == 0:
        return log_output
    else:
        print(f"Command failed with return code {return_code}")
        return ""


def handle_process_termination(process: subprocess.Popen) -> int:
    """
    Manage the termination of a process and return its exit code.

    Args:
        process (subprocess.Popen): The process to terminate.

    Returns:
        int: The exit code of the process.
    """
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
    return return_code


def parse_log_output(log_output: str) -> list:
    """
    Extract relevant data from the log output.

    Args:
        log_output (str): The log output from the command.

    Returns:
        list: Extracted metrics, values, and stderr.
    """
    pattern = r"\|\s*(truthfulqa_mc2)\s*\|(\d\.\d{3,4})\|\s*±\s*\|(\d\.\d{3,4})\|"
    try:
        matches = re.findall(pattern, log_output)
        return matches
    except re.error as e:
        print(f"Error processing log output with regex: {e}")
        return []


if __name__ == "__main__":

    results = run_lighteval()

    print(f"Results: {results}")
