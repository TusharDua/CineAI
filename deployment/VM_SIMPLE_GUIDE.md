# CINEAI VM Deployment - Complete Step-by-Step Guide

This guide will take you from VM creation to a fully working app with your GoDaddy domain.

---

## Part 1: Create and Setup VM (15 minutes)

### Step 1: Create VM on GCP

```bash
# Set your project
export PROJECT_ID="your-project-id"
export ZONE="us-central1-a"

# Set project
gcloud config set project $PROJECT_ID

# Create VM
gcloud compute instances create cineai-vm \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-standard-4 \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-balanced \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server,https-server

# Create firewall rules
gcloud compute firewall-rules create allow-http \
    --project=$PROJECT_ID \
    --allow tcp:80,tcp:443 \
    --target-tags http-server

gcloud compute firewall-rules create allow-api \
    --project=$PROJECT_ID \
    --allow tcp:8000 \
    --target-tags http-server
```

### Step 2: Get VM's External IP

```bash
# Get the external IP - save this!
gcloud compute instances describe cineai-vm \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

**Save this IP!** You'll need it for GoDaddy DNS.

---

## Part 2: Install Software on VM (10 minutes)

### Step 1: SSH into VM

```bash
gcloud compute ssh cineai-vm --zone=$ZONE
```

### Step 2: Install Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.11
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# Install other dependencies
sudo apt-get install -y \
    nginx \
    ffmpeg \
    git \
    curl

# Install Node.js (for building React)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## Part 3: Deploy Application (20 minutes)

### Step 1: Clone Your Code

```bash
# Go to home directory
cd ~

# Clone repository (replace with your repo)
git clone https://github.com/yourusername/CINEAI.git
# OR upload files manually
```

**If you don't have a git repo**, upload files:

```bash
# From your local machine:
gcloud compute scp --recurse ~/Documents/CINEAI cineai-vm:~ --zone=$ZONE
```

### Step 2: Setup Backend

```bash
cd ~/CINEAI/backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
nano .env
```

**Add to .env:**
```
GEMINI_API_KEY=your_gemini_api_key_here
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Step 3: Build React Frontend

```bash
cd ~/CINEAI/frontend

# Install dependencies
npm install

# Create production environment file
nano .env.production
```

**Add to .env.production:**
```
VITE_API_URL=http://your-domain.com/api
```

Replace `your-domain.com` with your actual domain.

Press `Ctrl+X`, then `Y`, then `Enter` to save.

```bash
# Build React app
npm run build
```

This creates a `dist` folder with production-ready files.

---

## Part 4: Setup Backend Service (10 minutes)

### Create Systemd Service

```bash
sudo nano /etc/systemd/system/cineai-api.service
```

**Add this content** (replace `YOUR_USERNAME` with your actual username):

```ini
[Unit]
Description=CINEAI API Service
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/CINEAI/backend
Environment="PATH=/home/YOUR_USERNAME/CINEAI/backend/venv/bin"
ExecStart=/home/YOUR_USERNAME/CINEAI/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**To get your username:**
```bash
whoami
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Start Backend Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable cineai-api

# Start service
sudo systemctl start cineai-api

# Check status
sudo systemctl status cineai-api
```

You should see "active (running)" in green.

---

## Part 5: Setup Nginx (15 minutes)

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/cineai
```

