# GCP Deployment Troubleshooting Guide

## Common Issues and Solutions

### 1. Cloud Run: Request Timeout (after 60 seconds)

**Problem:** Video processing takes 20+ minutes but Cloud Run has 60s timeout

**Solution:** Use async processing with Cloud Run Jobs

```python
# In main.py - Make /analyze-video async
@app.post("/analyze-video")
async def analyze_video_endpoint(video_id: str):
    # Create Cloud Run Job instead of processing directly
    job_name = f"process-video-{video_id}"
    
    # Submit job
    client = run_v2.JobsClient()
    job = run_v2.Job(
        name=f"projects/{PROJECT_ID}/locations/{REGION}/jobs/{job_name}",
        template=run_v2.ExecutionTemplate(
            template=run_v2.TaskTemplate(
                containers=[run_v2.Container(
                    image=f"gcr.io/{PROJECT_ID}/cineai-worker:latest",
                    env=[
                        run_v2.EnvVar(name="VIDEO_ID", value=video_id),
                        run_v2.EnvVar(name="GEMINI_API_KEY", value=GEMINI_API_KEY),
                    ]
                )],
                max_retries=2,
                timeout="7200s"  # 2 hours
            )
        )
    )
    
    client.run_job(name=job.name)
    return {"status": "processing", "job_name": job_name}
```

---

### 2. Out of Memory Error

**Symptoms:**
```
ERROR: Container killed due to memory limit
```

**Solutions:**

**For Cloud Run:**
```bash
gcloud run deploy cineai-api \
    --memory 8Gi \  # Increase from 4Gi to 8Gi
    --cpu 4         # Also increase CPU
```

**For VM:**
```bash
# Upgrade VM
gcloud compute instances stop cineai-vm --zone=us-central1-a
gcloud compute instances set-machine-type cineai-vm \
    --machine-type=e2-standard-8 \
    --zone=us-central1-a
gcloud compute instances start cineai-vm --zone=us-central1-a
```

---

### 3. Cloud Storage Permission Denied

**Symptoms:**
```
google.api_core.exceptions.Forbidden: 403 Permission Denied
```

**Solution:**
```bash
# Grant storage permissions to service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cineai-service@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Make sure Cloud Run uses this service account
gcloud run services update cineai-api \
    --service-account=cineai-service@${PROJECT_ID}.iam.gserviceaccount.com \
    --region=us-central1
```

---

### 4. Gemini API Rate Limiting

**Symptoms:**
```
429 Too Many Requests
RESOURCE_EXHAUSTED
```

**Solution:** Already implemented in code with exponential backoff, but you can:

1. **Request quota increase:**
   - Go to Google Cloud Console → APIs & Services → Gemini API
   - Request quota increase

2. **Reduce concurrent processing:**
```bash
# Update Cloud Tasks queue
gcloud tasks queues update video-processing-queue \
    --location=us-central1 \
    --max-concurrent-dispatches=1  # Process one at a time
```

---

### 5. Frontend Can't Connect to Backend

**Symptoms:**
- CORS errors
- Network errors

**Solution:**

**Update backend CORS settings:**
```python
# In main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Update frontend API URL:**
```bash
# In frontend/.env.production
VITE_API_URL=https://your-api-url.run.app
```

---

### 6. Video Upload Fails (File Too Large)

**Symptoms:**
```
413 Request Entity Too Large
```

**Solutions:**

**For Cloud Run:**
```bash
# Cloud Run has 32MB limit for direct uploads
# Use signed URLs for large files instead

# In main.py
from google.cloud import storage

@app.post("/get-upload-url")
async def get_upload_url(filename: str):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"uploads/{filename}")
    
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(hours=1),
        method="PUT",
        content_type="video/mp4"
    )
    
    return {"upload_url": url, "video_id": filename}
```

**For VM:**
```nginx
# In /etc/nginx/sites-available/cineai
client_max_body_size 2G;  # Increase from 500M
```

---

### 7. Cold Start Too Slow

**Symptoms:**
- First request takes 30+ seconds

**Solutions:**

**For Cloud Run:**
```bash
# Set minimum instances
gcloud run services update cineai-api \
    --min-instances=1 \
    --region=us-central1

# Note: This costs ~$10/month for always-on instance
```

**Optimize Docker image:**
```dockerfile
# Use slim images
FROM python:3.11-slim

# Install only necessary packages
RUN pip install --no-cache-dir -r requirements.txt
```

---

### 8. Database/Vector Store Not Persisting

**Symptoms:**
- Data disappears after container restart

**Solution:**

**For Cloud Run - Use Cloud Storage:**
```python
# Modify services to use Cloud Storage
from google.cloud import storage

def save_vector_db(video_id: str, index):
    # Save to Cloud Storage instead of local disk
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    
    # Save FAISS index
    faiss.write_index(index, f"/tmp/{video_id}.index")
    blob = bucket.blob(f"vector_databases/{video_id}.index")
    blob.upload_from_filename(f"/tmp/{video_id}.index")
```

---

### 9. Can't SSH into VM

**Symptoms:**
```
Permission denied (publickey)
```

**Solution:**
```bash
# Add SSH keys
gcloud compute config-ssh

# Or use browser SSH
gcloud compute ssh cineai-vm \
    --zone=us-central1-a \
    --tunnel-through-iap
```

---

### 10. High Costs

**Check what's expensive:**
```bash
# Export billing data
gcloud billing accounts list
gcloud billing projects describe $PROJECT_ID

# Check Cloud Run costs
gcloud run services list --format="table(name, status.url)" --region=us-central1

# Check most expensive SKUs in console:
# https://console.cloud.google.com/billing/
```

**Reduce costs:**

1. **Reduce Cloud Run minimum instances:**
```bash
gcloud run services update cineai-api --min-instances=0
```

2. **Use Cloud Storage Nearline for old videos:**
```bash
gsutil lifecycle set lifecycle.json gs://bucket-name
```

3. **Delete old vector databases:**
```bash
# Add cleanup script
gsutil -m rm gs://bucket-name/vector_databases/old-video-*.index
```

---

## Monitoring and Debugging

### View Logs

**Cloud Run:**
```bash
# Real-time logs
gcloud logging tail "resource.type=cloud_run_revision" --format=json

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit 50
```

**VM:**
```bash
# SSH into VM
gcloud compute ssh cineai-vm --zone=us-central1-a

# View logs
sudo journalctl -u cineai-api -f
sudo tail -f /var/log/nginx/error.log
```

### Check Service Status

**Cloud Run:**
```bash
gcloud run services describe cineai-api \
    --region=us-central1 \
    --format="table(status.conditions)"
```

**VM:**
```bash
gcloud compute ssh cineai-vm --zone=us-central1-a --command="systemctl status cineai-api"
```

### Performance Monitoring

**Enable Cloud Monitoring:**
```bash
# Already enabled with Cloud Run by default
# View in console:
# https://console.cloud.google.com/monitoring
```

---

## Getting Help

1. **Check logs first** - 90% of issues are visible in logs
2. **Check GCP Status** - https://status.cloud.google.com/
3. **Stack Overflow** - Tag with `google-cloud-run` or `google-compute-engine`
4. **GCP Support** - If you have a support plan

## Quick Health Check

```bash
# Test API
curl https://your-api-url.run.app/health

# Test storage
gsutil ls gs://your-bucket-name/

# Test service account
gcloud iam service-accounts get-iam-policy cineai-service@${PROJECT_ID}.iam.gserviceaccount.com
```
