import subprocess
import argparse
import os
from multiprocessing import Process
from dotenv import load_dotenv
import signal

# Gracefully handle termination signals
def terminate_processes(processes):
    for p in processes:
        if p.is_alive():
            p.terminate()
            p.join(timeout=5)  # Give some time to exit cleanly
            if p.is_alive():
                p.kill()  # Force kill if still running

def run_fetch_commits(args):
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


def run_report_score(args):
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


def run_process_commits(args):
    subprocess.run(
        [
            ".venv/bin/python",
            "main.py",
            "--world_size",
            str(args.world_size),
        ],
        check=True,
        cwd="process_commit",
    )


def run_weight_setter(args):
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
        parser = argparse.ArgumentParser(description="Run multiple processes with specified arguments.")
        parser.add_argument("--netuid", type=str, default="63", help="The unique identifier for the network")
        parser.add_argument("--wallet_name", type=str, required=True, help="The wallet name")
        parser.add_argument("--wallet_hotkey", type=str, required=True, help="The wallet hotkey")
        parser.add_argument("--subtensor_network", default="finney", type=str, help="The subtensor network")
        parser.add_argument("--world_size", type=int, default=1, help="The number of GPUs to use")

        args = parser.parse_args()

        # Create process objects
        fetch_process = Process(target=run_fetch_commits, args=(args,), daemon=True)
        process_process = Process(target=run_process_commits, args=(args,), daemon=True)
        weight_setter_process = Process(target=run_weight_setter, args=(args,), daemon=True)
        report_score_process = Process(target=run_report_score, args=(args,), daemon=True)

        processes = [fetch_process, process_process, weight_setter_process, report_score_process]

        # Start processes
        for p in processes:
            p.start()

        # Wait for processes to complete
        for p in processes:
            p.join()

    except KeyboardInterrupt:

        terminate_processes(processes)

        print("✅ All subprocesses terminated safely.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

        terminate_processes(processes)

        print("✅ All subprocesses terminated due to an error.")

    finally:
        terminate_processes(processes)


if __name__ == "__main__":

    load_dotenv()
    main()
