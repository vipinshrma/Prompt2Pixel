# Manim Cursor: AI-Powered 2D Animation Studio

An interactive full-stack application that generates math and science animations using the Manim library. The LLM writes python animation scripts, and a sandboxed Docker container compiles them into playable video clips in real-time, streaming progress logs to the browser.

---

## 🛠 Prerequisites

Ensure you have the following installed on your host system:
1. **Docker Desktop** (Make sure the Docker daemon is running).
2. **Node.js 18+** (For local frontend development outside Docker, if desired).
3. **Python 3.10+** (For local editor autocompletion).
4. An **OpenAI API Key** with access to GPT-4o / GPT-4o-mini.

---

## 📁 Directory Structure

```
manim-cursor/
├── docker-compose.yml       # Configuration for multi-container services
├── README.md                # This setup guide
├── renders/                 # [HOST] Shared directory containing compiled videos
├── backend/
│   ├── main.py              # FastAPI endpoints
│   ├── Dockerfile           # Python runner image configuration
│   ├── requirements.txt     # Backend python dependencies
│   ├── .dockerignore        # Files ignored in docker build context
│   └── services/
│       ├── compiler.py      # Docker compilation & streaming logic
│       └── openai_service.py # OpenAI prompt orchestration
└── frontend/
    ├── src/                 # Next.js App Router codebase
    ├── Dockerfile           # Next.js container configuration
    └── .dockerignore        # Files ignored in frontend docker build
```

---

## ⚙️ Env Configuration

The backend container requires an `OPENAI_API_KEY` to talk to the OpenAI completion engine.

Before starting the containers, export your API key in your terminal session:
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

---

## 🚀 Step-by-Step Execution Commands

### 1. Start the Containers (Docker Compose)
To compile and launch the full project (FastAPI backend on port `8020` and Next.js frontend on port `3000`):

```bash
docker compose up --build
```
*If you only want to build and run the backend in the background:*
```bash
docker compose up --build -d backend
```

---

### 2. Verify Backend Daemon Connection
Check if the backend container is running and has successfully connected to the host's `/var/run/docker.sock` to control sibling containers:

```bash
curl http://localhost:8020/health
```
**Expected Response:**
```json
{
  "status": "healthy",
  "docker_connected": true,
  "docker_version": "29.1.3"
}
```

---

### 3. Test Code Generation & Streaming Compilation
You can test the real-time log-streaming compilation endpoint using a `curl` POST request. The `-N` flag disables output buffering, allowing you to see logs print frame-by-frame:

```bash
curl -N -X POST \
  -H "Content-Type: application/json" \
  -d '{"code": "from manim import *\\n\\nclass TestScene(Scene):\\n    def construct(self):\\n        circle = Circle()\\n        circle.set_fill(PINK, opacity=0.5)\\n        self.play(Create(circle))\\n", "scene_name": "TestScene"}' \
  http://localhost:8020/compile
```

**Expected Stream Output:**
```
[INFO] Written code to scene.py. Starting compiler container...
Manim Community v0.20.1
Animation 0: Create(Circle):   0%|          | 0/30 [00:00<?, ?it/s]
Animation 0: Create(Circle):  93%|█████████▎| 28/30 [00:00<00:00, 269it/s]
File ready at '/manim/media/videos/scene/720p30/TestScene.mp4'

[SUCCESS] Render complete! Video URL: /renders/media/videos/scene/720p30/TestScene.mp4
```

---

### 4. Setup Local IDE Autocomplete & Linting (Optional)
To get IDE autocompletion for python code in Cursor/VS Code on your host machine, initialize a local virtual environment:

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies locally
pip install -r requirements.txt
```
*(Select the `.venv/bin/python` interpreter in your IDE to activate hover hints and library imports.)*
