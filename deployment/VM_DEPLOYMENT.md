# Simple VM Deployment Guide

If you prefer a simpler, more traditional deployment, use a single Compute Engine VM.

## Advantages
- ✅ No timeout concerns
- ✅ Simple architecture
- ✅ Everything in one place
- ✅ Predictable costs
- ✅ Easy debugging

## Cost: ~$50-100/month for an e2-medium VM with 100GB disk

---

## Deployment Steps

### 1. Create VM

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export ZONE="us-central1-a"

gcloud compute instances create cineai-vm \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-standard-4 \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-balanced \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server,https-server

# Allow HTTP/HTTPS traffic
gcloud compute firewall-rules create allow-http \
    --allow tcp:80,tcp:443 \
    --target-tags http-server

gcloud compute firewall-rules create allow-api \
    --allow tcp:8000 \
    --target-tags http-server
```

### 2. SSH into VM

```bash
gcloud compute ssh cineai-vm --zone=$ZONE
```

### 3. Install Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python, Node.js, Nginx, FFmpeg
sudo apt-get install -y python3.11 python3-pip nodejs npm nginx ffmpeg git

# Install Docker (optional, for easier management)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 4. Clone and Setup Application

```bash
# Clone your repository
cd ~
git clone https://github.com/yourusername/cineai.git
cd cineai

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key_here
EOF

# Setup frontend
cd ../frontend
npm install
npm run build
```

### 5. Setup Systemd Service for Backend

```bash
sudo nano /etc/systemd/system/cineai-api.service
```

Add:

```ini
[Unit]
Description=CINEAI API Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/cineai/backend
Environment="PATH=/home/your-username/cineai/backend/venv/bin"
ExecStart=/home/your-username/cineai/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cineai-api
sudo systemctl start cineai-api
sudo systemctl status cineai-api
```

### 6. Setup Nginx

```bash
sudo nano /etc/nginx/sites-available/cineai
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Or use VM's external IP

    # Frontend
    location / {
        root /home/your-username/cineai/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
        
        # Important: Allow long-running requests
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Serve uploaded videos
    location /uploads/ {
        alias /home/your-username/cineai/backend/uploads/;
        expires 7d;
    }

    client_max_body_size 500M;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/cineai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Setup SSL (Optional but Recommended)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is setup automatically
```

### 8. Setup Automatic Backups

```bash
# Create backup script
cat > ~/backup-cineai.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/$(whoami)/backups"
mkdir -p $BACKUP_DIR

# Backup vector databases and uploads
tar -czf $BACKUP_DIR/cineai-data-$DATE.tar.gz \
    ~/cineai/backend/uploads \
    ~/cineai/backend/vector_databases \
    ~/cineai/backend/analysis_output

# Keep only last 7 days
find $BACKUP_DIR -name "cineai-data-*.tar.gz" -mtime +7 -delete
EOF

chmod +x ~/backup-cineai.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/$(whoami)/backup-cineai.sh") | crontab -
```

### 9. Monitor and Maintain

```bash
# View API logs
sudo journalctl -u cineai-api -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Restart services if needed
sudo systemctl restart cineai-api
sudo systemctl restart nginx

# Update application
cd ~/cineai
git pull
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart cineai-api

cd ../frontend
npm install
npm run build
```

### 10. Get External IP

```bash
# From your local machine
gcloud compute instances describe cineai-vm \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

Visit: `http://YOUR_EXTERNAL_IP`

---

## Advantages of VM Approach

1. **No Timeouts**: Process videos as long as needed
2. **Simple**: Everything in one place
3. **Debugging**: Easy to SSH and check logs
4. **Persistent Storage**: No need for Cloud Storage
5. **Predictable Costs**: ~$50-100/month regardless of usage

## Disadvantages

1. Always running (costs even when idle)
2. Manual scaling (need to upgrade VM for more capacity)
3. Single point of failure
4. Need to manage backups yourself
