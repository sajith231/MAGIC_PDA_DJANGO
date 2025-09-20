#!/usr/bin/env python3
"""
SyncService - Django Project Runner
This script starts the Django project and displays terminal output with project status
"""

import os
import sys
import json
import time
import subprocess
import threading
import signal
import re
from datetime import datetime
from pathlib import Path

class SyncServiceRunner:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        # If script is in 'sync' folder, go up one level to find the main project
        if self.script_dir.name == 'sync':
            self.project_dir = self.script_dir.parent
        else:
            self.project_dir = self.script_dir
        
        self.django_dir = self.project_dir / "django_sync"
        self.config_file = self.project_dir / "config.json"
        
        # Look for manage.py in multiple locations
        possible_manage_paths = [
            self.django_dir / "manage.py",
            self.project_dir / "manage.py",
            self.project_dir / "manage"
        ]
        
        self.manage_py = None
        for path in possible_manage_paths:
            if path.exists():
                self.manage_py = path
                break
        
        if not self.manage_py:
            self.manage_py = self.project_dir / "manage.py"  # Default fallback
        self.django_process = None
        self.sync_process = None
        self.running = True
        
        # Load configuration
        self.config = self.load_config()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self):
        """Load configuration from config.json"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Default configuration
                return {
                    "ip": "192.168.1.53",
                    "port": 8000,
                    "dsn": "pktc",
                    "auto_start": True,
                    "log_level": "INFO",
                    "all_ips": ["192.168.1.53", "172.25.240.1"]
                }
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    def print_banner(self):
        """Print application banner"""
        print("=" * 60)
        print("🔄 SyncService - Django Project Runner")
        print("=" * 60)
        print(f"📁 Project Directory: {self.project_dir}")
        print(f"🐍 Django Directory: {self.django_dir}")
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Server IP: {self.config.get('ip', 'Unknown')}")
        print(f"🔌 Server Port: {self.config.get('port', 8000)}")
        print(f"🗄️ Database DSN: {self.config.get('dsn', 'Unknown')}")
        print("=" * 60)
    
    def check_prerequisites(self):
        """Check if all required files exist"""
        print("🔍 Checking prerequisites...")
        
        checks = [
            (self.django_dir.exists(), f"Django directory: {self.django_dir}"),
            (self.manage_py and self.manage_py.exists(), f"manage.py file: {self.manage_py}"),
            (self.config_file.exists(), f"Config file: {self.config_file}")
        ]
        
        all_good = True
        for check, description in checks:
            status = "✅" if check else "❌"
            print(f"  {status} {description}")
            if not check:
                all_good = False
        
        if not all_good:
            print("❌ Some prerequisites are missing!")
            return False
        
        print("✅ All prerequisites satisfied!")
        return True
    
    def start_sync_heartbeat(self):
        """Start the database heartbeat service"""
        def heartbeat_worker():
            import sqlanydb
            DSN = self.config.get('dsn', 'pktc')
            
            while self.running:
                try:
                    conn = sqlanydb.connect(DSN=DSN, UID="dba", PWD="(*$^)")
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    conn.close()
                    print(f"💓 DB heartbeat OK @ {datetime.now().strftime('%H:%M:%S')}")
                except Exception as e:
                    print(f"💔 Heartbeat failed: {e}")
                
                # Wait 30 seconds before next heartbeat
                for _ in range(30):
                    if not self.running:
                        break
                    time.sleep(1)
        
        print("💓 Starting database heartbeat service...")
        heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        heartbeat_thread.start()
        return heartbeat_thread
    
    def start_django_server(self):
        """Start Django development server"""
        print("🚀 Starting Django server...")
        
        ip = self.config.get('ip', '0.0.0.0')
        port = self.config.get('port', 8000)
        
        # Change to the directory containing manage.py
        manage_dir = self.manage_py.parent
        os.chdir(manage_dir)
        
        # Start Django server
        cmd = [sys.executable, str(self.manage_py.name), "runserver", f"{ip}:{port}"]
        print(f"🔧 Command: {' '.join(cmd)}")
        print(f"📂 Working directory: {os.getcwd()}")
        
        try:
            self.django_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print(f"✅ Django server started (PID: {self.django_process.pid})")
            print(f"🌐 Server URLs:")
            for ip_addr in self.config.get('all_ips', [ip]):
                print(f"   📡 http://{ip_addr}:{port}")
            print("-" * 60)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start Django server: {e}")
            return False
    
    def parse_http_status(self, line):
        """Parse HTTP status code from Django log format"""
        try:
            # Django format: [20/Sep/2025 14:19:15] "POST /upload-orders HTTP/1.1" 200 64
            # Use regex to extract the parts
            pattern = r'\[.*?\] "(\w+) ([^\s]+) HTTP/1\.1" (\d+) \d+'
            match = re.search(pattern, line)
            
            if match:
                method = match.group(1)
                endpoint = match.group(2)
                status_code = int(match.group(3))
                return method, endpoint, status_code
            else:
                # Fallback parsing
                if '"GET' in line or '"POST' in line:
                    method = "GET" if '"GET' in line else "POST"
                    # Try to find endpoint and status
                    parts = line.split('"')
                    if len(parts) >= 2:
                        http_part = parts[1]  # "POST /endpoint HTTP/1.1"
                        if ' ' in http_part:
                            endpoint = http_part.split()[1]
                        else:
                            endpoint = "Unknown"
                        
                        # Look for status code after the quoted part
                        remaining = parts[2] if len(parts) > 2 else ""
                        status_match = re.search(r'\s(\d{3})\s', remaining)
                        if status_match:
                            status_code = int(status_match.group(1))
                            return method, endpoint, status_code
                    
                    return method, "Unknown", None
        except Exception:
            pass
        
        return None, None, None
    
    def monitor_django_output(self):
        """Monitor Django server output"""
        if not self.django_process:
            return
        
        success_count = 0
        error_count = 0
        request_count = 0
        login_count = 0
        upload_count = 0
        pair_count = 0
        db_operations = 0
        
        print("📊 Monitoring Django Application Logs:")
        print("-" * 80)
        
        try:
            for line in iter(self.django_process.stdout.readline, ''):
                if not self.running:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                # Parse different types of application messages
                if '📱 Pair check request from:' in line or '\\U0001f4f1 Pair check request from:' in line:
                    pair_count += 1
                    print(f"🔗 PAIR [{timestamp}]: Mobile device pairing request")
                    try:
                        json_part = line.split('from: ')[1] if 'from: ' in line else 'Device connected'
                        print(f"   📱 {json_part}")
                    except:
                        print(f"   📱 Device connected")
                
                elif '✅ SyncService started' in line or 'SyncService already running' in line:
                    success_count += 1
                    if 'already running' in line:
                        pid = line.split('PID ')[1].split(')')[0] if 'PID ' in line else 'Unknown'
                        print(f"🔄 SYNC [{timestamp}]: SyncService already running (PID {pid})")
                    else:
                        print(f"🚀 START [{timestamp}]: SyncService launched successfully")
                
                elif '🔐 Login attempt for user:' in line or '\\U0001f510 Login attempt for user:' in line:
                    login_count += 1
                    user = line.split('user: ')[1] if 'user: ' in line else 'Unknown'
                    print(f"👤 LOGIN [{timestamp}]: User authentication attempt")
                    print(f"   🆔 User ID: {user}")
                
                elif '✅ Login successful' in line or '\\u2705 Login successful' in line:
                    success_count += 1
                    print(f"✅ AUTH [{timestamp}]: Login completed successfully")
                
                elif '📤 Uploading' in line and 'orders' in line:
                    upload_count += 1
                    order_count = line.split('Uploading ')[1].split(' orders')[0] if 'Uploading ' in line else '?'
                    print(f"📤 UPLOAD [{timestamp}]: Processing {order_count} order(s)")
                
                elif '📦 Raw JSON received:' in line:
                    try:
                        # Extract order details from JSON
                        json_part = line.split('Raw JSON received: ')[1]
                        import json
                        data = json.loads(json_part)
                        total = data.get('total_orders', '?')
                        print(f"   📊 Total Orders: {total}")
                        if 'orders' in data and data['orders']:
                            first_order = data['orders'][0]
                            supplier = first_order.get('supplier_code', 'Unknown')
                            barcode = first_order.get('barcode', 'Unknown')
                            qty = first_order.get('quantity', '?')
                            print(f"   🏪 Supplier: {supplier} | 📦 Item: {barcode} | 📈 Qty: {qty}")
                    except:
                        print(f"   📦 Order data received")
                
                elif '📥 Data download request' in line or '\\U0001f4e5 Data download request' in line:
                    print(f"📥 DOWNLOAD [{timestamp}]: Data download request received")
                
                elif 'Downloaded' in line and 'masters' in line and 'products' in line:
                    try:
                        parts = line.split('Downloaded ')[1]
                        masters = parts.split(' masters')[0]
                        products = parts.split(', ')[1].split(' products')[0]
                        success_count += 1
                        print(f"📊 DATA [{timestamp}]: Download completed")
                        print(f"   🏪 Masters: {masters} | 📦 Products: {products}")
                    except:
                        print(f"📊 DATA [{timestamp}]: Download completed")
                
                elif 'BEFORE –' in line and 'master today:' in line:
                    db_operations += 1
                    parts = line.split('master today: ')[1].split('  detail today: ')
                    master_before = parts[0] if len(parts) > 1 else '?'
                    detail_before = parts[1] if len(parts) > 1 else '?'
                    print(f"🗄️  DB-BEFORE [{timestamp}]: Masters: {master_before} | Details: {detail_before}")
                
                elif 'AFTER –' in line and 'master today:' in line:
                    parts = line.split('master today: ')[1].split('  detail today: ')
                    master_after = parts[0] if len(parts) > 1 else '?'
                    detail_after = parts[1] if len(parts) > 1 else '?'
                    print(f"🗄️  DB-AFTER [{timestamp}]: Masters: {master_after} | Details: {detail_after}")
                
                elif '✅ COMMITTED –' in line or '\\u2705 COMMITTED' in line:
                    success_count += 1
                    try:
                        parts = line.split('master today: ')[1].split('  detail today: ')
                        master_final = parts[0] if len(parts) > 1 else '?'
                        detail_final = parts[1] if len(parts) > 1 else '?'
                        print(f"✅ SUCCESS [{timestamp}]: Database transaction committed!")
                        print(f"   💾 Final Count - Masters: {master_final} | Details: {detail_final}")
                    except:
                        print(f"✅ SUCCESS [{timestamp}]: Database transaction committed!")
                
                elif 'EXEC detail sql=' in line:
                    # Extract SQL execution details
                    if 'params=' in line:
                        params_part = line.split('params=')[1] if 'params=' in line else ''
                        print(f"⚡ SQL [{timestamp}]: Executing database insert")
                        print(f"   🔧 {params_part}")
                
                elif 'Database connection established!' in line:
                    print(f"🔌 DB [{timestamp}]: Database connection successful")
                
                # HTTP Requests with Status Codes
                elif '"GET' in line or '"POST' in line:
                    request_count += 1
                    
                    method, endpoint, status_code = self.parse_http_status(line)
                    
                    # Determine status type
                    if status_code is not None:
                        if status_code == 200:
                            status_emoji = "✅"
                            status_text = "SUCCESS"
                            success_count += 1
                        elif 400 <= status_code < 500:
                            status_emoji = "⚠️"
                            status_text = "CLIENT ERROR"
                            error_count += 1
                        elif status_code >= 500:
                            status_emoji = "❌"
                            status_text = "SERVER ERROR"
                            error_count += 1
                        else:
                            status_emoji = "📡"
                            status_text = "HTTP"
                    else:
                        status_emoji = "📡"
                        status_text = "HTTP"
                        status_code = "Unknown"
                    
                    # Display formatted HTTP request
                    if '/status' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: Status Check - {method} → {status_code}")
                        if status_code == 200:
                            print(f"   ✅ Server status retrieved successfully!")
                    elif '/pair-check' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: Device Pairing - {method} → {status_code}")
                        if status_code == 200:
                            print(f"   🔗 Device pairing successful!")
                    elif '/login' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: User Login - {method} → {status_code}")
                        if status_code == 200:
                            print(f"   🎉 Login authentication successful!")
                        elif status_code == 401:
                            print(f"   🔒 Login failed - Invalid credentials!")
                    elif '/upload-orders' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: Order Upload - {method} → {status_code}")
                        if status_code == 200:
                            print(f"   📦 Orders successfully saved to database!")
                        elif isinstance(status_code, int) and status_code >= 400:
                            print(f"   💥 Order upload failed!")
                    elif '/data-download' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: Data Download - {method} → {status_code}")
                        if status_code == 200:
                            print(f"   📥 Data downloaded successfully!")
                    elif '/verify-token' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: Token Verification - {method} → {status_code}")
                        if status_code == 200:
                            print(f"   🔐 Token is valid!")
                        elif status_code == 401:
                            print(f"   🚫 Token expired or invalid!")
                    else:
                        print(f"{status_emoji} {status_text} [{timestamp}]: {method} {endpoint} → {status_code}")
                
                # Errors and Exceptions
                elif any(word in line.lower() for word in ['error', 'exception', 'failed', 'rollback']):
                    error_count += 1
                    if 'ROLLBACK' in line:
                        print(f"❌ ERROR [{timestamp}]: Database transaction rolled back!")
                        print(f"   ⚠️  {line}")
                    else:
                        print(f"❌ ERROR [{timestamp}]: {line}")
                
                # Keep all the detailed INFO messages as requested
                elif not any(skip in line for skip in ['Watching for file changes', 'StatReloader']):
                    print(f"ℹ️  INFO [{timestamp}]: {line}")
                
                # Print statistics every 15 operations
                total_operations = success_count + error_count + request_count + login_count + upload_count + pair_count
                if total_operations > 0 and total_operations % 20 == 0:
                    self.print_detailed_statistics(success_count, error_count, request_count, login_count, upload_count, pair_count, db_operations)
                    
        except Exception as e:
            print(f"❌ Error monitoring output: {e}")
            import traceback
            traceback.print_exc()
    
    def print_detailed_statistics(self, success_count, error_count, request_count, login_count, upload_count, pair_count, db_operations):
        """Print detailed application statistics"""
        print("\n" + "=" * 80)
        print(f"📊 DETAILED STATISTICS @ {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        print(f"✅ Successful Operations: {success_count}")
        print(f"❌ Errors Encountered: {error_count}")
        print(f"📡 HTTP Requests: {request_count}")
        print(f"👤 Login Attempts: {login_count}")
        print(f"📤 Order Uploads: {upload_count}")
        print(f"🔗 Device Pairings: {pair_count}")
        print(f"🗄️  Database Operations: {db_operations}")
        print("-" * 80)
        total_ops = success_count + error_count + request_count
        if total_ops > 0:
            success_rate = (success_count / total_ops) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"🔄 Total Operations: {total_ops}")
        print("=" * 80 + "\n")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown all services"""
        print("🛑 Shutting down SyncService...")
        self.running = False
        
        # Stop Django server
        if self.django_process:
            print("🔥 Stopping Django server...")
            try:
                self.django_process.terminate()
                self.django_process.wait(timeout=5)
                print("✅ Django server stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing Django server...")
                self.django_process.kill()
                self.django_process.wait()
        
        print("👋 SyncService shutdown complete")
        sys.exit(0)
    
    def run(self):
        """Main run method"""
        try:
            # Print banner
            self.print_banner()
            
            # Check prerequisites
            if not self.check_prerequisites():
                input("\nPress Enter to exit...")
                return
            
            # Start heartbeat service
            self.start_sync_heartbeat()
            
            # Start Django server
            if not self.start_django_server():
                input("\nPress Enter to exit...")
                return
            
            print("🎯 SyncService is now running!")
            print("💡 Press Ctrl+C to stop the service")
            print("=" * 60)
            
            # Monitor Django output
            self.monitor_django_output()
            
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()

def main():
    """Main entry point"""
    try:
        runner = SyncServiceRunner()
        runner.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()