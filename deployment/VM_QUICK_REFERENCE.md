# CINEAI VM Deployment - Quick Reference

## 🚀 Step-by-Step Checklist

Copy and paste these commands in order:

---

### 1️⃣ Create VM (5 min)

```bash
export PROJECT_ID="your-project-id"
export ZONE="us-central1-a"

gcloud config set project $PROJECT_ID

gcloud compute instances create cineai-vm \
    --zone=$ZONE \
    --machine-type=e2-standard-4 \
    --boot-disk-size=100GB \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server,https-server

gcloud compute firewall-rules create allow-http --allow tcp:80,tcp:443 --target-tags http-server
gcloud compute firewall-rules create allow-api --allow tcp:8000 --target-tags http-server

# Get VM IP (save this!)
gcloud compute instances describe cineai-vm --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

**📝 Save the IP address!**

---

### 2️⃣ SSH into VM

```bash
gcloud compute ssh cineai-vm --zone=$ZONE
```

---

### 3️⃣ Install Software (10 min)

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.11
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# Install dependencies
sudo apt-get install -y nginx ffmpeg git curl

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

### 4️⃣ Upload Your Code (5 min)

**From your LOCAL machine** (new terminal):

```bash
cd ~/Documents
gcloud compute scp --recurse CINEAI cineai-vm:~ --zone=us-central1-a
```

---

### 5️⃣ Setup Backend (10 min)

**Back on VM:**

```bash
cd ~/CINEAI/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env
echo "GEMINI_API_KEY=your_actual_key_here" > .env
```

---

### 6️⃣ Build Frontend (5 min)

```bash
cd ~/CINEAI/frontend

# Update API URL
echo "VITE_API_URL=http://your-domain.com/api" > .env.production

npm install
npm run build
```

---

### 7️⃣ Create Backend Service (5 min)

```bash
# Get your username
USERNAME=$(whoami)

# Create service file
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

# Start service
sudo systemctl daemon-reload
sudo systemctl enable cineai-api
sudo systemctl start cineai-api
sudo systemctl status cineai-api
```

---

### 8️⃣ Setup Nginx (5 min)

```bash
# Get username
USERNAME=$(whoami)

# Your domain (CHANGE THIS!)
DOMAIN="your-domain.com"

# Create Nginx config
sudo tee /etc/nginx/sites-available/cineai > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        root /home/$USERNAME/CINEAI/frontend/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

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
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_connect_timeout 3600s;
    }

    location /uploads/ {
        alias /home/$USERNAME/CINEAI/backend/uploads/;
        expires 7d;
    }

    client_max_body_size 2G;
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/cineai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

### 9️⃣ Setup GoDaddy DNS (5 min)

1. Go to https://godaddy.com → Login
2. **My Products** → **DNS** for your domain
3. Add these records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_VM_IP | 600 |
| A | www | YOUR_VM_IP | 600 |

**Wait 10 minutes for DNS to propagate**

---

### 🔟 Setup SSL (5 min)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow prompts:
1. Enter email
2. Agree (Y)
3. No to sharing email
4. Redirect HTTP to HTTPS: **2** (Yes)

---

## ✅ Test Everything

```bash
# Test backend
curl http://localhost:8000/health

# Check services
sudo systemctl status cineai-api
sudo systemctl status nginx

# View logs
sudo journalctl -u cineai-api -f
```

**Open browser:** https://your-domain.com

---

## 🔧 Common Commands

```bash
# Restart backend
sudo systemctl restart cineai-api

# Restart Nginx
sudo systemctl restart nginx

# View backend logs
sudo journalctl -u cineai-api -f

# View Nginx logs
sudo tail -f /var/log/nginx/error.log

# Check disk space
df -h
```

---

## 🔄 Update Code

```bash
cd ~/CINEAI
git pull  # or upload new files

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

---

## 🆘 Troubleshooting

**Backend won't start?**
```bash
sudo journalctl -u cineai-api -n 50
# Check .env file exists
cat ~/CINEAI/backend/.env
```

**Can't access website?**
```bash
sudo nginx -t
sudo systemctl restart nginx
sudo tail -f /var/log/nginx/error.log
```

**Out of disk space?**
```bash
df -h
# Clean old frames
find ~/CINEAI/backend/frames -type f -mtime +7 -delete
```

---

## 📊 Estimated Times

| Step | Time |
|------|------|
| Create VM | 5 min |
| Install software | 10 min |
| Upload code | 5 min |
| Setup backend | 10 min |
| Build frontend | 5 min |
| Configure services | 10 min |
| Setup DNS | 5 min |
| Setup SSL | 5 min |
| **Total** | **~60 min** |

---

## 💰 Monthly Cost

- **VM (e2-standard-4):** ~$120/month
- **Disk (100GB):** Included
- **Bandwidth:** Included (up to 1TB)
- **Gemini API:** Separate billing

**Total:** ~$120-150/month

---

## 🎯 Success Checklist

- [ ] VM created
- [ ] Software installed
- [ ] Code uploaded
- [ ] Backend running
- [ ] Frontend built
- [ ] Nginx configured
- [ ] Domain pointed to VM
- [ ] SSL working (https://)
- [ ] Video upload works
- [ ] Video processing works
- [ ] All 3 roles work (Actor, Director, Producer)

---

## 🔗 Useful Links

- GCP Console: https://console.cloud.google.com
- GoDaddy DNS: https://dcc.godaddy.com/manage/dns
- Check DNS: https://dnschecker.org
- SSL Check: https://www.ssllabs.com/ssltest/

---

**Need detailed explanations?** See `VM_SIMPLE_GUIDE.md`
