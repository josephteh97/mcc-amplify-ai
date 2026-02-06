# Complete Deployment Guide
## Ubuntu-First Approach (Windows Revit Later)

---

## 🎯 Deployment Strategy

We are using a Hybrid Distributed Architecture:

    Linux (Ubuntu): Handles heavy lifting (OCR, Computer Vision, Claude AI, 3D Geometry generation).

    Windows (Revit): Acts as the "Executive Arm" that receives instructions and builds native BIM models.

Since Windows Revit is not ready yet, we'll deploy in phases:

**Phase 1:** Ubuntu system (Stages 1-6) - **DO THIS NOW**
- Upload PDFs
- AI analysis
- 3D geometry
- Generate Revit transaction JSON
- Test everything except final RVT export

**Phase 2:** Windows Revit server - **DO LATER**
- Add RVT export capability when Windows is ready

---

## 📋 Prerequisites Checklist

### Ubuntu Machine (Your Development Machine)
- [ ] Ubuntu 20.04 LTS or 22.04 LTS
- [ ] 16GB RAM minimum (32GB recommended)
- [ ] 100GB free disk space
- [ ] Internet connection
- [ ] sudo/root access

### Required Accounts
- [ ] Anthropic account (for Claude API)
- [ ] Credit card for API usage (~$20/month)

---

## Part 1: Ubuntu System Setup (Phase 1)

### Step 1: System Preparation (5 minutes)

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential git curl wget nano software-properties-common

# Install OpenCV dependencies (Ubuntu 22.04+ compatible)
sudo apt install -y \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1

# Install PDF and OCR tools
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript

# Install Node.js 20.x LTS (Current stable version)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs

# Verify installations
node --version   # Should show v20.x.x
npm --version    # Should show 10.x.x
tesseract --version  # Should show Tesseract 4.x or 5.x

echo "✓ All system dependencies installed successfully!"
```

### Step 2: Install Miniconda (5 minutes)

```bash
# Download Miniconda
cd ~
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Install Miniconda
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

# Initialize conda
$HOME/miniconda3/bin/conda init bash

# Reload shell
source ~/.bashrc

# Verify installation
conda --version  # Should show conda 23.x.x or higher
```

### Step 3: Clone Repository (2 minutes)

```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/josephteh97/mcc-amplify-ai.git

# Enter project directory
cd mcc-amplify-ai

# Check structure
ls -la
# You should see: linux_server/, windows_server/, README.md, etc.
```

### Step 4: Setup Linux Server (10 minutes)

```bash
# Navigate to linux server
cd ~/mcc-amplify-ai/linux_server

# Create conda environment
conda env create -f environment.yml

# This will take 5-10 minutes
# It installs Python 3.10 and all dependencies

# Activate environment
conda activate floorplan-ai

# Verify Python version
python --version  # Should show Python 3.10.x

# Verify key packages
python -c "import fastapi; print('FastAPI OK')"
python -c "import anthropic; print('Anthropic OK')"
python -c "import cv2; print('OpenCV OK')"
```

### Step 5: Install Backend Dependencies (5 minutes)

```bash
# Navigate to backend
cd ~/mcc-amplify-ai/linux_server/backend

# Install Python dependencies
pip install -r requirements.txt

# This installs additional packages not in conda

# Verify critical imports
python -c "import ultralytics; print('YOLO OK')"
python -c "import trimesh; print('Trimesh OK')"
```

### Step 6: Install Frontend Dependencies (10 minutes)

```bash
# Navigate to frontend
cd ~/mcc-amplify-ai/linux_server/frontend

# Install Node.js dependencies
npm install

# This will take 5-10 minutes
# Downloads React, Vite, Three.js, etc.

# Build frontend for production
npm run build

# This creates the 'dist' folder with optimized files
```

### Step 7: Configure Environment (5 minutes)

```bash
# Go back to linux_server root
cd ~/mcc-amplify-ai/linux_server

# Create .env file from example
cp .env.example .env

# Edit .env file
nano .env
```

**Update these critical values:**

```bash
# ============================================
# REQUIRED: Update these values
# ============================================

# 1. Get your Claude API key from https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_ACTUAL_KEY_HERE

# 2. Windows server (LEAVE AS IS FOR NOW - we'll update later)
WINDOWS_REVIT_SERVER=http://localhost:5000
REVIT_SERVER_API_KEY=temporary-key-for-now

