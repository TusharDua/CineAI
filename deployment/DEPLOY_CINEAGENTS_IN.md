# CINEAI Deployment for cineagents.in - Ready to Copy & Paste

This guide is customized for your domain: **cineagents.in**

---

## 📋 Pre-Deployment Checklist

Before starting, make sure you have:
- ✅ Your Gemini API key
- ✅ GCP project created
- ✅ `gcloud` CLI installed and authenticated
- ✅ Access to GoDaddy DNS for cineagents.in

---

## Step 1: Build React Frontend (On Your Local Machine)

```bash
# Navigate to frontend
cd ~/Documents/CINEAI/frontend

# Create production environment file with YOUR domain
cat > .env.production << EOF
VITE_API_URL=https://cineagents.in/api
EOF

# Install dependencies (if not already done)
npm install

# Build for production
npm run build
```

**✅ This creates a `dist` folder with production-ready files**

---

## Step 2: Create GCP VM

```bash
# Set your project ID (replace with your actual project ID)
export PROJECT_ID="your-gcp-project-id"
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

# Get VM's external IP - SAVE THIS!
gcloud compute instances describe cineai-vm \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

**📝 COPY THE IP ADDRESS!** You'll need it for GoDaddy DNS.

---

## Step 3: Upload Code to VM

```bash
# Upload your entire CINEAI folder to VM
gcloud compute scp --recurse ~/Documents/CINEAI cineai-vm:~ --zone=$ZONE
```

---

## Step 4: Setup GoDaddy DNS (Do this NOW while software installs)

1. Go to: https://dcc.godaddy.com/
2. Login to your account
3. Find **cineagents.in** → Click **DNS**
4. Add/Update these records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_VM_IP | 600 |
| A | www | YOUR_VM_IP | 600 |

**Example:**
- Type: `A`
- Name: `@`
- Value: `34.123.45.67` (your actual VM IP)
- TTL: `600`

**Wait 5-10 minutes for DNS to propagate**

---

## Step 5: SSH into VM

```bash
gcloud compute ssh cineai-vm --zone=$ZONE
```

**From now on, all commands run on the VM (unless specified otherwise)**

---

## Step 6: Install Software on VM

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.11
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# Install other dependencies
sudo apt-get install -y nginx ffmpeg git curl

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installations
python3.11 --version
node --version
nginx -v
```

---

## Step 7: Setup Backend

```bash
cd ~/CINEAI/backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Create .env file with your Gemini API key
cat > .env << EOF
GEMINI_API_KEY=your_actual_gemini_api_key_here
EOF
```

**⚠️ IMPORTANT:** Replace `your_actual_gemini_api_key_here` with your real Gemini API key!

---

## Step 8: Create Backend Service

```bash
# Get your username (will be used in service file)
USERNAME=$(whoami)

# Create systemd service file
sudo tee /etc/systemd/system/cineai-api.service > /dev/null <<EOF
[Unit]
Description=CINEAI API Service
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=/home/$USERNAME/CINEAI/backend
Environment="PATH=/home/$USERNAME/CINEAI/backend/venv/bin"
ExecStart=/home/$USERNAME/CINEAI/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable cineai-api

# Start service
sudo systemctl start cineai-api

# Check status (should see "active (running)" in green)
sudo systemctl status cineai-api
```

Press `q` to exit status view.

---

## Step 9: Setup Nginx

```bash
# Get username
USERNAME=$(whoami)

# Create Nginx configuration for cineagents.in
sudo tee /etc/nginx/sites-available/cineai > /dev/null <<EOF
server {
    listen 80;
    server_name cineagents.in www.cineagents.in;

    # Frontend - Serve React build
    location / {
        root /home/$USERNAME/CINEAI/frontend/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # API - Proxy to FastAPI backend
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Allow long-running requests (video processing)
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_connect_timeout 3600s;
    }

    # Serve uploaded videos
    location /uploads/ {
        alias /home/$USERNAME/CINEAI/backend/uploads/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Allow large file uploads (2GB max)
    client_max_body_size 2G;
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/cineai /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# If test passes, restart Nginx
sudo systemctl restart nginx

# Check Nginx status
sudo systemctl status nginx
```

---

## Step 10: Test Without SSL (HTTP)

```bash
# Test backend API
curl http://localhost:8000/health

# Should return: {"status":"healthy"}
```

