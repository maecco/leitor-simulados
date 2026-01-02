#!/usr/bin/env python3
"""
Interactive client for Leitor de Simulados API

Run: python interactive_client.py
"""
import requests
import time
import sys
import os
from pathlib import Path
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000/api"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


class InteractiveClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.job_id: Optional[str] = None
        self.history: list = []
    
    def request(self, method: str, endpoint: str, **kwargs):
        """Make a request and handle errors"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, **kwargs)
            return response
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to {self.base_url}")
            print("   Make sure the server is running: python run.py")
            return None
    
    # ==================== Commands ====================
    
    def cmd_help(self, args: list):
        """Show help"""
        print("""
╔══════════════════════════════════════════════════════════════════╗
║                    AVAILABLE COMMANDS                            ║
╠══════════════════════════════════════════════════════════════════╣
║ SESSION MANAGEMENT                                               ║
║   create [TYPE]      Create session (SIMUFSC, PS_ALUNOS, etc)    ║
║   session            Show current session info                   ║
║   sessions           List all sessions (if supported)            ║
║   delete             Delete current session                      ║
║                                                                  ║
║ IMAGE MANAGEMENT                                                 ║
║   upload <PATH>      Upload image(s) - file or folder            ║
║   images             List images in current session              ║
║                                                                  ║
║ PROCESSING                                                       ║
║   process            Process all images (background job)         ║
║   process-one <ID>   Process single image by ID                  ║
║   status             Check current job status                    ║
║   watch              Watch job progress live                     ║
║   cancel             Cancel current job                          ║
║   results            Get job results                             ║
║                                                                  ║
║ REPORTS                                                          ║
║   report             Get JSON report for session                 ║
║   csv                Get CSV report for session                  ║
║                                                                  ║
║ SYSTEM                                                           ║
║   system-status      Show hardware & models info (GPU/CPU)       ║
║   models             List available models                       ║
║   jobs               Show job manager stats                      ║
║   health             Check API health                            ║
║                                                                  ║
║ OTHER                                                            ║
║   set-url <URL>      Change API base URL                         ║
║   history            Show command history                        ║
║   clear              Clear screen                                ║
║   help               Show this help                              ║
║   quit / exit        Exit the client                             ║
╚══════════════════════════════════════════════════════════════════╝
        """)
    
    def cmd_create(self, args: list):
        """Create a new session"""
        test_type = args[0].upper() if args else "SIMUFSC"
        
        response = self.request("POST", "/session/create", data={"test_type": test_type})
        if response and response.ok:
            data = response.json()
            self.session_id = data["session_id"]
            print(f"✅ Session created!")
            print(f"   ID: {self.session_id}")
            print(f"   Type: {data['test_type']}")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_session(self, args: list):
        """Show current session info"""
        if not self.session_id:
            print("⚠️  No active session. Use 'create' first.")
            return
        
        response = self.request("GET", f"/session/{self.session_id}")
        if response and response.ok:
            data = response.json()
            print(f"📋 Session Info:")
            print(f"   ID: {data['session_id']}")
            print(f"   Type: {data['test_type']}")
            print(f"   Images: {data['image_count']}")
            print(f"   Processed: {data['processed_count']}")
            print(f"   Created: {data['created_at']}")
        elif response:
            print(f"❌ Session not found")
            self.session_id = None
    
    def cmd_delete(self, args: list):
        """Delete current session"""
        if not self.session_id:
            print("⚠️  No active session.")
            return
        
        response = self.request("DELETE", f"/session/{self.session_id}")
        if response and response.ok:
            print(f"✅ Session {self.session_id} deleted")
            self.session_id = None
            self.job_id = None
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_upload(self, args: list):
        """Upload images"""
        if not self.session_id:
            print("⚠️  No active session. Use 'create' first.")
            return
        
        if not args:
            print("⚠️  Usage: upload <path>")
            print("   Examples:")
            print("     upload image.jpg")
            print("     upload /path/to/folder/")
            return
        
        path = Path(" ".join(args))  # Handle paths with spaces
        images = []
        
        if path.is_file():
            images = [path]
        elif path.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                images.extend(path.glob(f"*{ext}"))
                images.extend(path.glob(f"*{ext.upper()}"))
            images = sorted(set(images))
        else:
            print(f"❌ Path not found: {path}")
            return
        
        if not images:
            print(f"❌ No images found in: {path}")
            return
        
        print(f"📤 Uploading {len(images)} image(s)...")
        uploaded = 0
        
        for img_path in images:
            try:
                # Determine content type
                ext = img_path.suffix.lower()
                content_types = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".bmp": "image/bmp",
                    ".tiff": "image/tiff",
                }
                content_type = content_types.get(ext, "image/jpeg")
                
                with open(img_path, "rb") as f:
                    response = self.request(
                        "POST",
                        f"/upload/{self.session_id}",
                        files=[("files", (img_path.name, f, content_type))]
                    )
                    if response and response.ok:
                        data = response.json()
                        if data.get("uploaded"):
                            uploaded += 1
                            print(f"   ✅ {img_path.name}")
                        elif data.get("skipped"):
                            reason = data["skipped"][0].get("reason", "Unknown")
                            print(f"   ⚠️  {img_path.name} - Skipped: {reason}")
                    elif response:
                        detail = response.json().get("detail", response.text) if response.text else "Unknown error"
                        print(f"   ❌ {img_path.name} - {detail}")
                    else:
                        print(f"   ❌ {img_path.name} - Connection failed")
            except Exception as e:
                print(f"   ❌ {img_path.name} - {e}")
        
        print(f"\n📊 Uploaded {uploaded}/{len(images)} images")
    
    def cmd_images(self, args: list):
        """List images in session"""
        if not self.session_id:
            print("⚠️  No active session. Use 'create' first.")
            return
        
        response = self.request("GET", f"/images/{self.session_id}")
        if response and response.ok:
            data = response.json()
            images = data.get("images", [])
            
            if not images:
                print("📭 No images in session")
                return
            
            print(f"🖼️  Images in session ({len(images)}):")
            for img in images:
                status = "✅" if img.get("processed") else "⏳"
                print(f"   {status} [{img['id'][:8]}] {img['filename']}")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_process(self, args: list):
        """Process all images"""
        if not self.session_id:
            print("⚠️  No active session. Use 'create' first.")
            return
        
        fs_model = "YoloV8/first_stage/general_fs.pt"
        ss_model = "YoloV8/second_stage/general_ss_v2.pt"
        
        # Allow overriding models
        if len(args) >= 2:
            fs_model, ss_model = args[0], args[1]
        
        print(f"🚀 Starting processing...")
        print(f"   FS Model: {fs_model}")
        print(f"   SS Model: {ss_model}")
        
        response = self.request(
            "POST",
            f"/process-all/{self.session_id}",
            data={
                "fs_model": fs_model,
                "ss_model": ss_model,
                "fs_threshold": "0.5",
                "ss_threshold": "0.5"
            }
        )
        
        if response and response.ok:
            data = response.json()
            self.job_id = data["job_id"]
            print(f"✅ Job started!")
            print(f"   Job ID: {self.job_id}")
            print(f"   Images: {data['total_images']}")
            print(f"\n   Use 'status' to check progress, or 'watch' to monitor")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")

    def cmd_process_one(self, args: list):
        """Process single image"""
        if not self.session_id:
            print("⚠️  No active session.")
            return
        
        if not args:
            print("⚠️  Usage: process-one <image_id>")
            return
        
        image_id = args[0]
        response = self.request(
            "POST",
            f"/process/{self.session_id}/{image_id}",
            data={
                "fs_model": "YoloV8/first_stage/general_fs.pt",
                "ss_model": "YoloV8/second_stage/general_ss_v2.pt"
            }
        )
        
        if response and response.ok:
            data = response.json()
            print(f"✅ Image processed!")
            print(f"   Detections: {data['detections_count']}")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_status(self, args: list):
        """Check job status"""
        job_id = args[0] if args else self.job_id
        
        if not job_id:
            print("⚠️  No active job. Use 'process' first, or 'status <job_id>'")
            return
        
        response = self.request("GET", f"/jobs/{job_id}")
        if response and response.ok:
            data = response.json()
            progress = data["progress"]
            
            status_icons = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫"
            }
            icon = status_icons.get(data["status"], "❓")
            
            print(f"{icon} Job Status: {data['status'].upper()}")
            print(f"   Progress: {progress['processed']}/{progress['total']} ({progress['percentage']}%)")
            print(f"   Success: {progress['successful']}, Failed: {progress['failed']}")
            
            if data.get("duration_seconds"):
                print(f"   Duration: {data['duration_seconds']:.2f}s")
            if data.get("error"):
                print(f"   Error: {data['error']}")
        elif response:
            print(f"❌ Job not found")
    
    def cmd_watch(self, args: list):
        """Watch job progress until complete"""
        job_id = args[0] if args else self.job_id
        
        if not job_id:
            print("⚠️  No active job.")
            return
        
        print("👀 Watching job progress (Ctrl+C to stop)...")
        try:
            while True:
                response = self.request("GET", f"/jobs/{job_id}")
                if not response or not response.ok:
                    break
                
                data = response.json()
                progress = data["progress"]
                pct = progress["percentage"]
                
                bar_len = 30
                filled = int(bar_len * pct / 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                
                print(f"\r   [{bar}] {pct:.1f}% ({progress['processed']}/{progress['total']})", end="", flush=True)
                
                if data["status"] in ("completed", "failed", "cancelled"):
                    print(f"\n✅ Job {data['status']}")
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Stopped watching")
    
    def cmd_cancel(self, args: list):
        """Cancel current job"""
        job_id = args[0] if args else self.job_id
        
        if not job_id:
            print("⚠️  No active job.")
            return
        
        response = self.request("POST", f"/jobs/{job_id}/cancel")
        if response and response.ok:
            print(f"✅ Job cancelled")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_results(self, args: list):
        """Get job results"""
        job_id = args[0] if args else self.job_id
        
        if not job_id:
            print("⚠️  No active job.")
            return
        
        response = self.request("GET", f"/jobs/{job_id}/results")
        if response and response.ok:
            data = response.json()
            print(f"📊 Results for job {job_id}:")
            print(f"   Total: {data['summary']['total']}")
            print(f"   Success: {data['summary']['successful']}")
            print(f"   Failed: {data['summary']['failed']}")
            
            print(f"\n   Details:")
            for r in data["results"]:
                icon = "✅" if r["status"] == "success" else "❌"
                name = r.get("filename", r.get("image_id", "?"))
                if r["status"] == "success":
                    print(f"   {icon} {name} - {r.get('detections_count', 0)} detections")
                else:
                    print(f"   {icon} {name} - {r.get('error', 'Error')}")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_report(self, args: list):
        """Get JSON report"""
        if not self.session_id:
            print("⚠️  No active session.")
            return
        
        # Use /reports/ for all reports or /export/ for export format
        response = self.request("GET", f"/reports/{self.session_id}")
        if response and response.ok:
            import json
            data = response.json()
            if data.get("reports"):
                print(f"📊 Reports ({data['total']} images):\n")
                print(json.dumps(data, indent=2))
            else:
                print("⚠️  No reports yet. Process images first.")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_csv(self, args: list):
        """Get CSV report"""
        if not self.session_id:
            print("⚠️  No active session.")
            return
        
        response = self.request("GET", f"/export/{self.session_id}", params={"format": "csv"})
        if response and response.ok:
            data = response.json()
            csv_content = data.get("csv", "")
            if csv_content:
                print(csv_content)
            else:
                print("⚠️  No data to export. Process images first.")
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
    
    def cmd_models(self, args: list):
        """List available models"""
        response = self.request("GET", "/models")
        if response and response.ok:
            models = response.json().get("models", [])
            print(f"🤖 Available Models ({len(models)}):")
            for m in models:
                print(f"   [{m['target_stage']}] {m['rel_path']}")
        elif response:
            print(f"❌ Error getting models")
    
    def cmd_jobs(self, args: list):
        """Show job manager stats"""
        response = self.request("GET", "/jobs/")
        if response and response.ok:
            data = response.json()
            print(f"📊 Job Manager Stats:")
            print(f"   Total jobs: {data['total_jobs']}")
            print(f"   By status: {data['by_status']}")
            print(f"   Parallel: {data['parallel_enabled']}")
            print(f"   Max concurrent: {data['max_concurrent_jobs']}")
    
    def cmd_health(self, args: list):
        """Check API health"""
        response = self.request("GET", "/health")
        if response and response.ok:
            print(f"✅ API is healthy")
        else:
            print(f"❌ API is not responding")
    
    def cmd_system_status(self, args: list):
        """Show system status including hardware and models"""
        response = self.request("GET", "/status")
        if response and response.ok:
            data = response.json()
            
            # Server status
            print(f"🖥️  Server Status: {data.get('server_status', 'unknown').upper()}")
            
            # Hardware info
            hw = data.get("hardware", {})
            print(f"\n⚙️  Hardware:")
            print(f"   CPU Cores: {hw.get('cpu_cores', 'N/A')}")
            if hw.get("cuda_available"):
                print(f"   GPU: ✅ CUDA Available")
                print(f"   GPU Device: {hw.get('cuda_device_name', 'Unknown')}")
                print(f"   GPU Count: {hw.get('cuda_device_count', 0)}")
            else:
                print(f"   GPU: ❌ CUDA Not Available (using CPU)")
            
            # Models info
            models = data.get("available_models", {})
            print(f"\n🤖 Available Models ({data.get('models_count', len(models))}):\n")
            
            for key, model in models.items():
                device_icon = "🎮" if model.get('running_on') == 'cuda' else "💻"
                print(f"   {device_icon} {model.get('name', key)}")
                print(f"      Type: {model.get('type', 'N/A')}")
                print(f"      Stage: {model.get('stage', 'N/A')}")
                print(f"      Device: {model.get('running_on', 'N/A').upper()}")
                print(f"      Path: {model.get('path', 'N/A')}")
                print()
        elif response:
            print(f"❌ Error: {response.json().get('detail', response.text)}")
        else:
            print(f"❌ Could not connect to server")
    
    def cmd_set_url(self, args: list):
        """Change API URL"""
        if not args:
            print(f"   Current URL: {self.base_url}")
            print(f"   Usage: set-url http://localhost:8000/api")
            return
        
        self.base_url = args[0]
        print(f"✅ API URL set to: {self.base_url}")
    
    def cmd_history(self, args: list):
        """Show command history"""
        if not self.history:
            print("📜 No command history")
            return
        
        print("📜 Command History:")
        for i, cmd in enumerate(self.history[-20:], 1):
            print(f"   {i}. {cmd}")
    
    def cmd_clear(self, args: list):
        """Clear screen"""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def cmd_info(self, args: list):
        """Show current state"""
        print(f"📍 Current State:")
        print(f"   API URL: {self.base_url}")
        print(f"   Session: {self.session_id or 'None'}")
        print(f"   Job: {self.job_id or 'None'}")
    
    # ==================== Main Loop ====================
    
    def run(self):
        """Run the interactive loop"""
        print("""