# 3. Application settings (can leave as default)
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# 4. File upload settings
MAX_UPLOAD_SIZE=52428800
ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png

# 5. Processing defaults
DEFAULT_WALL_HEIGHT=2800
DEFAULT_FLOOR_THICKNESS=200
DEFAULT_CEILING_HEIGHT=3000
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

### Step 8: Create Data Directories (1 minute)

```bash
# Create required directories
cd ~/mcc-amplify-ai/linux_server

mkdir -p data/uploads
mkdir -p data/processed
mkdir -p data/models/revit_transactions
mkdir -p data/models/rvt
mkdir -p data/models/gltf
mkdir -p logs

# Set permissions
chmod -R 755 data/
chmod -R 755 logs/

# Verify structure
tree -L 2 data/
```

### Step 9: Test Backend (5 minutes)

```bash
# Make sure conda environment is active
conda activate floorplan-ai

# Navigate to backend
cd ~/mcc-amplify-ai/linux_server/backend

# Run the application
python app.py
```

**You should see:**
```
INFO:     Starting server on 0.0.0.0:8000
INFO:     Application startup complete.
✓ System ready!
```

**Open another terminal and test:**
```bash
# Test health endpoint
curl -v http://LT-HQ-277:49152/health
## curl http://localhost:8000/health

# Should return:
# {"status":"healthy","service":"Amplify Floor Plan AI","version":"1.0.0"}
```

**If it works:** Press `Ctrl+C` to stop the server

### Step 10: Test Frontend (5 minutes)

```bash
# Open a new terminal
# Navigate to frontend
cd ~/mcc-amplify-ai/linux_server/frontend

# Run development server
npm run dev
```

**You should see:**
```
  VITE v5.0.8  ready in 2000 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Test in browser:**
1. Open: `http://localhost:5173`
2. You should see the upload interface
3. Press `Ctrl+C` to stop

---

## Part 2: Windows Revit Setup (The Builder)

**This section describes how to deploy the C# Bridge we built.**

### Step 1: Prerequisites

    Windows 10/11 with Revit 2023 installed.

    .NET SDK 8.0 (for building) and .NET Framework 4.8 (for running).

### Step 2: Build the Revit Plugin

    Verify output exists at: ...\bin\Debug\net48\RevitService.dll

### Step 3: Install the Add-in

Copy the .addin manifest to the Revit discovery folder:

    Copy RevitService.addin to %AppData%\Autodesk\Revit\Addins\2023\

    Ensure the <Assembly> path inside the file points to your net48\RevitService.dll.

### Step 4: Start the Service

    Launch Revit 2023.

    Click "Always Load" on the security popup.

    Open any project file (The service requires an active document to process commands).

### Step 5: Connecting the Pipeline

    Update Ubuntu Configuration

    Edit ~/mcc-amplify-ai/linux_server/.env:
    The Full Workflow Test

    Ubuntu: curl -X POST http://localhost:8000/process -d @floorplan.pdf

    Processing: System converts PDF → YOLO Detection → Claude Analysis → Revit JSON.

    Execution: Ubuntu sends JSON to http://LT-HQ-277:49152/build.

    Result: A native Revit wall appears automatically in the Windows Revit instance.

📋 Status Dashboard
📞 Troubleshooting Handshake Issues

If Ubuntu cannot see Revit:

    Check Port: Run Test-NetConnection -ComputerName localhost -Port 49152 on Windows.

    Firewall: Ensure Windows Firewall allows Inbound TCP Traffic on Port 49152.

    Revit State: Ensure Revit is not in a "Modal" state (like having an Options window or Print dialog open), as this blocks the API.
---

## Part 3: Setup Nginx (Optional but Recommended)

```bash
# Install nginx
sudo apt install -y nginx

# Create configuration
sudo nano /etc/nginx/sites-available/floorplan-ai
```

**Add this configuration:**

```nginx
server {
    listen 80;
    server_name localhost;

    client_max_body_size 50M;

    # Serve frontend
    location / {
        root /home/youruser/mcc-amplify-ai/linux_server/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**Enable and test:**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/floorplan-ai /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Enable nginx on boot
sudo systemctl enable nginx
```

**Access:** http://localhost or http://YOUR_IP_ADDRESS

---

## Part 4: Test the System (Without RVT Export)

### Step 1: Upload a PDF

1. Open browser: `http://localhost` or `http://localhost:5173`
2. Click "Upload Floor Plan"
3. Select a PDF file (or use test file from `tests/sample_plans/`)

