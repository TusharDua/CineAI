# CINEAI Architecture for cineagents.in

## 🌐 How Everything Connects

```
┌─────────────────────────────────────────────────────┐
│                    User's Browser                    │
│              (anywhere in the world)                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       │ visits https://cineagents.in
                       ↓
┌─────────────────────────────────────────────────────┐
│                  GoDaddy DNS                         │
│           A Record: cineagents.in                    │
│              Points to → VM IP                       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────┐
│              Google Cloud Platform                   │
│                  VM (cineai-vm)                      │
│              IP: 34.xxx.xxx.xxx                      │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │            Nginx (Port 80/443)              │    │
│  │         SSL Certificate (HTTPS)             │    │
│  └──────────┬──────────────────┬───────────────┘    │
│             │                  │                     │
│             │                  │                     │
│    ┌────────▼────────┐  ┌─────▼──────────┐         │
│    │   Frontend      │  │   Backend API   │         │
│    │   React Build   │  │   FastAPI       │         │
│    │   (dist/)       │  │   Port 8000     │         │
│    │                 │  │                 │         │
│    │  Static Files:  │  │  Endpoints:     │         │
│    │  - index.html   │  │  - /upload      │         │
│    │  - bundle.js    │  │  - /analyze     │         │
│    │  - styles.css   │  │  - /chat        │         │
│    └─────────────────┘  └─────┬───────────┘         │
│                                │                     │
│                                │                     │
│                         ┌──────▼──────────┐         │
│                         │  Local Storage  │         │
│                         │                 │         │
│                         │  - uploads/     │         │
│                         │  - frames/      │         │
│                         │  - vector_dbs/  │         │
│                         └─────────────────┘         │
│                                                      │
└──────────────────────────────────────────────────────┘
                       │
                       │ API calls to
                       ↓
            ┌──────────────────────┐
            │   Gemini API         │
            │  (Google AI)         │
            │  - Frame analysis    │
            │  - Embeddings        │
            │  - Answer generation │
            └──────────────────────┘
```

---

## 📊 Request Flow Examples

### Example 1: User Visits Homepage

```
1. User types: https://cineagents.in
                    ↓
2. DNS lookup: cineagents.in → 34.xxx.xxx.xxx
                    ↓
3. Request hits: VM's Nginx (Port 443)
                    ↓
4. Nginx checks: location /
                    ↓
5. Nginx serves: /home/user/CINEAI/frontend/dist/index.html
                    ↓
6. Browser loads: React app
                    ↓
7. React loaded at: https://cineagents.in ✅
```

---

### Example 2: User Uploads Video

```
1. User clicks: Upload button
                    ↓
2. React calls: https://cineagents.in/api/upload-video
                    ↓
3. DNS resolves: cineagents.in → VM IP
                    ↓
4. Nginx receives: https://cineagents.in/api/upload-video
                    ↓
5. Nginx proxies to: http://localhost:8000/upload-video
                    ↓
6. FastAPI handles: Save to /uploads/
                    ↓
7. Returns: video_id = "abc123"
                    ↓
8. React receives: video_id and displays ✅
```

---

### Example 3: Video Processing

```
1. React calls: https://cineagents.in/api/analyze-video
                    ↓
2. Nginx proxies to: localhost:8000/analyze-video
                    ↓
3. FastAPI starts: Video processing (20+ mins)
   - Extract frames → /frames/
   - Analyze with Gemini API
   - Generate embeddings
   - Build vector DB → /vector_databases/
                    ↓
4. React polls: /api/status every 5 seconds
                    ↓
5. When done: Status = "completed" ✅
```

---

### Example 4: User Asks Question

```
1. User types: "Show romantic scenes"
                    ↓
2. React calls: https://cineagents.in/api/chat
   Body: { query: "romantic scenes", role: "actor" }
                    ↓
3. Nginx proxies to: localhost:8000/chat
                    ↓
4. FastAPI:
   - Loads vector DB for "actor" role
   - Searches for similar embeddings
   - Calls Gemini API for answer
   - Returns: { answer: "...", results: [...] }
                    ↓
5. React displays: Answer + clickable timestamps ✅
```

---

## 🔑 Key Concepts

### Why Nginx?

**Without Nginx:**
```
User → FastAPI (Port 8000)
     ❌ No HTTPS
     ❌ Can't serve React files
     ❌ No caching
```

**With Nginx:**
```
User → Nginx (Port 443)
     ✅ HTTPS/SSL
     ✅ Serves React static files
     ✅ Proxies API requests to FastAPI
     ✅ Handles large uploads
     ✅ Caching for videos
```

---

### Why Build React?

**Development (npm run dev):**
```
Frontend: http://localhost:3000 (Vite dev server)
Backend:  http://localhost:8000
```

**Production (npm run build):**
```
Frontend: Static files (HTML, JS, CSS)
         → Served by Nginx
         → https://cineagents.in

Backend:  FastAPI still running
         → Accessed via /api/*
```

---

### Environment Variables

**Development (.env):**
```env
VITE_API_URL=http://localhost:8000
```
React calls: `http://localhost:8000/upload-video`

**Production (.env.production):**
```env
VITE_API_URL=https://cineagents.in/api
```
React calls: `https://cineagents.in/api/upload-video`
              ↓
         Nginx proxies to: `http://localhost:8000/upload-video`

---

## 🎯 Summary

1. **GoDaddy DNS** points `cineagents.in` → Your VM IP
2. **Nginx** receives all requests on Port 443 (HTTPS)
3. **Nginx routes:**
   - `/` → React static files (frontend)
   - `/api/*` → FastAPI backend (localhost:8000)
   - `/uploads/*` → Video files
4. **FastAPI** processes requests and talks to Gemini API
5. **Files stored** on VM's local disk

**One VM, everything connected!** 🚀
