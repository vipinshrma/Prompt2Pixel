import os
import sys
import sqlite3

# Ensure python path contains backend directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.cache_service import init_db, normalize_prompt, find_similar_prompt, insert_cache, DB_PATH

def run_tests():
    print("=== STARTING NORMALIZED CACHE TESTS ===")
    
    # 1. Test Normalization Function
    print("\n1. Testing normalization rules...")
    test_cases = [
        ("Draw a red circle", "circle red"),
        ("Make a red circle.", "circle red"),
        ("Animate a circle in red", "circle red"),
        ("red glowing square", "glowing red square"),
        ("glowing red square", "glowing red square"),
    ]
    
    for prompt, expected in test_cases:
        actual = normalize_prompt(prompt)
        print(f"  Prompt: \"{prompt}\" -> Key: \"{actual}\" (Expected: \"{expected}\")")
        assert actual == expected, f"Normalization mismatch for: {prompt}"
        
    print("Normalization tests passed!")

    # 2. Re-create Database
    print("\n2. Re-creating Database with new schema...")
    init_db(force_recreate=True)
    print(f"Database file initialized at: {DB_PATH}")

    # 3. Test Insert
    print("\n3. Testing cache insertion...")
    prompt = "Draw a glowing green triangle"
    code = "from manim import *\nclass GreenTriangle(Scene):\n    def construct(self):\n        self.play(Create(Triangle(color=GREEN)))\n"
    scene_name = "GreenTriangle"
    video_rel_path = "media/videos/scene/1080p60/GreenTriangle.mp4"
    
    insert_cache(prompt, code, scene_name, video_rel_path)
    print("Cache entry inserted successfully.")

    # 4. Test Cache Hits
    print("\n4. Testing cache hits...")
    # Exact hit
    match_exact = find_similar_prompt(prompt)
    assert match_exact is not None, "Failed to find exact cache match"
    print(f"  Exact match found! Path: {match_exact['video_rel_path']}")
    
    # Synonymous hit (different capitalization, added stop words, swapped word order)
    synonym_prompt = "Make a green glowing triangle."
    match_synonym = find_similar_prompt(synonym_prompt)
    assert match_synonym is not None, "Failed to find semantic/synonymous cache match"
    print(f"  Synonymous match found for \"{synonym_prompt}\"!")
    print(f"  Matched original prompt: \"{match_synonym['prompt']}\"")
    
    # 5. Test Cache Misses (Ensuring parameter changes don't collide)
    print("\n5. Testing cache misses (parameter variations)...")
    
    # Shape change
    shape_change_prompt = "Draw a glowing green square"
    match_shape = find_similar_prompt(shape_change_prompt)
    assert match_shape is None, "FAIL: Shape change shouldn't result in cache hit!"
    print("  Shape change correctly missed the cache.")
    
    # Color change
    color_change_prompt = "Draw a glowing red triangle"
    match_color = find_similar_prompt(color_change_prompt)
    assert match_color is None, "FAIL: Color change shouldn't result in cache hit!"
    print("  Color change correctly missed the cache.")
    
    print("\n=== ALL CACHE TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_tests()
