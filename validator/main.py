import subprocess
import argparse
from multiprocessing import Process

def run_fetch_commits(args=None):
    # Run fetch_commits in the bittensor environment
    command = ['.venv/bin/python', 'main.py',
               '--netuid', args.netuid,
               '--wallet.name', args.wallet_name,
               '--wallet.hotkey', args.wallet_hotkey,
               '--subtensor.network', args.subtensor_network
               ]
    subprocess.run(command, check=True, cwd='fetch_commit')

def run_process_commits(args=None):
    # Run process_commits in the nanotron environment
    subprocess.run([
        '.venv/bin/python', 'main.py'
    ], check=True, cwd='process_commit')

def main():
    parser = argparse.ArgumentParser(description="Run fetch_commits with specified arguments.")
    parser.add_argument('--netuid', type=str,  help="The unique identifier for the network")
    parser.add_argument('--wallet_name', type=str,  help="The wallet name")
    parser.add_argument('--wallet_hotkey', type=str,  help="The wallet hotkey")
    parser.add_argument('--subtensor_network', type=str, help="The subtensor network")

    # Parse the arguments
    args = parser.parse_args()

    # fetch_process = Process(target=run_fetch_commits, args=(args,))
    process_process = Process(target=run_process_commits, args=(args,))

    # fetch_process.start()
    process_process.start()

    # fetch_process.join()
    process_process.join()

if __name__ == "__main__":

    main()