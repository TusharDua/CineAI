# 🚀 CINEAI GCP Deployment - Complete Guide

## 📋 What's Included

I've created a complete deployment solution for your CINEAI application on Google Cloud Platform with **two deployment options**:

### Option 1: Cloud Run + Cloud Storage (Recommended) ☁️
Modern, serverless architecture that auto-scales and handles your 20+ minute processing

### Option 2: Compute Engine VM 🖥️
Traditional server setup - simple and predictable

---

## 📁 Files Created

```
deployment/
├── README.md                    # Main deployment guide
├── WHICH_TO_CHOOSE.md          # Decision guide (start here!)
├── VM_DEPLOYMENT.md            # VM deployment steps
├── TROUBLESHOOTING.md          # Common issues & solutions
└── deploy.sh                    # Automated deployment script

backend/
├── Dockerfile                   # API container
├── Dockerfile.worker            # Processing worker container
├── worker.py                    # Long-running video processing
├── storage_adapter.py           # Cloud Storage integration
└── cloudbuild.yaml             # Automated build config
```

---

## 🎯 Quick Start

### Step 1: Choose Your Deployment

**Read this first:** `deployment/WHICH_TO_CHOOSE.md`

**TL;DR:**
- **Variable traffic or starting out?** → Cloud Run
- **Heavy regular usage or want simplicity?** → VM

---

### Step 2A: Deploy with Cloud Run (Automated)

```bash
# Set your credentials
export GCP_PROJECT_ID="your-project-id"
export GEMINI_API_KEY="your-gemini-api-key"
export GCP_REGION="us-central1"

# Run deployment script
cd deployment
chmod +x deploy.sh
./deploy.sh
```

**Time:** 15-20 minutes
**Result:** Fully deployed application with auto-scaling

---

### Step 2B: Deploy with VM (Manual but Simple)

```bash
# Create VM
gcloud compute instances create cineai-vm \
    --machine-type=e2-standard-4 \
    --boot-disk-size=100GB \
    --zone=us-central1-a

# Follow detailed steps in:
```
See: `deployment/VM_DEPLOYMENT.md`

**Time:** 30-40 minutes
**Result:** Traditional server you can SSH into

---

## 🔧 How It Handles 20+ Minute Processing

### Cloud Run Solution:
1. **API receives video** (fast response in <1s)
2. **Creates Cloud Run Job** (async processing)
3. **Worker processes video** (can run 24 hours!)
4. **Updates status** (check via API)
5. **Frontend polls** for completion

**Key files:**
- `backend/worker.py` - Processing worker
- `backend/Dockerfile.worker` - Worker container

### VM Solution:
- No timeout limits!
- Processes run directly on server
- Simple but works perfectly

---

## 💰 Cost Comparison

### Low Usage (10 videos/month):
- **Cloud Run:** ~$6/month ✅ Winner
- **VM:** ~$50/month

### Medium Usage (100 videos/month):
- **Cloud Run:** ~$42/month ✅ Winner
- **VM:** ~$60/month

### Heavy Usage (500 videos/month):
- **Cloud Run:** ~$200/month
- **VM:** ~$120/month ✅ Winner

**Plus:** Gemini API costs (separate billing)

---

## 🏗️ Architecture Overview

### Cloud Run Architecture:
```
User → Frontend (Cloud Run)
          ↓
      API (Cloud Run) → Uploads video to Cloud Storage
          ↓
    Cloud Run Job → Processes video (20+ mins)
          ↓
    Cloud Storage → Stores results
          ↓
      API → Returns results
```

**Advantages:**
✅ Auto-scales from 0 to 100+ instances
✅ Pay only for actual processing time
✅ No server management
✅ Handles long processing (up to 24 hours)
✅ Global CDN included

### VM Architecture:
```
User → Nginx (on VM)
          ↓
      FastAPI (on VM) → Process video
          ↓
    Local Disk → Store results
```

**Advantages:**
✅ Simple to understand
✅ Easy to debug (SSH access)
✅ No cold starts
✅ Predictable costs

---

## 🔍 Key Features Implemented

### For Cloud Run:
1. **Storage Adapter** (`storage_adapter.py`)
   - Abstracts local vs Cloud Storage
   - Works in both dev and production

2. **Worker System** (`worker.py`)
   - Handles long processing
   - Runs as Cloud Run Job
   - Auto-retries on failure

3. **Async Processing**
   - API responds immediately
   - Processing happens in background
   - Status polling endpoint

### For VM:
1. **Systemd Service**
   - Auto-starts on boot
   - Restarts on failure
   - Logs to journalctl

2. **Nginx Proxy**
   - Serves frontend
   - Proxies API requests
   - Handles large file uploads

---

## 📚 Documentation Guide

**Start here:**
1. Read `WHICH_TO_CHOOSE.md` - Decide which option
2. Follow `README.md` (Cloud Run) OR `VM_DEPLOYMENT.md` (VM)
3. Keep `TROUBLESHOOTING.md` handy for issues

**Quick commands:**
```bash
# Health check
curl https://your-api-url/health

# View logs (Cloud Run)
gcloud logging tail "resource.type=cloud_run_revision"

# SSH to VM
gcloud compute ssh cineai-vm --zone=us-central1-a
```

---

## 🎓 What You Need to Know

### Prerequisites:
- Google Cloud account with billing enabled
- `gcloud` CLI installed
- Basic terminal knowledge

### For Cloud Run:
- Docker basics (helpful but not required)
- Understanding of async processing

### For VM:
- Linux server basics
- SSH and systemd knowledge

---

## 🚨 Common Issues & Solutions

### "Request timeout after 60 seconds"
→ **Solution:** Already handled! Uses Cloud Run Jobs for long processing

### "Out of memory"
→ **Solution:** Increase memory in Cloud Run config or upgrade VM

### "Permission denied accessing Cloud Storage"
→ **Solution:** Grant storage.objectAdmin role to service account

### "High costs"
→ **Solution:** Set min-instances to 0, or switch to VM

**Full guide:** `TROUBLESHOOTING.md`

---

## 🎯 Deployment Checklist

### Before Deployment:
- [ ] GCP project created and billing enabled
- [ ] `gcloud` CLI installed and authenticated
- [ ] GEMINI_API_KEY obtained
- [ ] Decided between Cloud Run or VM

### After Deployment:
- [ ] Test video upload
- [ ] Test video processing (20+ mins)
- [ ] Test all three roles (Actor, Director, Producer)
- [ ] Setup monitoring alerts
- [ ] Configure backups (if using VM)

---

## 📞 Need Help?

1. **Check logs first** - Most issues show up there
2. **Read TROUBLESHOOTING.md** - Common issues covered
3. **GCP Console** - https://console.cloud.google.com
4. **Stack Overflow** - Tag with `google-cloud-run` or `google-compute-engine`

---

## 🎉 Next Steps

After deployment:

1. **Test thoroughly** - Upload a video and verify processing
2. **Monitor costs** - Check GCP billing dashboard
3. **Setup alerts** - Get notified of errors
4. **Configure domain** - Point your domain to Cloud Run/VM
5. **Add SSL** - Use Cloud Load Balancer or Certbot

**Enjoy your deployed CINEAI app!** 🎬✨
