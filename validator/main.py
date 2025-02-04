import subprocess
import argparse
from multiprocessing import Process
from dotenv import load_dotenv
import psutil


def terminate_process(process):
    if process.is_alive():
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in children:
                child.terminate()
            process.terminate()
            process.join(timeout=15)

            for child in children:
                if child.is_running():
                    child.kill()

            if process.is_alive():
                process.kill()
        except psutil.NoSuchProcess:
            print(f"Process {process.pid} no longer exists.")

        print(f"✅ {process.name} (PID: {process.pid}) terminated successfully.")


def terminate_processes(processes):
    for process in processes:
        terminate_process(process)


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

    try:
        subprocess.run(command, check=True, cwd="fetch_commit")
    except subprocess.CalledProcessError as e:
        print(f"Error in fetch_commits: {e}")
        raise


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

    try:
        subprocess.run(command, check=True, cwd="fetch_commit")
    except subprocess.CalledProcessError as e:
        print(f"Error in report_score: {e}")
        raise


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

    try:
        subprocess.run(command, check=True, cwd="fetch_commit")
    except subprocess.CalledProcessError as e:
        print(f"Error in weight_setter: {e}")
        raise


def main():
    processes = []
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

        # # Monitor processes
        while True:
            for process in processes:
                if not process.is_alive():
                    print(
                        f"❌ {process.name} (PID: {process.pid}) terminated unexpectedly.\n🙊 Terminating other processes..."
                    )
                    terminate_processes(processes)
                    return

            if process.exitcode:
                raise RuntimeError(
                    f"Process {process.name} (PID: {process.pid}) failed with exit code {process.exitcode}"
                )

    except KeyboardInterrupt as e:
        print("🔴 Main process interrupted by user.")
    except RuntimeError as e:
        print("🔴 All subprocesses terminated due to an error.")
    finally:
        terminate_processes(processes)


if __name__ == "__main__":

    load_dotenv()

    main()
