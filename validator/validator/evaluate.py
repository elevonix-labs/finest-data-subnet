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

def run_lighteval(world_size : int = 1):
    # Set the environment variable
    env = os.environ.copy()
    env["CUDA_DEVICE_MAX_CONNECTIONS"] = "1"
    env['MASTER_ADDR'] = os.environ.get('MASTER_ADDR', 'localhost')
    env['MASTER_PORT'] = str(find_free_port())  # Assign a dynamic port if MASTER_PORT is already in use
    env['WORLD_SIZE'] = str(world_size)
    env['RANK'] = str(os.environ.get('RANK', 0))
    
    command = [
        "poetry", "run", "lighteval", "nanotron",
        "--checkpoint-config-path", "validator/checkpoints/10/config.yaml",
        "--lighteval-override", "validator/template.yaml"
    ]
    
    # Use pty to create a pseudo-terminal
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(command, env=env, stdout=slave_fd, stderr=slave_fd, close_fds=True, text=True)

    try:
        while True:
            # Use select to wait for data to be ready
            rlist, _, _ = select.select([master_fd], [], [], 1.0)
            if rlist:
                output = os.read(master_fd, 1024).decode('utf-8')
                if output:
                    print(output, end='')

            if process.poll() is not None:
                print("Process completed.")
                break
    except OSError as e:
        print(f"Error reading output: {e}")
    finally:
        os.close(master_fd)
        os.close(slave_fd)

    try:
        return_code = process.wait(timeout=10)  # Wait with a timeout
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            return_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            return_code = process.wait()

    if return_code == 0:
        print("Command executed successfully")
    else:
        print(f"Command failed with return code {return_code}")

if __name__ == "__main__":
    run_lighteval()