### Step 2: Watch Processing

You'll see progress through stages:
- ✅ Processing PDF...
- ✅ Detecting scale...
- ✅ Detecting elements (AI)...
- ✅ Analyzing with Claude AI...
- ✅ Generating 3D geometry...
- ✅ Creating Revit instructions...
- ⏳ Building Revit model... (This will fail - expected!)

### Step 3: Check Outputs

```bash
# View generated files
cd ~/mcc-amplify-ai/linux_server/data/models

# Revit transaction JSON (Stage 6 output)
cat revit_transactions/YOUR_JOB_ID.json

# This JSON file will be sent to Windows server later
```

### Step 4: View Logs

```bash
# Backend logs
tail -f ~/mcc-amplify-ai/linux_server/logs/app.log

# Or if using systemd:
sudo journalctl -u floorplan-backend -f
```

---

## Part 5: Understanding What's Working

### ✅ Working Now (Stages 1-6):

| Stage | Component | Status |
|-------|-----------|--------|
| 1 | PDF Processing | ✅ Working |
| 2 | Scale Detection | ✅ Working |
| 3 | Element Detection (YOLO) | ✅ Working |
| 4 | AI Analysis (Claude) | ✅ Working |
| 5 | 3D Geometry | ✅ Working |
| 6 | Revit Transaction JSON | ✅ Working |

**Output:** JSON file with complete Revit instructions

### ⏳ Pending (Stage 7):

| Stage | Component | Status |
|-------|-----------|--------|
| 7 | Windows Revit Server | ⏳ Not installed yet |

**When Windows is ready:**
- Install Revit 2023
- Setup Windows service
- Connect to Ubuntu system
- Get native .RVT files

---

## Part 6: Troubleshooting

### Issue: Backend won't start

```bash
# Check conda environment
conda activate floorplan-ai
which python  # Should show path with 'floorplan-ai'

# Check logs
tail -50 ~/mcc-amplify-ai/linux_server/logs/app.log

# Test imports
python -c "import fastapi, anthropic, cv2; print('OK')"
```

### Issue: Frontend shows blank page

```bash
# Rebuild frontend
cd ~/mcc-amplify-ai/linux_server/frontend
npm run build

# Check nginx configuration
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Issue: "Cannot connect to Windows server"

**This is expected!** You don't have Windows server yet.

The system will work through Stage 6 and generate the JSON file.
Stage 7 (RVT export) will fail gracefully.

**To bypass for now:**
```bash
# Edit .env
nano ~/mcc-amplify-ai/linux_server/.env

# Make sure this is set:
WINDOWS_REVIT_SERVER=http://localhost:5000
# This tells the system Windows server is not ready
```

### Issue: Claude API errors

```bash
# Check API key
cat ~/mcc-amplify-ai/linux_server/.env | grep ANTHROPIC_API_KEY

# Test API key
python << EOF
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=10,
    messages=[{"role": "user", "content": "Hello"}]
)
print("API Key OK:", message.content[0].text)
EOF
```

### Issue: Permission denied

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER ~/mcc-amplify-ai/linux_server/data/
sudo chown -R $USER:$USER ~/mcc-amplify-ai/linux_server/logs/
chmod -R 755 ~/mcc-amplify-ai/linux_server/data/
chmod -R 755 ~/mcc-amplify-ai/linux_server/logs/
```


```bash
echo "191.168.124.64 LT-HQ-277" | sudo tee -a /etc/hosts  ## tell Ubuntu the hostname and ip of the same PC

curl -v http://LT-HQ-277:49152/health
```
---

## Part 7: What to Show Your Supervisor (Now)

### Demo Flow:

1. **Upload PDF floor plan**
   - Show web interface
   - Upload sample plan

2. **Watch AI processing**
   - Real-time progress bar
   - Each stage completes
   - Takes 30-60 seconds

3. **Show generated data:**
   ```bash
   # Show Revit transaction JSON
   cat data/models/revit_transactions/LATEST_JOB_ID.json | less
   
   # Explain: "This JSON contains exact Revit API commands"
   # Point out: walls, doors, windows with precise coordinates
   ```

4. **Explain what's working:**
   - ✅ PDF analysis: Complete
   - ✅ AI detection: Complete
   - ✅ 3D geometry: Complete
   - ✅ Revit instructions: Complete
   - ⏳ RVT export: Waiting for Windows Revit

