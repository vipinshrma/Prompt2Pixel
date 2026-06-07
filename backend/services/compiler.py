import os
import docker
from services.openai_service import generate_manim_code, heal_manim_code
from services.cache_service import find_similar_prompt, insert_cache

# Initialize docker client
try:
    client = docker.from_env()
except Exception as e:
    client = None
    print(f"Warning: Docker client could not be initialized: {str(e)}")

HOST_RENDERS_DIR = os.getenv("HOST_RENDERS_DIR", "/Users/vipan/Desktop/projects/manim-cursor/renders")
RENDERS_LOCAL_DIR = "/app/renders"

def compile_manim_generator(code: str, scene_name: str):
    """
    Generator function that runs a Manim compilation container,
    streams the stdout/stderr logs frame-by-frame, handles cleanup,
    and reports success or failure.
    """
    if client is None:
        yield "[ERROR] Docker is not available on the backend server.\n"
        return

    filename = "scene.py"
    filepath = os.path.join(RENDERS_LOCAL_DIR, filename)

    # 1. Write the code to scene.py
    try:
        with open(filepath, "w") as f:
            f.write(code)
        yield "[INFO] Written code to scene.py. Starting compiler container...\n"
    except Exception as e:
        yield f"[ERROR] Failed to write scene.py: {str(e)}\n"
        return

    # 2. Run the sibling Manim container in detached mode
    try:
        # We start the container detaching immediately so we can stream logs
        container = client.containers.run(
            image="manimcommunity/manim:stable",
            command=f"manim -qh {filename} {scene_name}",
            volumes={
                HOST_RENDERS_DIR: {
                    'bind': '/manim',
                    'mode': 'rw'
                }
            },
            detach=True,
            stdout=True,
            stderr=True
        )

        # 3. Stream the container logs line-by-line in real-time
        # container.logs(stream=True, follow=True) returns a generator yielding raw bytes
        for log_line in container.logs(stream=True, follow=True):
            yield log_line.decode("utf-8")

        # 4. Wait for the container to finish and extract the exit code
        result = container.wait()
        exit_code = result.get("StatusCode", 0)

        # 5. Clean up the container (remove it since it was detached)
        try:
            container.remove()
        except Exception as remove_err:
            yield f"[WARNING] Failed to remove compiler container: {str(remove_err)}\n"

        # 6. Verify if output file was created
        # Default Manim directory structure: media/videos/scene/1080p60/SceneName.mp4
        video_rel_path = f"media/videos/scene/1080p60/{scene_name}.mp4"
        video_full_path = os.path.join(RENDERS_LOCAL_DIR, video_rel_path)

        if exit_code == 0 and os.path.exists(video_full_path):
            yield f"\n[SUCCESS] Render complete! Video URL: /renders/{video_rel_path}\n"
        else:
            yield f"\n[FAILED] Compilation finished with exit code {exit_code}. Video not generated or compiled with errors.\n"

    except docker.errors.ContainerError as ce:
        yield f"\n[ERROR] Container error: {ce.stderr.decode('utf-8')}\n"
    except Exception as e:
        yield f"\n[ERROR] Runner crashed: {str(e)}\n"

