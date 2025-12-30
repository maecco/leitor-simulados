#!/usr/bin/env python3
"""
Leitor de Simulados - Desktop Client
Launches the lightweight desktop client that connects to the server

Usage:
    python run_client.py                           # Connect to localhost:8000
    python run_client.py --server http://server:8000  # Connect to remote server
"""
import argparse
import sys
from pathlib import Path

# Add desktop_client to path
CLIENT_PATH = Path(__file__).parent / "desktop_client"
sys.path.insert(0, str(CLIENT_PATH))


def main():
    parser = argparse.ArgumentParser(
        description="Leitor de Simulados - Desktop Client"
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Server URL to connect to (default: http://localhost:8000)"
    )
    args = parser.parse_args()
    
    print("=" * 50)
    print("  📝 Leitor de Simulados - Desktop Client")
    print("=" * 50)
    print(f"  Default server: {args.server}")
    print("=" * 50)
    
    from client import DesktopClient
    
    app = DesktopClient()
    app.server_var.set(args.server)
    app.mainloop()


if __name__ == "__main__":
    main()
