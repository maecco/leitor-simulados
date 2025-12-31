#!/usr/bin/env python3
"""
Leitor de Simulados - API Server

Usage:
    python run.py                  # Run with default settings
    python run.py --port 8080      # Run on custom port
    python run.py --reload         # Run with auto-reload (development)
"""
import argparse
import uvicorn
import sys
from pathlib import Path

# Add src to path
BACKEND_PATH = Path(__file__).parent / "src"
sys.path.insert(0, str(BACKEND_PATH))


def main():
    parser = argparse.ArgumentParser(
        description="Leitor de Simulados API Server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("  📝 Leitor de Simulados - API Server")
    print("=" * 50)
    print(f"  Server: http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/docs")
    print(f"  Reload: {'Enabled' if args.reload else 'Disabled'}")
    print(f"  Workers: {args.workers}")
    print("=" * 50)
    
    uvicorn.run(
        "src.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()