╔══════════════════════════════════════════════════════════════════╗
║         🔍 LEITOR DE SIMULADOS - Interactive Client              ║
║                                                                  ║
║  Type 'help' for available commands, 'quit' to exit             ║
╚══════════════════════════════════════════════════════════════════╝
        """)
        
        # Command mapping
        commands = {
            "help": self.cmd_help,
            "?": self.cmd_help,
            "create": self.cmd_create,
            "session": self.cmd_session,
            "delete": self.cmd_delete,
            "upload": self.cmd_upload,
            "images": self.cmd_images,
            "process": self.cmd_process,
            "process-one": self.cmd_process_one,
            "status": self.cmd_status,
            "watch": self.cmd_watch,
            "cancel": self.cmd_cancel,
            "results": self.cmd_results,
            "report": self.cmd_report,
            "csv": self.cmd_csv,
            "models": self.cmd_models,
            "jobs": self.cmd_jobs,
            "health": self.cmd_health,
            "system-status": self.cmd_system_status,
            "sys": self.cmd_system_status,  # Alias
            "set-url": self.cmd_set_url,
            "history": self.cmd_history,
            "clear": self.cmd_clear,
            "info": self.cmd_info,
        }
        
        while True:
            try:
                # Build prompt
                prompt_parts = ["leitor"]
                if self.session_id:
                    prompt_parts.append(f"session:{self.session_id[:8]}")
                if self.job_id:
                    prompt_parts.append(f"job:{self.job_id[:8]}")
                prompt = f"[{' | '.join(prompt_parts)}]> "
                
                # Get input
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Parse command
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1].split() if len(parts) > 1 else []
                
                # Handle quit
                if cmd in ("quit", "exit", "q"):
                    print("👋 Goodbye!")
                    break
                
                # Execute command
                if cmd in commands:
                    self.history.append(user_input)
                    commands[cmd](args)
                else:
                    print(f"❓ Unknown command: {cmd}")
                    print("   Type 'help' for available commands")
                
                print()  # Empty line after each command
                
            except KeyboardInterrupt:
                print("\n   (Use 'quit' to exit)")
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Interactive client for Leitor de Simulados")
    parser.add_argument("--url", default=BASE_URL, help="API base URL")
    args = parser.parse_args()
    
    client = InteractiveClient(base_url=args.url)
    client.run()


if __name__ == "__main__":
    main()
