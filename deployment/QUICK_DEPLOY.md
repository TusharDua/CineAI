# 🚀 CINEAI Quick Deploy - cineagents.in

Copy and paste these commands in order!

---

## 1️⃣ Build Frontend (Local Machine)

```bash
cd ~/Documents/CINEAI/frontend
echo "VITE_API_URL=https://cineagents.in/api" > .env.production
npm install
npm run build
```

---

## 2️⃣ Create VM

```bash
export PROJECT_ID="your-gcp-project-id"  # CHANGE THIS!
export ZONE="us-central1-a"

gcloud config set project $PROJECT_ID

gcloud compute instances create cineai-vm \
    --zone=$ZONE --machine-type=e2-standard-4 \
    --boot-disk-size=100GB --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud --tags=http-server,https-server

gcloud compute firewall-rules create allow-http --allow tcp:80,tcp:443 --target-tags http-server
gcloud compute firewall-rules create allow-api --allow tcp:8000 --target-tags http-server

# Get VM IP - SAVE THIS!
gcloud compute instances describe cineai-vm --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

**📝 Copy the IP!**

---

## 3️⃣ Setup GoDaddy DNS

**Go to:** https://dcc.godaddy.com/

**Add A Records for cineagents.in:**
- Type: `A`, Name: `@`, Value: `YOUR_VM_IP`, TTL: `600`
- Type: `A`, Name: `www`, Value: `YOUR_VM_IP`, TTL: `600`

---

## 4️⃣ Upload Code

```bash
gcloud compute scp --recurse ~/Documents/CINEAI cineai-vm:~ --zone=us-central1-a
```

---

## 5️⃣ SSH to VM

```bash
gcloud compute ssh cineai-vm --zone=us-central1-a
```

**⬇️ Everything below runs ON THE VM ⬇️**

---

## 6️⃣ Install Software

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev nginx ffmpeg git curl
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## 7️⃣ Setup Backend

```bash
cd ~/CINEAI/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Add your Gemini API key here! ⬇️
echo "GEMINI_API_KEY=your_actual_key_here" > .env
```

---

## 8️⃣ Start Backend Service

```bash
USERNAME=$(whoami)

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

sudo systemctl daemon-reload
sudo systemctl enable cineai-api
sudo systemctl start cineai-api
sudo systemctl status cineai-api  # Should be green "active"
```

---

## 9️⃣ Setup Nginx

```bash
USERNAME=$(whoami)

sudo tee /etc/nginx/sites-available/cineai > /dev/null <<EOF
server {
    listen 80;
    server_name cineagents.in www.cineagents.in;

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
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location /uploads/ {
        alias /home/$USERNAME/CINEAI/backend/uploads/;
        expires 7d;
    }

    client_max_body_size 2G;
}
EOF

sudo ln -s /etc/nginx/sites-available/cineai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔟 Install SSL (Wait 10 min after DNS setup)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cineagents.in -d www.cineagents.in
```

**Prompts:**
1. Email: `your@email.com`
2. Agree: `Y`
3. Share email: `N`
4. Redirect: `2`

---

## ✅ Test

```bash
curl http://localhost:8000/health
```

**Browser:** https://cineagents.in

---

## 🔧 Useful Commands

```bash
# Restart backend
sudo systemctl restart cineai-api

# View logs
sudo journalctl -u cineai-api -f

# Check status
sudo systemctl status cineai-api
sudo systemctl status nginx
```

---

## 🎉 Done!

**Your app:** https://cineagents.in

**Need details?** See `DEPLOY_CINEAGENTS_IN.md`
