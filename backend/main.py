import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import docker

from services.compiler import compile_manim_generator, compile_and_heal_generator, RENDERS_LOCAL_DIR, HOST_RENDERS_DIR

app = FastAPI(title="Manim Cursor API")

# Configure CORS so our Next.js frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the renders folder exists inside the container
os.makedirs(RENDERS_LOCAL_DIR, exist_ok=True)

# Mount the renders directory as static files to serve the generated video files
app.mount("/renders", StaticFiles(directory=RENDERS_LOCAL_DIR), name="renders")

class CompileRequest(BaseModel):
    code: str
    scene_name: str

@app.get("/")
def read_root():
    return {"message": "Manim Cursor API is online", "host_renders_dir": HOST_RENDERS_DIR}

@app.get("/health")
def health_check():
    # Verify we can connect to the Docker daemon
    try:
        client = docker.from_env()
        docker_info = client.info()
        return {
            "status": "healthy",
            "docker_connected": True,
            "docker_version": docker_info.get("ServerVersion", "Unknown")
        }
    except Exception as e:
        return {
            "status": "degraded",
            "docker_connected": False,
            "error": str(e)
        }

@app.post("/compile")
def compile_scene(req: CompileRequest):
    """
    Streams the output of the compilation process line-by-line.
    Uses Server-Sent Events (SSE) / streaming text.
    """
    # Returns a real-time stream of logs as they are printed by the Manim compiler
    return StreamingResponse(
        compile_manim_generator(req.code, req.scene_name),
        media_type="text/event-stream"
    )

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o-mini"

@app.post("/generate-render")
def generate_and_render_scene(req: GenerateRequest):
    """
    Receives a user text prompt, asks OpenAI to write Manim code,
    compiles it, and automatically self-heals any errors.
    """
    return StreamingResponse(
        compile_and_heal_generator(req.prompt, req.model),
        media_type="text/event-stream"
    )
