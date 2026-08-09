import os

path = r"c:\Users\rthiv\Desktop\CONSTRUCTION_OS\frontend\.next\server\app\page.js"
if not os.path.exists(path):
    # Try client chunk
    path = r"c:\Users\rthiv\Desktop\CONSTRUCTION_OS\frontend\.next\static\chunks\app\page.js"

print(f"Reading compiled bundle at {path}...")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Let's find occurrences of "ReasoningTrace"
    pos = 0
    idx = 1
    while True:
        pos = content.find("ReasoningTrace", pos)
        if pos == -1:
            break
        print(f"\n--- Occurrence {idx} (char pos {pos}) ---")
        # Print 300 characters before and after
        start = max(0, pos - 300)
        end = min(len(content), pos + 2500)
        print(content[start:end])
        pos += 1
        idx += 1
        if idx > 3: # limit output
            break
else:
    print("Bundle not found!")
