import os

search_dir = r"c:\Users\rthiv\Desktop\CONSTRUCTION_OS\frontend\.next"
target_str = "grid-cols-1 md:grid-cols-2 gap-5"

print(f"Recursively searching {search_dir} for '{target_str}'...")

matches_found = 0
for root, dirs, files in os.walk(search_dir):
    # Skip trace or cache directories to keep search clean and fast
    if "cache" in root or "trace" in root:
        continue
    for file in files:
        if file.endswith(".js") or file.endswith(".html"):
            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if target_str in content:
                    matches_found += 1
                    print(f"\nMatch {matches_found} in file: {full_path}")
                    # Find index and print snippet
                    pos = content.find(target_str)
                    start = max(0, pos - 150)
                    end = min(len(content), pos + 150)
                    print(f"Snippet:\n... {content[start:end]} ...")
            except Exception as e:
                # ignore read errors
                pass

if matches_found == 0:
    print("No matches found in built bundles.")
