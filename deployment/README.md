# CINEAI - GCP Deployment Guide

## 🚀 Start Here

**New to deployment?** Read `QUICKSTART.md` first!

**Already decided?** Jump to your deployment method below.

---

## 📖 Documentation

| File | Purpose | Read If... |
|------|---------|-----------|
| **[QUICKSTART.md](./QUICKSTART.md)** | Overview & getting started | You're new to this |
| **[WHICH_TO_CHOOSE.md](./WHICH_TO_CHOOSE.md)** | Compare Cloud Run vs VM | You're deciding which option |
| **[README.md](./README.md)** | Cloud Run deployment | You chose Cloud Run |
| **[VM_DEPLOYMENT.md](./VM_DEPLOYMENT.md)** | VM deployment | You chose VM |
| **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** | Fix common issues | Something went wrong |

---

## 🎯 Two Deployment Options

### Option 1: Cloud Run + Cloud Storage (Recommended)

**Best for:** Auto-scaling, variable traffic, modern architecture

**Pros:**
- ✅ Handles 20+ min processing with Cloud Run Jobs
- ✅ Auto-scales based on demand
- ✅ Pay only for what you use
- ✅ No server management

**Deploy:**
```bash
export GCP_PROJECT_ID="your-project-id"
export GEMINI_API_KEY="your-key"
cd deployment
./deploy.sh
```

**Cost:** $5-200/month (depends on usage)

---

### Option 2: Compute Engine VM

**Best for:** Simplicity, heavy regular usage, full control

**Pros:**
- ✅ No timeout limits
- ✅ Simple to understand
- ✅ Easy debugging (SSH access)
- ✅ Predictable costs

**Deploy:** Follow `VM_DEPLOYMENT.md`

**Cost:** $50-100/month (fixed)