5. **Show next steps:**
   - "Once Windows Revit is installed..."
   - "We just connect it and get native .RVT files"
   - "No code changes needed"

---

## Part 8: Monitoring & Maintenance

### Check System Health:

```bash
# Backend status
sudo systemctl status floorplan-backend

# Disk space
df -h ~/mcc-amplify-ai/linux_server/data/

# Memory usage
free -h

# Recent logs
sudo journalctl -u floorplan-backend --since "10 minutes ago"
```

### Cleanup Old Files:

```bash
# Clean up old uploads (keep last 7 days)
find ~/mcc-amplify-ai/linux_server/data/uploads/ -type f -mtime +7 -delete

# Clean up old processed files
find ~/mcc-amplify-ai/linux_server/data/processed/ -type f -mtime +7 -delete

# Clean up old logs
find ~/mcc-amplify-ai/linux_server/logs/ -type f -name "*.log" -mtime +30 -delete
```

### Backup Important Files:

```bash
# Create backup directory
mkdir -p ~/backups

# Backup .env file
cp ~/mcc-amplify-ai/linux_server/.env ~/backups/.env.backup

# Backup generated transaction JSONs
tar -czf ~/backups/transactions-$(date +%Y%m%d).tar.gz \
    ~/mcc-amplify-ai/linux_server/data/models/revit_transactions/
```

---

## Part 9: When Windows Revit is Ready

### What You'll Need to Do:

1. **Install Revit 2023 on Windows machine**

2. **Get Windows IP address:**
   ```cmd
   ipconfig
   # Note the IPv4 Address
   ```

3. **Update Ubuntu .env:**
   ```bash
   nano ~/mcc-amplify-ai/linux_server/.env
   
   # Change this:
   WINDOWS_REVIT_SERVER=http://192.168.1.100:5000  # Your Windows IP
   REVIT_SERVER_API_KEY=your-secure-key
   ```

4. **Setup Windows service:**
   - Follow Part 2 of original deployment guide
   - Install Python service on Windows
   - Start Revit API server
   ```powershell
   # Get window ready for handshake
   cd C:\MyDocuments\mcc-amplify-ai\revit_server\csharp_service
   dotnet run
   ```

5. **Test connection:**
   ```bash
   curl http://WINDOWS_IP:5000/health
   ```

6. **Restart backend:**
   ```bash
   sudo systemctl restart floorplan-backend
   ```

7. **Test full pipeline:**
   - Upload PDF
   - Should complete all stages including RVT export!

---

## ✅ Deployment Checklist (Ubuntu Only)

- [ ] Ubuntu system updated
- [ ] System dependencies installed (tesseract, poppler, opencv)
- [ ] Miniconda installed
- [ ] Repository cloned
- [ ] Conda environment created
- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed
- [ ] Frontend built (`npm run build`)
- [ ] .env file configured with Claude API key
- [ ] Data directories created
- [ ] Backend tested manually (`python app.py`)
- [ ] Frontend tested manually (`npm run dev`)
- [ ] Systemd service created (optional)
- [ ] Nginx configured (optional)
- [ ] Can upload PDF and see processing through Stage 6
- [ ] Generated JSON files visible in data/models/revit_transactions/

---

## 📞 Getting Help

**If something doesn't work:**

1. **Check logs first:**
   ```bash
   tail -100 ~/mcc-amplify-ai/linux_server/logs/app.log
   ```

2. **Test individual components:**
   ```bash
   # Test Python environment
   conda activate floorplan-ai
   python -c "import sys; print(sys.executable)"
   
   # Test API key
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Key:', os.getenv('ANTHROPIC_API_KEY')[:20])"
   ```

3. **Restart everything:**
   ```bash
   sudo systemctl restart floorplan-backend
   sudo systemctl restart nginx
   ```

4. **Check GitHub issues:**
   - https://github.com/josephteh97/mcc-amplify-ai/issues

---

## 🎯 Summary

**What you have now:**
- ✅ Complete Ubuntu system
- ✅ Stages 1-6 fully working
- ✅ Can process PDFs and generate Revit instructions
- ✅ Ready to demo to supervisor

**What's pending:**
- ⏳ Windows Revit server (when machine is ready)
- ⏳ Stage 7: Native .RVT export

**Time to complete:** ~1 hour for Ubuntu setup

**You're ready to show your supervisor the AI processing capabilities!** 🚀