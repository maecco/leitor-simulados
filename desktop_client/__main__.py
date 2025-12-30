#!/usr/bin/env python3
"""
Leitor de Simulados - Desktop Client Launcher
Run this script to start the desktop client application
"""
import sys
from pathlib import Path

# Add desktop_client to path
CLIENT_PATH = Path(__file__).parent
sys.path.insert(0, str(CLIENT_PATH))

from client import DesktopClient


def main():
    print("=" * 50)
    print("  📝 Leitor de Simulados - Desktop Client")
    print("=" * 50)
    
    app = DesktopClient()
    app.mainloop()


if __name__ == "__main__":
    main()