**Open browser:** http://cineagents.in

If DNS has propagated, you should see your app (without HTTPS yet).

---

## Step 11: Install SSL Certificate (HTTPS)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate for cineagents.in
sudo certbot --nginx -d cineagents.in -d www.cineagents.in
```

**Follow the prompts:**
1. Enter your email address
2. Agree to terms of service: **Y**
3. Share email with EFF: **N** (optional)
4. Redirect HTTP to HTTPS: **2** (Yes, recommended)

**✅ Done!** Certbot will:
- Get free SSL certificate
- Configure Nginx for HTTPS
- Set up auto-renewal

---

## Step 12: Test Everything

### Test in Browser

1. Open: **https://cineagents.in**
2. You should see CINEAI app with HTTPS 🔒
3. Try uploading a video
4. Test all three roles: Actor, Director, Producer

### Check Logs

```bash
# Backend logs (real-time)
sudo journalctl -u cineai-api -f

# Press Ctrl+C to stop

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

---

## 🎉 Success! Your App is Live at:

- **🌐 Website:** https://cineagents.in
- **🔒 SSL:** Automatic with Let's Encrypt
- **✅ No Timeouts:** Process 20+ minute videos

---

## Common Commands for Daily Use

### Restart Services

```bash
# Restart backend
sudo systemctl restart cineai-api

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status cineai-api
sudo systemctl status nginx
```

### View Logs

```bash
# Backend logs (last 50 lines)
sudo journalctl -u cineai-api -n 50

# Backend logs (real-time)
sudo journalctl -u cineai-api -f

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log
```

### Update Code

```bash
# From your local machine, upload new code
gcloud compute scp --recurse ~/Documents/CINEAI cineai-vm:~ --zone=us-central1-a

# SSH to VM
gcloud compute ssh cineai-vm --zone=us-central1-a

# Update backend
cd ~/CINEAI/backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart cineai-api

# Update frontend (if you rebuilt locally)
# Just upload and it's done! Nginx serves the new dist folder
```

### Check Disk Space

```bash
df -h

# Clean old frames (older than 7 days)
find ~/CINEAI/backend/frames -type f -mtime +7 -delete
```

---

## Troubleshooting

### Can't access cineagents.in

```bash
# Check DNS propagation
nslookup cineagents.in

# Check Nginx
sudo systemctl status nginx
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Backend not working

```bash
# Check status
sudo systemctl status cineai-api

# View errors
sudo journalctl -u cineai-api -n 100

# Restart
sudo systemctl restart cineai-api
```

### Video upload fails

```bash
# Check disk space
df -h

# Check Nginx error log
sudo tail -f /var/log/nginx/error.log

# Check uploads directory
ls -la ~/CINEAI/backend/uploads/
```

### SSL certificate issues

```bash
# Check certificate status
sudo certbot certificates

# Renew manually (dry run)
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal
```

---

## 💰 Monthly Cost

- **VM (e2-standard-4):** ~$120/month
- **100GB Disk:** Included
- **SSL Certificate:** FREE (Let's Encrypt)
- **Bandwidth:** Included (first 1TB)
- **Gemini API:** Separate billing

**Total:** ~$120-150/month

---

## 🔒 Security Checklist

After deployment, improve security:

```bash
# Setup firewall
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Disable root SSH
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd

# Enable automatic security updates
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 📞 Need Help?

**Check these in order:**
1. Backend logs: `sudo journalctl -u cineai-api -f`
2. Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. DNS: https://dnschecker.org (check cineagents.in)
4. SSL: https://www.ssllabs.com/ssltest/analyze.html?d=cineagents.in

---

## ✅ Final Checklist

- [ ] VM created and running
- [ ] Code uploaded to VM
- [ ] Backend service running (`systemctl status cineai-api`)
- [ ] Nginx running (`systemctl status nginx`)
- [ ] DNS pointing to VM (cineagents.in → VM IP)
- [ ] SSL certificate installed (https:// works)
- [ ] Can access https://cineagents.in
- [ ] Video upload works
- [ ] Video processing works
- [ ] All 3 roles work (Actor, Director, Producer)

---

## 🎊 Congratulations!

Your CINEAI app is now live at **https://cineagents.in**

Enjoy! 🚀🎬
