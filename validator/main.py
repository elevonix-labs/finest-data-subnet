import subprocess
import argparse
from multiprocessing import Process
from dotenv import load_dotenv


# Handle termination signals gracefully
def terminate_processes(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)  # Allow some time for a clean exit
            if process.is_alive():
                process.kill()  # Forcefully terminate if still running


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

    if args.subtensor_chain_endpoint:
        command.extend(["--subtensor.chain_endpoint", args.subtensor_chain_endpoint])

    subprocess.run(command, check=True, cwd="fetch_commit")


def run_report_score(args):
    command = [
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
    ]

    if args.subtensor_chain_endpoint:
        command.extend(["--subtensor.chain_endpoint", args.subtensor_chain_endpoint])

    subprocess.run(command, check=True, cwd="fetch_commit")


def run_process_commits(args):
    command = [
        ".venv/bin/python",
        "main.py",
        "--world_size",
        str(args.world_size),
    ]

    subprocess.run(command, check=True, cwd="process_commit")


def run_weight_setter(args):
    command = [
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
    ]

    if args.subtensor_chain_endpoint:
        command.extend(["--subtensor.chain_endpoint", args.subtensor_chain_endpoint])

    subprocess.run(command, check=True, cwd="fetch_commit")


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Execute validator code with the provided arguments."
        )
        parser.add_argument(
            "--netuid",
            type=str,
            default="63",
            help="The unique identifier for the network",
        )
        parser.add_argument(
            "--wallet_name", type=str, required=True, help="The wallet name"
        )
        parser.add_argument(
            "--wallet_hotkey", type=str, required=True, help="The wallet hotkey"
        )
        parser.add_argument(
            "--subtensor_network",
            default="finney",
            type=str,
            help="The subtensor network",
        )
        parser.add_argument(
            "--subtensor_chain_endpoint",
            default="",
            type=str,
            help="The subtensor network endpoint",
        )
        parser.add_argument(
            "--world_size", type=int, default=1, help="The number of GPUs to utilize"
        )

        args = parser.parse_args()

        # Verify validity of the validator

        # Initialize process objects
        fetch_process = Process(target=run_fetch_commits, args=(args,), daemon=True)
        process_process = Process(target=run_process_commits, args=(args,), daemon=True)
        weight_setter_process = Process(
            target=run_weight_setter, args=(args,), daemon=True
        )
        report_score_process = Process(
            target=run_report_score, args=(args,), daemon=True
        )

        processes = [
            fetch_process,
            process_process,
            weight_setter_process,
            report_score_process,
        ]

        # Launch processes
        for process in processes:
            process.start()

        # Await process completion
        for process in processes:
            process.join()

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
