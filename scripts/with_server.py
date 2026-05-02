#!/usr/bin/env python3
"""
Server Lifecycle Manager for Web Application Testing

Starts one or more servers, waits for them to be ready, runs a command, then stops them.
Useful for automated testing where you need servers running in the background.

Usage:
    python scripts/with_server.py --server "command" --port PORT -- command_to_run

Examples:
    # Single server
    python scripts/with_server.py --server "npm run dev" --port 5173 -- python test_webapp.py

    # Multiple servers
    python scripts/with_server.py \\
      --server "uvicorn src.api.app:app --port 8000" --port 8000 \\
      --server "npm run dev" --port 5173 \\
      -- pytest tests/e2e/

    # FastAPI + React development stack
    python scripts/with_server.py \\
      --server "cd backend && python -m uvicorn app:app --reload --port 8000" --port 8000 \\
      --server "cd frontend && npm run dev" --port 5173 \\
      -- python playwright_tests.py
"""

import subprocess
import time
import sys
import argparse
import requests
import signal
import os
from typing import List, Tuple
from contextlib import contextmanager


class ServerManager:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []

    def start_server(self, command: str, port: int, wait_timeout: int = 30) -> bool:
        """Start a server and wait for it to be ready"""
        print(f"🚀 Starting server: {command}")
        print(f"📡 Expected on port: {port}")

        # Start the server process
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for clean shutdown
            )
            self.processes.append(process)
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False

        # Wait for server to be ready
        print(f"⏳ Waiting for server on port {port}...")
        for attempt in range(wait_timeout):
            try:
                response = requests.get(f"http://localhost:{port}", timeout=1)
                if response.status_code < 500:  # Accept any non-server-error response
                    print(f"✅ Server ready on port {port}")
                    return True
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                pass

            time.sleep(1)
            print(".", end="", flush=True)

            # Check if process died
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"\n❌ Server process died")
                print(f"STDOUT: {stdout.decode()[:500]}...")
                print(f"STDERR: {stderr.decode()[:500]}...")
                return False

        print(f"\n❌ Server on port {port} not ready after {wait_timeout} seconds")
        return False

    def stop_all_servers(self):
        """Stop all started servers"""
        for process in self.processes:
            if process.poll() is None:  # Still running
                try:
                    # Terminate the entire process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    # Force kill if needed
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

        print(f"🛑 Stopped {len(self.processes)} servers")
        self.processes.clear()

    @contextmanager
    def managed_servers(self, servers: List[Tuple[str, int]], wait_timeout: int = 30):
        """Context manager for server lifecycle"""
        try:
            # Start all servers
            all_ready = True
            for command, port in servers:
                if not self.start_server(command, port, wait_timeout):
                    all_ready = False
                    break

            if not all_ready:
                print("❌ Not all servers started successfully")
                self.stop_all_servers()
                return False

            print(f"✅ All {len(servers)} servers ready!")
            yield True

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self.stop_all_servers()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Start servers, run command, then stop servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--server",
        action="append",
        nargs=1,
        metavar="COMMAND",
        help="Server command to start (can be used multiple times)",
        dest="servers"
    )

    parser.add_argument(
        "--port",
        action="append",
        type=int,
        metavar="PORT",
        help="Port for the corresponding server (must match --server order)"
    )

    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=30,
        help="Seconds to wait for servers to be ready (default: 30)"
    )

    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run after servers are ready"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if not args.servers:
        print("❌ No servers specified. Use --server to specify at least one server.")
        sys.exit(1)

    if not args.port or len(args.servers) != len(args.port):
        print("❌ Each --server must have a corresponding --port")
        sys.exit(1)

    if not args.command:
        print("❌ No command specified to run after servers start")
        sys.exit(1)

    # Remove the '--' separator if present
    if args.command and args.command[0] == '--':
        args.command = args.command[1:]

    # Prepare server list
    servers = [(server[0], port) for server, port in zip(args.servers, args.port)]

    print("🔧 Server Lifecycle Manager")
    print("=" * 50)
    for i, (command, port) in enumerate(servers):
        print(f"Server {i+1}: {command} → port {port}")
    print(f"Command: {' '.join(args.command)}")
    print("=" * 50)

    manager = ServerManager()

    with manager.managed_servers(servers, args.wait_timeout) as success:
        if not success:
            sys.exit(1)

        # Run the user command
        print(f"\n🎯 Running command: {' '.join(args.command)}")
        try:
            result = subprocess.run(args.command, check=False)
            print(f"\n✅ Command completed with exit code: {result.returncode}")
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            print("\n🛑 Command interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Command failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()