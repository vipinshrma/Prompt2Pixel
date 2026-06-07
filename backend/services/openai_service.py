import os
import re
from openai import OpenAI

# Initialize the OpenAI client using environment variable
api_key = os.getenv("OPENAI_API_KEY")

# We fallback to a dummy client if not provided, allowing startup
if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None
    print("Warning: OPENAI_API_KEY environment variable is not set. OpenAI calls will fail.")

SYSTEM_PROMPT = """You are an expert animator and educator specializing in the Manim (Math Animation) library.
Your task is to write high-quality, bug-free, and self-contained Manim Python code based on the user's prompt.

You MUST adhere to these strict guidelines:
1. ONLY return valid Python code enclosed in a single markdown code block, i.e., ```python <code here> ```. Do not include any explanations or conversational text before or after the code block.
2. Use ONLY the standard imports: `from manim import *`.
3. Write clean, readable code. Ensure all geometry, colors, and math equations are correct.
4. Always use standard colors like `BLUE`, `RED`, `GREEN`, `YELLOW`, `ORANGE`, `PINK`, `WHITE`, `BLACK`, `PURPLE`.
5. Make sure the animation is visually appealing, has smooth transitions, and runs in a reasonable time (10-30 seconds).
6. Do NOT reference external files (images, custom SVGs, or audio) because they will not be available in the container environment. Use basic Mobjects like Circle, Square, Text, MathTex, Line, Arrow, VGroup, etc.
7. Design the scene to fit a standard 16:9 aspect ratio.
8. If representing math, use raw strings for LaTeX formulas (e.g., MathTex(r"\\frac{a}{b}")), noting the double backslash in python strings to avoid escaping issues.
9. IF the user's prompt is completely unrelated to drawing, math, or animations (e.g. 'hi', 'hello', 'what is the weather'), you MUST reply EXACTLY with the string `[REJECT] I can only create Manim animations. Try asking me something like: "Draw a glowing red square that morphs into a circle" or "Animate the Pythagorean theorem".` Do not output any code. HOWEVER, you MUST accept any request to draw shapes, math, or text, even if very brief (like 'create a square' or 'draw a line').
10. IMPORTANT SPACING: When adding multiple shapes or text labels, you MUST properly space them out using generous buffering (e.g., `.arrange(RIGHT, buff=1.0)` or `.next_to(obj, DOWN, buff=0.5)`) so nothing overlaps. NEVER let text labels overlap shapes or other text.
11. PREVENT OVERFLOW: If drawing a large scene with many spaced-out elements (like a solar system), group everything into a `VGroup` and scale the entire group down to fit the screen (e.g. `my_group.scale_to_fit_width(13)`) AFTER spacing them out, so nothing gets cut off by the camera edges.
"""

def extract_manim_code(llm_output: str) -> tuple[str, str]:
    """
    Extracts the python code and the main Scene class name from the LLM output.
    Returns:
        (code_content, scene_name)
    """
    if llm_output.strip().startswith("[REJECT]"):
        raise ValueError(llm_output.replace("[REJECT]", "").strip())
    # Regex to find python code blocks
    code_match = re.search(r"```python\s*(.*?)\s*```", llm_output, re.DOTALL)
    if not code_match:
        # Fallback if the LLM output raw python without code blocks
        code_content = llm_output.strip()
    else:
        code_content = code_match.group(1).strip()

    # Regex to search for the first class declaration inheriting from Scene or VectorScene
    scene_match = re.search(r"class\s+([\w_]+)\s*\(\s*(?:Scene|VectorScene|LinearTransformationScene|MovingCameraScene|ThreeDScene)\s*\)\s*:", code_content)
    if scene_match:
        scene_name = scene_match.group(1)
    else:
        # Fallback default if we cannot parse
        scene_name = "GeneratedScene"
        # Append class wrapper if LLM forgot to define a class
        if "def construct(self):" not in code_content:
            code_content = f"from manim import *\n\nclass {scene_name}(Scene):\n    def construct(self):\n" + "\n".join(f"        {line}" for line in code_content.splitlines())

    return code_content, scene_name

def generate_manim_code(prompt: str, model: str = "gpt-4o-mini") -> tuple[str, str]:
    """
    Calls OpenAI chat completions API to generate Manim code from a text prompt.
    Returns:
        (code, scene_name)
    """
    if not client:
        raise ValueError("OpenAI client is not configured. Please supply an OPENAI_API_KEY environment variable.")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Low temperature for more predictable code structures
        )
        output_text = response.choices[0].message.content
        return extract_manim_code(output_text)
    except Exception as e:
        raise RuntimeError(f"OpenAI API call failed: {str(e)}")

def heal_manim_code(failed_code: str, error_logs: str, scene_name: str, model: str = "gpt-4o-mini") -> tuple[str, str]:
    """
    Submits failed code and error traceback back to OpenAI to correct the code.
    """
    if not client:
        raise ValueError("OpenAI client is not configured. Please supply an OPENAI_API_KEY environment variable.")

    prompt = f"""The following Manim code failed during compilation:

```python
{failed_code}
```

It produced the following compilation error logs:
```
{error_logs}
```

Please fix the error. Return ONLY the complete corrected Python code inside a single ```python ``` code block. Ensure the Scene class '{scene_name}' exists and works correctly.
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, # Keep temperature extremely low for error fixing
        )
        output_text = response.choices[0].message.content
        return extract_manim_code(output_text)
    except Exception as e:
        raise RuntimeError(f"OpenAI self-healing call failed: {str(e)}")
