import os
import re
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache.db")

def normalize_prompt(prompt: str) -> str:
    """Normalizes a prompt to create a standard cache key:
    1. Lowercase the text.
    2. Strip punctuation.
    3. Filter out action verbs and common articles (stop words).
    4. Sort words alphabetically to handle word order variations.
    """
    # 1. Lowercase
    text = prompt.lower()
    # 2. Strip punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    # 3. Tokenize
    words = text.split()
    # 4. Remove minimalist stop words / action verbs
    stop_words = {
        "a", "an", "the", "and", "or", "to", "of", "in", "with", "by", "for", 
        "draw", "animate", "create", "make", "show", "render", "generate"
    }
    filtered_words = [w for w in words if w not in stop_words]
    # 5. Sort alphabetically
    filtered_words.sort()
    # 6. Rejoin
    return " ".join(filtered_words)

def init_db(force_recreate: bool = False):
    """Initializes the SQLite database and creates the cache table.
    If force_recreate is True, drops the existing table first.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if force_recreate:
        cursor.execute("DROP TABLE IF EXISTS animation_cache")
        
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS animation_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            cache_key TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL,
            scene_name TEXT NOT NULL,
            video_rel_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def find_similar_prompt(prompt: str) -> dict | None:
    """Looks up a prompt in the cache using the normalized cache key."""
    init_db()
    cache_key = normalize_prompt(prompt)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT prompt, code, scene_name, video_rel_path FROM animation_cache WHERE cache_key = ?",
        (cache_key,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        cached_prompt, code, scene_name, video_rel_path = row
        return {
            "prompt": cached_prompt,
            "code": code,
            "scene_name": scene_name,
            "video_rel_path": video_rel_path
        }
    return None

def insert_cache(prompt: str, code: str, scene_name: str, video_rel_path: str):
    """Inserts a new animation metadata entry into the cache database."""
    init_db()
    cache_key = normalize_prompt(prompt)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO animation_cache (prompt, cache_key, code, scene_name, video_rel_path) VALUES (?, ?, ?, ?, ?)",
            (prompt, cache_key, code, scene_name, video_rel_path)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Already exists in cache
        pass
    finally:
        conn.close()
