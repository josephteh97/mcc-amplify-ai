# Deployment Guide

Complete guide for deploying the Amplify Floor Plan AI System.

## Prerequisites

### Linux Server
- Ubuntu 20.04 LTS or later
- 32GB RAM (16GB minimum)
- 8+ CPU cores
- 500GB SSD storage
- Static IP address or domain name

### Windows Server
- Windows Server 2019+ or Windows 10/11 Pro
- Autodesk Revit 2022 or later with valid license
- 16GB RAM minimum
- 4+ CPU cores
- .NET 6.0 SDK
- Static IP address on same network as Linux server

## Part 1: Linux Server Setup

### Step 1: System Preparation

```bash
# Update system
sudo apt update

# Install system dependencies
# sudo apt install -y build-essential git curl wget
# sudo apt install -y tesseract-ocr
# sudo apt install -y poppler-utils  # For pdf2image
# sudo apt install -y libgl1-mesa-glx  # For OpenCV

```

### Step 2: Clone Repository

```bash


# Navigate to Linux server directory
cd linux_server
```

### Step 3: Create Conda Environment

```bash
# Create environment from yml
conda env create -f environment.yml

# Activate environment
conda activate floorplan-ai

# Verify installation
python --version  # Should show Python 3.10.x
```

### Step 4: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt

# Download YOLOv8 weights (if not included)
# This will be done automatically on first run, or:
# python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Step 5: Install Frontend Dependencies

```bash
cd ../frontend
npm install
npm run build  # Build for production
```

### Step 6: Configure Environment

```bash
cd ..
cp .env.example .env
nano .env
```

