#!/usr/bin/env python3
"""
Example script to process images using the Leitor de Simulados API

Usage:
    python example_client.py /path/to/images/folder
    python example_client.py /path/to/images/folder --test-type PS_ALUNOS
    python example_client.py image1.jpg image2.jpg image3.jpg
"""
import argparse
import requests
import time
import sys
from pathlib import Path


# Configuration
BASE_URL = "http://localhost:8000/api"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def find_images(paths: list) -> list:
    """Find all image files from given paths (files or directories)"""
    images = []
    
    for path_str in paths:
        path = Path(path_str)
        
        if path.is_file():
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                images.append(path)
            else:
                print(f"⚠️  Skipping non-image file: {path}")
        elif path.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                images.extend(path.glob(f"*{ext}"))
                images.extend(path.glob(f"*{ext.upper()}"))
        else:
            print(f"⚠️  Path not found: {path}")
    
    return sorted(set(images))


def create_session(test_type: str) -> str:
    """Create a new processing session"""
    response = requests.post(
        f"{BASE_URL}/session/create",
        data={"test_type": test_type}
    )
    response.raise_for_status()
    return response.json()["session_id"]


def upload_images(session_id: str, image_paths: list) -> int:
    """Upload images to the session"""
    uploaded = 0
    
    for img_path in image_paths:
        try:
            with open(img_path, "rb") as f:
                response = requests.post(
                    f"{BASE_URL}/upload/{session_id}",
                    files={"files": (img_path.name, f, "image/jpeg")}
                )
                response.raise_for_status()
                uploaded += 1
                print(f"  📤 Uploaded: {img_path.name}")
        except Exception as e:
            print(f"  ❌ Failed to upload {img_path.name}: {e}")
    
    return uploaded


def start_processing(session_id: str, fs_model: str, ss_model: str) -> str:
    """Start batch processing and return job ID"""
    response = requests.post(
        f"{BASE_URL}/process-all/{session_id}",
        data={
            "fs_model": fs_model,
            "ss_model": ss_model,
            "fs_threshold": "0.5",
            "ss_threshold": "0.5"
        }
    )
    response.raise_for_status()
    return response.json()["job_id"]


def poll_progress(job_id: str, poll_interval: float = 2.0) -> dict:
    """Poll for job progress until complete"""
    while True:
        response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        response.raise_for_status()
        status = response.json()
        
        progress = status["progress"]
        pct = progress["percentage"]
        processed = progress["processed"]
        total = progress["total"]
        
        # Print progress bar
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  ⏳ [{bar}] {pct:.1f}% ({processed}/{total})", end="", flush=True)
        
        if status["status"] in ("completed", "failed", "cancelled"):
            print()  # New line after progress bar
            return status
        
        time.sleep(poll_interval)


def get_report(session_id: str, format: str = "json") -> dict:
    """Get the processing report"""
    response = requests.get(f"{BASE_URL}/report/{session_id}/{format}")
    response.raise_for_status()
    return response.json() if format == "json" else response.text


def print_results(status: dict):
    """Print the processing results"""
    progress = status["progress"]
    
    print(f"\n{'='*50}")
    print(f"  📊 RESULTS")
    print(f"{'='*50}")
    print(f"  Total images:  {progress['total']}")
    print(f"  ✅ Successful:  {progress['successful']}")
    print(f"  ❌ Failed:      {progress['failed']}")
    
    if status.get("duration_seconds"):
        print(f"  ⏱️  Duration:    {status['duration_seconds']:.2f}s")
    
    # Print individual results
    if "results" in status:
        print(f"\n  Individual Results:")
        for result in status["results"]:
            icon = "✅" if result["status"] == "success" else "❌"
            filename = result.get("filename", result.get("image_id", "unknown"))
            if result["status"] == "success":
                print(f"    {icon} {filename} - {result.get('detections_count', 0)} detections")
            else:
                print(f"    {icon} {filename} - Error: {result.get('error', 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(
        description="Process exam sheet images using Leitor de Simulados API"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Image files or directories containing images"
    )
    parser.add_argument(
        "--test-type",
        choices=["SIMUFSC", "PS_ALUNOS", "SIMUENEM"],
        default="SIMUFSC",
        help="Type of test/exam (default: SIMUFSC)"
    )
    parser.add_argument(
        "--fs-model",
        default="YoloV8/first_stage/general_fs.pt",
        help="First stage model path"
    )
    parser.add_argument(
        "--ss-model",
        default="YoloV8/second_stage/general_ss_v2.pt",
        help="Second stage model path"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/api",
        help="API base URL"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output results as CSV"
    )
    
    args = parser.parse_args()
    
    global BASE_URL
    BASE_URL = args.base_url
    
    print(f"\n{'='*50}")
    print(f"  🔍 LEITOR DE SIMULADOS - Client")
    print(f"{'='*50}")
    
    # Find images
    print(f"\n📁 Finding images...")
    images = find_images(args.paths)
    
    if not images:
        print("❌ No images found!")
        sys.exit(1)
    
    print(f"  Found {len(images)} image(s)")
    
    try:
        # Create session
        print(f"\n📋 Creating session (test type: {args.test_type})...")
        session_id = create_session(args.test_type)
        print(f"  Session ID: {session_id}")
        
        # Upload images
        print(f"\n📤 Uploading images...")
        uploaded = upload_images(session_id, images)
        print(f"  Uploaded {uploaded}/{len(images)} images")
        
        if uploaded == 0:
            print("❌ No images uploaded!")
            sys.exit(1)
        
        # Start processing
        print(f"\n🚀 Starting processing...")
        job_id = start_processing(session_id, args.fs_model, args.ss_model)
        print(f"  Job ID: {job_id}")
        
        # Poll for progress
        print(f"\n⏳ Processing...")
        status = poll_progress(job_id)
        
        # Handle result
        if status["status"] == "completed":
            print_results(status)
            
            # Get CSV if requested
            if args.csv:
                print(f"\n📄 CSV Report:")
                print("-" * 50)
                csv_report = get_report(session_id, "csv")
                print(csv_report)
            
            print(f"\n✅ Processing complete!")
            
        elif status["status"] == "failed":
            print(f"\n❌ Processing failed: {status.get('error', 'Unknown error')}")
            sys.exit(1)
            
        elif status["status"] == "cancelled":
            print(f"\n⚠️  Processing was cancelled")
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to API at {BASE_URL}")
        print(f"   Make sure the server is running: python run.py")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ API error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
