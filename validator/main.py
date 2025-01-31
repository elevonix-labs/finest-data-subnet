import subprocess
import argparse
from multiprocessing import Process
from dotenv import load_dotenv


def run_fetch_commits(args=None):
    # Run fetch_commits in the bittensor environment
    command = [
        ".venv/bin/python",
        "main.py",
        "--netuid",
        args.netuid,
        "--wallet.name",
        args.wallet_name,
        "--wallet.hotkey",
        args.wallet_hotkey,
        "--subtensor.network",
        args.subtensor_network,
    ]
    subprocess.run(command, check=True, cwd="fetch_commit")


def run_report_score(args=None):
    # Run report_score in the bittensor environment
    subprocess.run(
        [
            ".venv/bin/python",
            "report_score.py",
            "--netuid",
            args.netuid,
            "--wallet.name",
            args.wallet_name,
            "--wallet.hotkey",
            args.wallet_hotkey,
            "--subtensor.network",
            args.subtensor_network,
        ],
        check=True,
        cwd="fetch_commit",
    )


def run_process_commits(args=None):
    # Run process_commits in the nanotron environment
    subprocess.run(
        [
            ".venv/bin/python",
            "main.py",
            "--world_size",
            args.world_size,
        ],
        check=True,
        cwd="process_commit",
    )


def run_weight_setter(args=None):
    # Run weight_setter in the bittensor environment
    subprocess.run(
        [
            ".venv/bin/python",
            "weight_setter.py",
            "--netuid",
            args.netuid,
            "--wallet.name",
            args.wallet_name,
            "--wallet.hotkey",
            args.wallet_hotkey,
            "--subtensor.network",
            args.subtensor_network,
        ],
        check=True,
        cwd="fetch_commit",
    )


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Run fetch_commits with specified arguments."
        )
        parser.add_argument(
            "--netuid",
            type=int,
            default=63,
            help="The unique identifier for the network",
        )
        parser.add_argument("--wallet_name", type=str, help="The wallet name")
        parser.add_argument("--wallet_hotkey", type=str, help="The wallet hotkey")
        parser.add_argument(
            "--subtensor_network", type=str, help="The subtensor network"
        )
        parser.add_argument(
            "--world_size", type=str, default=1, help="The number of GPUs to use"
        )

        # Parse the arguments
        args = parser.parse_args()

        fetch_process = Process(target=run_fetch_commits, args=(args,))
        process_process = Process(target=run_process_commits, args=(args,))
        weight_setter_process = Process(target=run_weight_setter, args=(args,))
        report_score_process = Process(target=run_report_score, args=(args,))

        fetch_process.start()
        process_process.start()
        weight_setter_process.start()
        report_score_process.start()

        fetch_process.join()
        process_process.join()
        weight_setter_process.join()
        report_score_process.join()
    except KeyboardInterrupt:
        print("Process interrupted by user.")
        # Optionally, terminate the processes if needed
        fetch_process.terminate()
        process_process.terminate()
        weight_setter_process.terminate()
        report_score_process.terminate()


if __name__ == "__main__":

    load_dotenv()

    main()
