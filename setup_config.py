#!/usr/bin/env python3
"""
Configuration Setup Helper
Interactive configuration setup for Django SyncService
"""

import json
import socket
from pathlib import Path

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def check_port_availability(ip, port):
    """Check if port is available"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((ip, port))
        s.close()
        return True
    except:
        return False

def setup_config():
    """Interactive configuration setup"""
    print("=" * 60)
    print("Django SyncService Configuration Setup")
    print("=" * 60)
    
    # Get current config or create default
    config_file = Path("config.json")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        print("Found existing configuration")
    else:
        config = {
            "ip": "127.0.0.1",
            "port": 8000,
            "dsn": "pktc",
            "auto_start": True,
            "log_level": "INFO",
            "all_ips": []
        }
    
    # Get local IP
    local_ip = get_local_ip()
    print(f"Detected local IP: {local_ip}")
    
    # Interactive setup
    print("\nConfiguration Setup:")
    print("(Press Enter to keep current value)")
    
    # Server IP
    current_ip = config.get('ip', local_ip)
    new_ip = input(f"Server IP [{current_ip}]: ").strip()
    if new_ip:
        config["ip"] = new_ip
    elif not config.get("ip"):
        config["ip"] = local_ip
    
    # Server Port
    current_port = config.get('port', 8000)
    while True:
        new_port = input(f"Server Port [{current_port}]: ").strip()
        if new_port:
            try:
                port = int(new_port)
                if 1024 <= port <= 65535:
                    if check_port_availability(config["ip"], port):
                        config["port"] = port
                        break
                    else:
                        print(f"Port {port} is already in use. Try another port.")
                else:
                    print("Port must be between 1024 and 65535")
            except ValueError:
                print("Invalid port number")
        else:
            if check_port_availability(config["ip"], current_port):
                config["port"] = current_port
                break
            else:
                print(f"Default port {current_port} is in use. Please choose another port.")
    
    # Database DSN
    current_dsn = config.get('dsn', 'pktc')
    new_dsn = input(f"Database DSN [{current_dsn}]: ").strip()
    if new_dsn:
        config["dsn"] = new_dsn
    elif not config.get("dsn"):
        config["dsn"] = current_dsn
    
    # Auto-start option
    current_autostart = config.get('auto_start', True)
    autostart_str = "y" if current_autostart else "n"
    new_autostart = input(f"Auto-start service [{autostart_str}]: ").strip().lower()
    if new_autostart in ['y', 'yes', 'true', '1']:
        config["auto_start"] = True
    elif new_autostart in ['n', 'no', 'false', '0']:
        config["auto_start"] = False
    
    # Log level
    current_log_level = config.get('log_level', 'INFO')
    print(f"\nAvailable log levels: DEBUG, INFO, WARNING, ERROR")
    new_log_level = input(f"Log Level [{current_log_level}]: ").strip().upper()
    if new_log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        config["log_level"] = new_log_level
    elif not config.get("log_level"):
        config["log_level"] = current_log_level
    
    # Update all_ips
    config["all_ips"] = [config["ip"], local_ip, "127.0.0.1"]
    if "192.168.1.53" not in config["all_ips"]:
        config["all_ips"].append("192.168.1.53")
    config["all_ips"] = list(set(config["all_ips"]))  # Remove duplicates
    
    # Save configuration
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\nConfiguration saved to {config_file}")
    print(f"Server will be accessible at:")
    for ip in config["all_ips"]:
        print(f"   http://{ip}:{config['port']}")
    
    # Show summary
    print("\n" + "=" * 60)
    print("Configuration Summary:")
    print("=" * 60)
    print(f"Server IP: {config['ip']}")
    print(f"Server Port: {config['port']}")
    print(f"Database DSN: {config['dsn']}")
    print(f"Auto Start: {config['auto_start']}")
    print(f"Log Level: {config['log_level']}")
    print("=" * 60)
    
    return config

if __name__ == "__main__":
    try:
        setup_config()
        print("\nConfiguration setup complete!")
        input("Press Enter to continue...")
    except KeyboardInterrupt:
        print("\nConfiguration setup cancelled")
    except Exception as e:
        print(f"Error during configuration setup: {e}")
        input("Press Enter to exit...")