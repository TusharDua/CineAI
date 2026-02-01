# Docker setup and run (macOS)

## Step 1: Install Docker on your Mac

### Option A: Docker Desktop (recommended)

1. **Download Docker Desktop**
   - Go to: https://www.docker.com/products/docker-desktop/
   - Click **Download for Mac** (choose **Apple Chip** if you have M1/M2/M3, else **Intel**).

2. **Install**
   - Open the downloaded `.dmg` and drag **Docker** to Applications.
   - Open **Docker** from Applications.
   - Accept the terms and finish the setup (you may need to enter your Mac password).
   - Wait until the whale icon in the menu bar shows Docker is running.

3. **Verify**
   - Open **Terminal** and run:
   ```bash
   docker --version
   ```
   - You should see something like `Docker version 24.x.x`.

### Option B: Homebrew (if you use Homebrew)

```bash
brew install --cask docker
```

Then open **Docker** from Applications and wait until it’s running. Check with `docker --version`.

---

## Step 2: Build and run CINEAI

In Terminal, run these from your project folder:

```bash
# Go to project root
cd /Users/prasad/Documents/CINEAI

# Build the image (first time may take a few minutes)
docker build -t cineai .

# Run the app (port 8080)
docker run -p 8080:8080 --env-file backend/.env cineai
```

Then open in your browser: **http://localhost:8080**

---

## Useful commands

| Action              | Command                                      |
|---------------------|----------------------------------------------|
| Stop the app        | Press `Ctrl+C` in the terminal running Docker |
| Run in background   | `docker run -d -p 8080:8080 --env-file backend/.env --name cineai-app cineai` |
| Stop background app | `docker stop cineai-app`                     |
| View running        | `docker ps`                                  |