**Add this content** (replace `YOUR_USERNAME` and `your-domain.com`):

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Frontend - Serve React build
    location / {
        root /home/YOUR_USERNAME/CINEAI/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API - Proxy to FastAPI backend
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Important: Allow long-running requests (for video processing)
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_connect_timeout 3600s;
    }

    # Serve uploaded videos
    location /uploads/ {
        alias /home/YOUR_USERNAME/CINEAI/backend/uploads/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Allow large file uploads
    client_max_body_size 2G;
}
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Enable Nginx Site

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/cineai /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# If test passes, restart Nginx
sudo systemctl restart nginx
```

---

## Part 6: Setup GoDaddy Domain (5 minutes)

### Step 1: Login to GoDaddy

1. Go to https://godaddy.com
2. Login to your account
3. Go to **My Products** → **DNS** for your domain

### Step 2: Add DNS Records

**Add/Update these records:**

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_VM_IP | 600 |
| A | www | YOUR_VM_IP | 600 |

Replace `YOUR_VM_IP` with the external IP from Step 2 of Part 1.

**Example:**
- Type: `A`
- Name: `@`
- Value: `34.123.45.67` (your VM's IP)
- TTL: `600`

**Wait 5-10 minutes** for DNS propagation.

---

## Part 7: Setup SSL (HTTPS) (5 minutes)

### Install Certbot

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts:
1. Enter your email
2. Agree to terms (Yes)
3. Share email (No)
4. Redirect HTTP to HTTPS (Yes - option 2)

**That's it!** Certbot automatically:
- Gets SSL certificate
- Configures Nginx for HTTPS
- Sets up auto-renewal

---

## Part 8: Test Everything (5 minutes)

### Test Backend API

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### Test from Browser

1. Go to: `http://your-domain.com`
2. You should see the CINEAI frontend
3. Try uploading a video
4. Check if it processes

### Check Logs

```bash
# Backend logs
sudo journalctl -u cineai-api -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Common Commands

### Restart Services

```bash
# Restart backend
sudo systemctl restart cineai-api

# Restart Nginx
sudo systemctl restart nginx

# Check backend status
sudo systemctl status cineai-api
```

### Update Code

```bash
# Pull latest code
cd ~/CINEAI
git pull

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart cineai-api

# Update frontend
cd ../frontend
npm install
npm run build
```

### View Logs

```bash
# Backend logs (real-time)
sudo journalctl -u cineai-api -f

# Backend logs (last 100 lines)
sudo journalctl -u cineai-api -n 100

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

---

## Troubleshooting

### Issue: Backend not starting

```bash
# Check status
sudo systemctl status cineai-api

# Check logs
sudo journalctl -u cineai-api -n 50

# Common fixes:
# 1. Check .env file exists
ls ~/CINEAI/backend/.env

# 2. Check virtual environment
ls ~/CINEAI/backend/venv

# 3. Restart service
sudo systemctl restart cineai-api
```

### Issue: Can't access website

```bash
# Check Nginx status
sudo systemctl status nginx

# Test Nginx config
sudo nginx -t

# Check firewall
sudo ufw status

# Restart Nginx
sudo systemctl restart nginx
```

### Issue: Video upload fails

```bash
# Check disk space
df -h

# Check uploads directory
ls -la ~/CINEAI/backend/uploads/

# Check Nginx error log
sudo tail -f /var/log/nginx/error.log
```

### Issue: SSL not working

```bash
# Renew certificate manually
sudo certbot renew --dry-run

# Check certificate status
sudo certbot certificates
```

---

## Maintenance

### Daily Monitoring

```bash
# Check service health
sudo systemctl status cineai-api
sudo systemctl status nginx

# Check disk space
df -h

# Check memory usage
free -h
```

### Weekly Tasks

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Check logs for errors
sudo journalctl -u cineai-api --since "1 week ago" | grep -i error
```

### Monthly Tasks

```bash
# Backup data
cd ~
tar -czf cineai-backup-$(date +%Y%m%d).tar.gz \
    CINEAI/backend/uploads \
    CINEAI/backend/vector_databases \
    CINEAI/backend/analysis_output

# Clean old frames
find ~/CINEAI/backend/frames -type f -mtime +7 -delete
```

---

## Cost Estimate

**VM (e2-standard-4):** ~$120/month
- 4 vCPUs
- 16 GB RAM
- 100 GB disk

**Total:** ~$120/month + Gemini API costs

---

## Final Checklist

- [ ] VM created and accessible
- [ ] Software installed (Python, Node, Nginx, FFmpeg)
- [ ] Backend deployed and running
- [ ] Frontend built and served by Nginx
- [ ] Domain pointed to VM IP
- [ ] SSL certificate installed
- [ ] Video upload tested
- [ ] Video processing tested
- [ ] All three roles tested (Actor, Director, Producer)

---

## 🎉 You're Done!

Your CINEAI app is now running on:
- **HTTP:** http://your-domain.com
- **HTTPS:** https://your-domain.com

Enjoy! 🚀
