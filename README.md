# Django SyncService - Quick Setup Guide

## 🚀 Quick Start (Recommended)

### Windows Users:
1. **Double-click** `install.bat`
2. Wait for installation to complete
3. **Double-click** `SyncService.py` to start
4. **Alternative**: Double-click `start.bat`

### Linux/Mac Users:
1. Open terminal in project folder
2. Run: `chmod +x install.sh && ./install.sh`
3. Run: `python SyncService.py`
4. **Alternative**: Run: `chmod +x start.sh && ./start.sh`

## 🔧 Manual Setup (If needed)

### Prerequisites:
- Python 3.8 or higher
- Internet connection for package installation

### Step-by-step:
1. Install Python from https://python.org (Windows users: check "Add to PATH")
2. Open command prompt/terminal in project folder
3. Run: `python -m pip install -r requirements.txt`
4. Run: `python setup_config.py` (optional - for custom configuration)
5. Run: `python SyncService.py`

## 🌐 Access URLs

After starting, your application will be available at:
- http://localhost:8000
- http://127.0.0.1:8000
- http://YOUR_LOCAL_IP:8000

## ⚙️ Configuration

Run `python setup_config.py` to configure:
- Server IP address
- Server port
- Database DSN
- Auto-start options
- Logging level

## 📋 Features

- ✅ Automatic dependency installation
- ✅ Virtual environment management
- ✅ Database heartbeat monitoring  
- ✅ Real-time request logging
- ✅ Mobile device pairing
- ✅ Order upload/download system
- ✅ Interactive configuration setup

## 📁 Project Structure

```
YourProject/
├── django_sync/           # Django application
│   ├── manage.py
│   └── ...
├── SyncService.py         # Main application launcher
├── install.bat           # Windows installer
├── install.sh            # Linux/Mac installer
├── start.bat             # Windows quick start
├── start.sh              # Linux/Mac quick start
├── setup_config.py       # Configuration helper
├── requirements.txt      # Python dependencies
├── config.json          # Configuration file
└── README.md            # This file
```

## 🆘 Troubleshooting

### Python not found:
- **Windows**: Reinstall Python with "Add to PATH" checked
- **Linux**: `sudo apt install python3 python3-pip python3-venv`
- **Mac**: `brew install python3`

### Permission denied (Linux/Mac):
```bash
chmod +x install.sh
chmod +x start.sh
chmod +x SyncService.py
```

### Port already in use:
- Change port in config.json
- Or run: `python setup_config.py`
- Or kill the process using the port

### Database connection issues:
- Check your SAP SQL Anywhere installation
- Verify DSN configuration in config.json
- Make sure database service is running

### Virtual environment issues:
- Delete the `venv` folder
- Re-run the installation script

### Django migrations:
If you encounter database migration issues:
```bash
# Activate virtual environment first
# Windows:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Then run:
cd django_sync
python manage.py makemigrations
python manage.py migrate
cd ..
```

## 🔄 Updates and Maintenance

### To update dependencies:
```bash
# Activate virtual environment
# Then run:
pip install --upgrade -r requirements.txt
```

### To reset the environment:
1. Delete the `venv` folder
2. Re-run installation script

## 💡 Usage Tips

1. **First Time Setup**: Always run the installation script first
2. **Configuration**: Use `setup_config.py` for easy configuration
3. **Monitoring**: Check the console output for real-time status
4. **Stopping**: Press Ctrl+C to stop the service gracefully
5. **Logs**: All activity is logged to the console with timestamps

## 🔐 Security Notes

- The default configuration listens on localhost only
- Change the IP address in config.json to allow external access
- Consider using proper authentication in production
- Database credentials should be secured properly

## 📞 Support

For issues:
1. Check the console output for detailed error messages
2. Verify all prerequisites are installed
3. Try running `python setup_config.py` to reconfigure
4. Make sure all project files are in the correct locations

## 🎯 Quick Commands

```bash
# Installation
install.bat              # Windows installation
./install.sh             # Linux/Mac installation

# Starting the application
python SyncService.py    # Cross-platform
start.bat               # Windows quick start
./start.sh              # Linux/Mac quick start

# Configuration
python setup_config.py  # Interactive configuration

# Manual Django operations
cd django_sync
python manage.py runserver 0.0.0.0:8000
```

---

**Version**: 2.0  
**Compatible with**: Python 3.8+, Django 4.2+  
**Platform**: Windows, Linux, macOS











DISTRIBUTION FOLDER :::


Complete Deployment Package
I've created a complete deployment package for your Django SyncService project. Here's what you now have:
📦 Files Created:

Updated SyncService.py - Enhanced with automatic environment setup
install.bat - Windows automatic installation
install.sh - Linux/Mac automatic installation
start.bat - Windows quick launcher
start.sh - Linux/Mac quick launcher
requirements.txt - All Python dependencies
setup_config.py - Interactive configuration helper
README.md - Complete user documentation

🎯 Key Features Added:

Auto-environment setup: Automatically creates virtual environment and installs dependencies
Cross-platform compatibility: Works on Windows, Linux, and Mac
Error handling: Comprehensive error checking and user-friendly messages
Configuration management: Interactive configuration setup
Enhanced logging: Better status messages and monitoring

📋 For Distribution, Include These Files:
YourProject/
├── django_sync/          # Your Django project folder
├── SyncService.py        # Updated main launcher
├── install.bat          # Windows installer
├── install.sh           # Linux/Mac installer
├── start.bat            # Windows quick start
├── start.sh             # Linux/Mac quick start
├── setup_config.py      # Configuration helper
├── requirements.txt     # Dependencies
├── config.json          # Your config file
└── README.md            # User instructions