def compile_and_heal_generator(prompt: str, model: str = "gpt-4o-mini"):
    """
    Orchestration generator that:
    1. Asks OpenAI to write the Manim python code.
    2. Compiles it inside the sandboxed sibling container.
    3. Streams compiler logs in real-time.
    4. If it fails, grabs the error logs, sends them back to OpenAI to heal,
       and runs compile again.
    """
    if client is None:
        yield "[ERROR] Docker is not available on the backend server.\n"
        return

    # Check the cache first
    yield "[INFO] Checking cache...\n"
    match = find_similar_prompt(prompt)
    
    code = None
    scene_name = None

    if match:
        yield f"[INFO] Found matching prompt in cache.\n"
        yield f"[INFO] Match prompt: \"{match['prompt']}\"\n"
        
        video_rel_path = match['video_rel_path']
        video_full_path = os.path.join(RENDERS_LOCAL_DIR, video_rel_path)
        
        if os.path.exists(video_full_path):
            yield f"[INFO] Reusing cached video render: {video_rel_path}\n"
            yield f"[INFO] Generated scene class name: '{match['scene_name']}'\n"
            yield f"[CODE]\n{match['code']}\n[/CODE]\n"
            yield f"\n[SUCCESS] Render complete! Video URL: /renders/{video_rel_path}\n"
            return
        else:
            yield "[WARNING] Cached video file not found on disk. Re-compiling the cached code...\n"
            code = match['code']
            scene_name = match['scene_name']

    if code is None or scene_name is None:
        # 1. Generate code from prompt
        yield f"[INFO] Contacting OpenAI ({model}) to generate animation code...\n"
        try:
            code, scene_name = generate_manim_code(prompt, model)
            yield f"[INFO] Generated scene class name: '{scene_name}'\n"
            # Stream the code back so the frontend can populate the editor
            yield f"[CODE]\n{code}\n[/CODE]\n"
        except Exception as e:
            yield f"[ERROR] Code generation failed: {str(e)}\n"
            return

    # 2. Main compile-and-heal loop
    max_attempts = 2
    attempt = 0
    filename = "scene.py"
    filepath = os.path.join(RENDERS_LOCAL_DIR, filename)

    while attempt < max_attempts:
        yield f"[INFO] Starting compilation attempt {attempt + 1}...\n"
        
        # Write python script to renders directory
        try:
            with open(filepath, "w") as f:
                f.write(code)
        except Exception as e:
            yield f"[ERROR] Failed to write scene.py: {str(e)}\n"
            return

        # Start compiling in a sibling container
        try:
            container = client.containers.run(
                image="manimcommunity/manim:stable",
                command=f"manim -qh {filename} {scene_name}",
                volumes={
                    HOST_RENDERS_DIR: {
                        'bind': '/manim',
                        'mode': 'rw'
                    }
                },
                detach=True,
                stdout=True,
                stderr=True
            )

            # Capture logs to stream and store for self-healing
            logs_accumulator = []
            for log_line in container.logs(stream=True, follow=True):
                decoded_line = log_line.decode("utf-8")
                logs_accumulator.append(decoded_line)
                yield decoded_line

            # Wait for container execution to finish
            result = container.wait()
            exit_code = result.get("StatusCode", 0)
            container.remove()

            # Check if video was successfully created
            video_rel_path = f"media/videos/scene/1080p60/{scene_name}.mp4"
            video_full_path = os.path.join(RENDERS_LOCAL_DIR, video_rel_path)

            if exit_code == 0 and os.path.exists(video_full_path):
                yield f"\n[SUCCESS] Render complete! Video URL: /renders/{video_rel_path}\n"
                # Save to cache
                try:
                    insert_cache(prompt, code, scene_name, video_rel_path)
                    yield "[INFO] Successfully cached this animation for future runs.\n"
                except Exception as cache_err:
                    yield f"[WARNING] Failed to cache animation: {str(cache_err)}\n"
                # Success! Terminate the generator loop
                return
            else:
                attempt += 1
                if attempt >= max_attempts:
                    yield f"\n[FAILED] Compilation failed after {max_attempts} attempts. Check final logs for errors.\n"
                    return

                yield f"\n[HEALING] Compilation failed with exit code {exit_code}. Fetching traceback error...\n"
                
                # Extract last 25 lines of compiler logs to find the Python traceback
                traceback = "".join(logs_accumulator[-25:])
                
                yield "[HEALING] Submitting traceback back to OpenAI for self-healing...\n"
                try:
                    code, scene_name = heal_manim_code(code, traceback, scene_name, model)
                    yield f"[HEALING] OpenAI corrected the code. Extracted new scene class: '{scene_name}'. Retrying...\n"
                    # Stream the healed code back so the editor updates
                    yield f"[CODE]\n{code}\n[/CODE]\n"
                except Exception as heal_err:
                    yield f"[ERROR] Self-healing request failed: {str(heal_err)}\n"
                    return

        except docker.errors.ContainerError as ce:
            yield f"\n[ERROR] Container execution error: {ce.stderr.decode('utf-8')}\n"
            return
        except Exception as e:
            yield f"\n[ERROR] Runner crashed during compilation: {str(e)}\n"
            return
