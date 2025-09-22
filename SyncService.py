#!/usr/bin/env python3
"""
SyncService - Django Project Runner with Auto Setup
This script starts the Django project and displays terminal output with project status
Includes automatic environment setup and dependency checking
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

def check_and_setup_environment():
    """Check if virtual environment exists and dependencies are installed"""
    script_dir = Path(__file__).parent
    venv_dir = script_dir / "venv"
    
    # Check if virtual environment exists
    if not venv_dir.exists():
        print("🔧 Virtual environment not found. Setting up environment...")
        print("📋 This may take a few minutes on first run...")
        
        # Check if Python is available
        try:
            result = subprocess.run([sys.executable, "--version"], 
                                 capture_output=True, text=True, check=True)
            print(f"🐍 Python found: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Python not found. Please install Python 3.8+ and try again.")
            input("Press Enter to exit...")
            sys.exit(1)
        
        # Check if requirements.txt exists
        requirements_file = script_dir / "requirements.txt"
        if not requirements_file.exists():
            print("❌ requirements.txt not found!")
            print("🛠️  Creating basic requirements.txt...")
            with open(requirements_file, 'w') as f:
                f.write("Django>=4.2.0,<5.0\n")
                f.write("sqlanydb>=1.0.0\n")
                f.write("requests>=2.28.0\n")
                f.write("python-dateutil>=2.8.0\n")
                f.write("pytz>=2023.3\n")
            print("✅ Basic requirements.txt created")
        
        # Create virtual environment
        print("🔨 Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], 
                         check=True, cwd=script_dir)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            input("Press Enter to exit...")
            sys.exit(1)
        
        # Determine pip path
        if sys.platform == "win32":
            pip_exe = venv_dir / "Scripts" / "pip.exe"
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            pip_exe = venv_dir / "bin" / "pip"
            python_exe = venv_dir / "bin" / "python"
        
        # Upgrade pip
        print("⬆️  Upgrading pip...")
        try:
            subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, cwd=script_dir)
            print("✅ Pip upgraded")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Pip upgrade failed: {e}")
        
        # Install requirements
        print("📦 Installing dependencies...")
        try:
            subprocess.run([str(pip_exe), "install", "-r", "requirements.txt"], 
                         check=True, cwd=script_dir)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            print("💡 Please check your requirements.txt file and internet connection")
            input("Press Enter to exit...")
            sys.exit(1)
        
        # Check if Django project needs setup
        django_dir = script_dir / "django_sync"
        if django_dir.exists():
            manage_py = django_dir / "manage.py"
            if manage_py.exists():
                print("🗄️  Setting up Django database...")
                try:
                    # Run migrations
                    subprocess.run([str(python_exe), str(manage_py), "makemigrations"], 
                                 cwd=django_dir, check=False)
                    subprocess.run([str(python_exe), str(manage_py), "migrate"], 
                                 cwd=django_dir, check=False)
                    print("✅ Django database setup complete")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  Django setup warning: {e}")
        
        print("🎉 Environment setup complete!")
        print("-" * 60)
    
    # Verify virtual environment
    if sys.platform == "win32":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
    
    if not python_exe.exists():
        print("❌ Virtual environment is corrupted. Please delete 'venv' folder and run again.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    return str(python_exe)

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
        """Load configuration from config.json and .env"""
        try:
            # Load from config.json
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    print(f"📄 Configuration loaded from {self.config_file}")
            else:
                # Create default configuration
                config = {
                    "ip": "192.168.1.53",
                    "port": 8000,
                    "dsn": "pktc",
                    "auto_start": True,
                    "log_level": "INFO",
                    "all_ips": ["192.168.1.53", "172.25.240.1", "127.0.0.1"]
                }
                
                # Try to detect local IP
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    if local_ip not in config["all_ips"]:
                        config["all_ips"].append(local_ip)
                        config["ip"] = local_ip
                except:
                    pass
                
                # Save default config
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                print(f"📝 Default configuration created at {self.config_file}")
            
            # Load environment variables from .env file
            env_file = self.project_dir / ".env"
            if env_file.exists():
                print(f"📄 Loading environment variables from {env_file}")
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
            
            # Add database credentials with fallback
            config["db_uid"] = os.getenv("DB_UID", "dba")
            config["db_pwd"] = os.getenv("DB_PWD", "(*$^)")
            
            return config
            
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {
                "ip": "127.0.0.1",
                "port": 8000,
                "dsn": "pktc",
                "auto_start": True,
                "log_level": "INFO",
                "all_ips": ["127.0.0.1"],
                "db_uid": "dba",
                "db_pwd": "(*$^)"
            }
    
    def print_banner(self):
        """Print application banner"""
        print("=" * 60)
        print("🔄 SyncService - Django Project Runner v2.0")
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
            print("💡 Make sure you have the complete project structure")
            return False
        
        print("✅ All prerequisites satisfied!")
        return True
    
    def start_sync_heartbeat(self):
        """Start the database heartbeat service"""
        def heartbeat_worker():
            # Try to import sqlanydb, skip if not available
            try:
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
            
            except ImportError:
                print("⚠️  sqlanydb not available - skipping database heartbeat")
                print("💡 Install SAP SQL Anywhere client if you need database connectivity")
        
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
        
        # Use virtual environment Python if available
        venv_dir = self.script_dir / "venv"
        if venv_dir.exists():
            if sys.platform == "win32":
                python_exe = venv_dir / "Scripts" / "python.exe"
            else:
                python_exe = venv_dir / "bin" / "python"
            
            if python_exe.exists():
                python_cmd = str(python_exe)
            else:
                python_cmd = sys.executable
        else:
            python_cmd = sys.executable
        
        # Start Django server
        cmd = [python_cmd, str(self.manage_py.name), "runserver", f"{ip}:{port}"]
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
            print("💡 Make sure Django is installed and manage.py is accessible")
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
                if 'Pair check request from:' in line or 'U0001f4f1 Pair check request from:' in line:
                    pair_count += 1
                    print(f"🔗 PAIR [{timestamp}]: Mobile device pairing request")
                    try:
                        json_part = line.split('from: ')[1] if 'from: ' in line else 'Device connected'
                        print(f"   📱 {json_part}")
                    except:
                        print(f"   📱 Device connected")
                
                elif 'SyncService started' in line or 'SyncService already running' in line:
                    success_count += 1
                    if 'already running' in line:
                        pid = line.split('PID ')[1].split(')')[0] if 'PID ' in line else 'Unknown'
                        print(f"🔄 SYNC [{timestamp}]: SyncService already running (PID {pid})")
                    else:
                        print(f"🚀 START [{timestamp}]: SyncService launched successfully")
                
                elif 'Login attempt for user:' in line or 'U0001f510 Login attempt for user:' in line:
                    login_count += 1
                    user = line.split('user: ')[1] if 'user: ' in line else 'Unknown'
                    print(f"👤 LOGIN [{timestamp}]: User authentication attempt")
                    print(f"   🆔 User ID: {user}")
                
                elif 'Login successful' in line or 'u2705 Login successful' in line:
                    success_count += 1
                    print(f"✅ AUTH [{timestamp}]: Login completed successfully")
                
                elif 'Uploading' in line and 'orders' in line:
                    upload_count += 1
                    order_count = line.split('Uploading ')[1].split(' orders')[0] if 'Uploading ' in line else '?'
                    print(f"📤 UPLOAD [{timestamp}]: Processing {order_count} order(s)")
                
                elif 'Raw JSON received:' in line:
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
                
                elif 'Data download request' in line or 'U0001f4e5 Data download request' in line:
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
                    print(f"🗄️ DB-BEFORE [{timestamp}]: Masters: {master_before} | Details: {detail_before}")
                
                elif 'AFTER –' in line and 'master today:' in line:
                    parts = line.split('master today: ')[1].split('  detail today: ')
                    master_after = parts[0] if len(parts) > 1 else '?'
                    detail_after = parts[1] if len(parts) > 1 else '?'
                    print(f"🗄️ DB-AFTER [{timestamp}]: Masters: {master_after} | Details: {detail_after}")
                
                elif 'COMMITTED –' in line or 'u2705 COMMITTED' in line:
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
                elif '"GET' in line or '"POST' in line or '"PUT' in line or '"DELETE' in line:
                    request_count += 1
                    
                    method, endpoint, status_code = self.parse_http_status(line)
                    
                    # Determine status type
                    if status_code is not None:
                        if status_code == 200:
                            status_emoji = "✅"
                            status_text = "SUCCESS"
                            success_count += 1
                        elif status_code == 201:
                            status_emoji = "✅"
                            status_text = "CREATED"
                            success_count += 1
                        elif status_code == 400:
                            status_emoji = "⚠️"
                            status_text = "BAD REQUEST"
                            error_count += 1
                        elif status_code == 401:
                            status_emoji = "🔒"
                            status_text = "UNAUTHORIZED"
                            error_count += 1
                        elif status_code == 403:
                            status_emoji = "🚫"
                            status_text = "FORBIDDEN"
                            error_count += 1
                        elif status_code == 404:
                            status_emoji = "❓"
                            status_text = "NOT FOUND"
                            error_count += 1
                        elif status_code == 405:
                            status_emoji = "⛔"
                            status_text = "METHOD NOT ALLOWED"
                            error_count += 1
                        elif 400 <= status_code < 500:
                            status_emoji = "⚠️"
                            status_text = "CLIENT ERROR"
                            error_count += 1
                        elif status_code == 500:
                            status_emoji = "💥"
                            status_text = "INTERNAL ERROR"
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
                    
                    # Display formatted HTTP request with specific URL pattern matching
                    if 'status' in endpoint or '/status' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: STATUS CHECK - {method} /status → {status_code}")
                        if status_code == 200:
                            print(f"   ✅ Server status retrieved successfully!")
                        elif status_code >= 500:
                            print(f"   💥 Status check failed - Server error!")
                    elif 'pair-check' in endpoint or '/pair-check' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: PAIR CHECK - {method} /pair-check → {status_code}")
                        if status_code == 200:
                            print(f"   🔗 Device pairing successful!")
                        elif status_code == 400:
                            print(f"   ⚠️ Invalid pairing request!")
                        elif status_code >= 500:
                            print(f"   💥 Pairing failed - Server error!")
                    elif 'login' in endpoint or '/login' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: LOGIN - {method} /login → {status_code}")
                        if status_code == 200:
                            print(f"   🎉 Login authentication successful!")
                        elif status_code == 401:
                            print(f"   🔒 Login failed - Invalid credentials!")
                        elif status_code == 400:
                            print(f"   ⚠️ Bad login request!")
                        elif status_code >= 500:
                            print(f"   💥 Login failed - Server error!")
                    elif 'verify-token' in endpoint or '/verify-token' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: TOKEN VERIFY - {method} /verify-token → {status_code}")
                        if status_code == 200:
                            print(f"   🔐 Token is valid!")
                        elif status_code == 401:
                            print(f"   🚫 Token expired or invalid!")
                        elif status_code == 400:
                            print(f"   ⚠️ Invalid token format!")
                        elif status_code >= 500:
                            print(f"   💥 Token verification failed - Server error!")
                    elif 'data-download' in endpoint or '/data-download' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: DATA DOWNLOAD - {method} /data-download → {status_code}")
                        if status_code == 200:
                            print(f"   📥 Data downloaded successfully!")
                        elif status_code == 401:
                            print(f"   🔒 Download unauthorized!")
                        elif status_code == 404:
                            print(f"   ❓ Data not found!")
                        elif status_code >= 500:
                            print(f"   💥 Download failed - Server error!")
                    elif 'upload-orders' in endpoint or '/upload-orders' in line:
                        print(f"{status_emoji} {status_text} [{timestamp}]: UPLOAD ORDERS - {method} /upload-orders → {status_code}")
                        if status_code == 200:
                            print(f"   📦 Orders successfully saved to database!")
                        elif status_code == 201:
                            print(f"   📦 Orders created successfully!")
                        elif status_code == 400:
                            print(f"   ⚠️ Invalid order data!")
                        elif status_code == 401:
                            print(f"   🔒 Upload unauthorized!")
                        elif status_code >= 500:
                            print(f"   💥 Order upload failed - Server error!")
                    elif endpoint == '/' or '/admin' in endpoint:
                        print(f"{status_emoji} {status_text} [{timestamp}]: WEB ACCESS - {method} {endpoint} → {status_code}")
                        if status_code == 200:
                            print(f"   🌐 Page loaded successfully!")
                        elif status_code == 404:
                            print(f"   ❓ Page not found!")
                        elif status_code >= 500:
                            print(f"   💥 Page load failed - Server error!")
                    else:
                        print(f"{status_emoji} {status_text} [{timestamp}]: HTTP REQUEST - {method} {endpoint} → {status_code}")
                        if status_code == 200:
                            print(f"   ✅ Request successful!")
                        elif status_code >= 400 and status_code < 500:
                            print(f"   ⚠️ Client error!")
                        elif status_code >= 500:
                            print(f"   💥 Server error!")
                
                # Django startup messages
                elif 'Starting development server' in line:
                    print(f"🚀 DJANGO [{timestamp}]: Development server starting...")
                elif 'Watching for file changes' in line:
                    print(f"👁️ DJANGO [{timestamp}]: File watcher active")
                elif 'Quit the server with CONTROL-C' in line:
                    print(f"✅ DJANGO [{timestamp}]: Server ready - Press Ctrl+C to stop")
                
                # Errors and Exceptions
                elif any(word in line.lower() for word in ['error', 'exception', 'failed', 'rollback']):
                    error_count += 1
                    if 'ROLLBACK' in line:
                        print(f"❌ ERROR [{timestamp}]: Database transaction rolled back!")
                        print(f"   ⚠️ {line}")
                    else:
                        print(f"❌ ERROR [{timestamp}]: {line}")
                
                # Skip Django debug messages but keep application info
                elif not any(skip in line for skip in ['StatReloader', 'autoreload']):
                    # Only show non-empty, meaningful lines
                    if len(line.strip()) > 0:
                        print(f"ℹ️ INFO [{timestamp}]: {line}")
                
                # Print statistics every 20 operations
                total_operations = success_count + error_count + request_count + login_count + upload_count + pair_count
                if total_operations > 0 and total_operations % 25 == 0:
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
        print(f"🗄️ Database Operations: {db_operations}")
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
                print("⚠️ Force killing Django server...")
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
                print("\n💡 Tips:")
                print("   - Make sure all project files are in the correct location")
                print("   - Check that your Django project structure is intact")
                input("\nPress Enter to exit...")
                return
            
            # Start heartbeat service
            self.start_sync_heartbeat()
            
            # Start Django server
            if not self.start_django_server():
                print("\n💡 Troubleshooting:")
                print("   - Check if the port is already in use")
                print("   - Verify Django is properly installed")
                print("   - Make sure manage.py is executable")
                input("\nPress Enter to exit...")
                return
            
            print("🎯 SyncService is now running!")
            print("💡 Press Ctrl+C to stop the service")
            print("🌐 Access your application in a web browser using the URLs above")
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
    """Main entry point with auto-setup"""
    try:
        # First, check and setup the environment
        if __name__ == "__main__":
            python_exe = check_and_setup_environment()
            
            # Re-run the script with the virtual environment Python if needed
            if sys.executable != python_exe:
                print("🔄 Switching to virtual environment...")
                subprocess.run([python_exe, __file__] + sys.argv[1:])
                sys.exit(0)
        
        # Initialize and run the service
        runner = SyncServiceRunner()
        runner.run()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print("💡 Please check the error message above and try again")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()