Edit the following critical values:
- `ANTHROPIC_API_KEY`: Your Claude API key
- `WINDOWS_REVIT_SERVER`: IP address of Windows machine (e.g., http://192.168.1.100:5000)
- `REVIT_SERVER_API_KEY`: Secure random string (must match Windows config)

### Step 7: Setup Database

```bash
# Create database directory
mkdir -p data/database

# Run migrations (if using PostgreSQL)
cd backend
alembic upgrade head
```

### Step 8: Create Systemd Service

```bash
sudo nano /etc/systemd/system/floorplan-backend.service
```

Add:
```ini
[Unit]
Description=Floor Plan AI Backend
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/amplify-floor-plan-ai/linux_server/backend
Environment="PATH=/home/youruser/miniconda3/envs/floorplan-ai/bin"
ExecStart=/home/youruser/miniconda3/envs/floorplan-ai/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable floorplan-backend
sudo systemctl start floorplan-backend
sudo systemctl status floorplan-backend
```

### Step 9: Setup Nginx (Optional but Recommended)

```bash
sudo apt install -y nginx

sudo nano /etc/nginx/sites-available/floorplan-ai
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50M;

    # Frontend
    location / {
        root /home/youruser/amplify-floor-plan-ai/linux_server/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/floorplan-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Part 2: Windows Server Setup

### Option A: C# Service (Recommended)

#### Step 1: Install Prerequisites

1. Install Autodesk Revit 2022 or later
2. Install .NET 6.0 SDK from https://dotnet.microsoft.com/download
3. Install Git for Windows

#### Step 2: Clone Repository

```powershell
# Open PowerShell as Administrator
cd C:\
git clone https://github.com/yourusername/amplify-floor-plan-ai.git
cd amplify-floor-plan-ai\windows_server\csharp_service
```

#### Step 3: Configure

```powershell
# Edit config.json
notepad config.json
```

Update:
- `api_key`: Must match Linux server's REVIT_SERVER_API_KEY
- `template_path`: Path to your Revit template
- `output_directory`: Where to save RVT files

#### Step 4: Build Service

```powershell
# Build the C# project
dotnet build -c Release

# Test run (before installing as service)
dotnet run --project RevitService.csproj
```

Test by visiting: http://localhost:5000/health

#### Step 5: Install as Windows Service

```powershell
# Create output directory
New-Item -ItemType Directory -Force -Path C:\RevitOutput
New-Item -ItemType Directory -Force -Path C:\RevitService\Logs

# Install as service using SC
sc create "RevitAPIService" binPath="C:\amplify-floor-plan-ai\windows_server\csharp_service\bin\Release\net6.0\RevitService.exe" start=auto

# Start service
sc start RevitAPIService

# Check status
sc query RevitAPIService
```

#### Step 6: Configure Firewall

```powershell
# Allow port 5000
New-NetFirewallRule -DisplayName "Revit API Service" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### Option B: Python Service (Alternative)

#### Step 1: Install Prerequisites

1. Install Autodesk Revit 2022 or later
2. Install Python 3.10 from python.org
3. Install pythonnet dependencies

#### Step 2: Install Python Dependencies

```powershell
cd C:\amplify-floor-plan-ai\windows_server\python_service

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### Step 3: Configure and Run

```powershell
# Edit config
notepad config.json

# Run service
python revit_server.py
```

## Part 3: Network Configuration

### Ensure Connectivity

**On Linux server:**
```bash
# Test connectivity to Windows
curl http://windows-ip:5000/health
```

**On Windows server:**
```powershell
# Test if service is accessible
Invoke-WebRequest -Uri http://localhost:5000/health
```

### Security Considerations

1. **Firewall Rules**
   - Linux: Allow port 8000 (backend) and 80/443 (nginx)
   - Windows: Allow port 5000 (Revit service)

2. **API Key Security**
   - Use strong random keys
   - Rotate keys regularly
   - Never commit to git

3. **HTTPS (Production)**
   - Use Let's Encrypt for SSL certificates
   - Enable HTTPS in Nginx configuration

## Part 4: Testing Deployment

### Test Linux Backend

```bash
# Check backend is running
curl http://localhost:8000/health

# Check logs
tail -f logs/app.log
```

### Test Windows Service

```powershell
# Check service status
sc query RevitAPIService

# Check logs
Get-Content C:\RevitService\Logs\service.log -Tail 50 -Wait
```

### End-to-End Test

1. Open web browser: http://linux-server-ip
2. Upload a sample PDF floor plan
3. Watch processing progress
4. Download generated RVT file
5. Open RVT in Revit to verify

## Part 5: Monitoring & Maintenance

### Linux Server Monitoring

```bash
# View backend logs
sudo journalctl -u floorplan-backend -f

# Check resource usage
htop

# Check disk space
df -h
```

### Windows Server Monitoring

```powershell
# Check service logs
Get-EventLog -LogName Application -Source "RevitAPIService" -Newest 50

# Monitor performance
Task Manager > Performance tab
```

### Backup Strategy

**Linux Server:**
```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf backup-$DATE.tar.gz data/ backend/database/
```

**Windows Server:**
```powershell
# Backup Revit templates and config
Copy-Item -Path "C:\RevitService\config.json" -Destination "C:\Backups\config-$(Get-Date -Format 'yyyyMMdd').json"
```

## Troubleshooting

### Common Issues

**Linux: Backend won't start**
```bash
# Check Python environment
conda activate floorplan-ai
which python

# Check dependencies
pip list | grep fastapi

# Check environment variables
cat .env
```

**Windows: Revit service fails**
```powershell
# Verify Revit is installed
Test-Path "C:\Program Files\Autodesk\Revit 2022\Revit.exe"

# Check .NET version
dotnet --version

# Restart service
sc stop RevitAPIService
sc start RevitAPIService
```

**Connection refused between servers**
```bash
# On Linux, test connection
telnet windows-ip 5000

# Check firewall
sudo ufw status
```

## Production Checklist

- [ ] SSL certificate installed (Let's Encrypt)
- [ ] Firewall rules configured
- [ ] API keys rotated and secured
- [ ]
