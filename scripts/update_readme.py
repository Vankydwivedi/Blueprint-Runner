import os
import subprocess
from datetime import datetime, timezone

def get_stats(path):
    total_files = 0
    latest_mtime = 0
    for root, _, files in os.walk(path):
        for f in files:
            total_files += 1
            fp = os.path.join(root, f)
            latest_mtime = max(latest_mtime, os.path.getmtime(fp))
    latest_str = datetime.fromtimestamp(latest_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return total_files, latest_str

def get_commit_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"

def build_section(stats, commit_hash):
    return f"""## 1. Data Foundation

## KB Folder Stats

### /kb/raw
- Total files: {stats['kb/raw']['total']}
- Latest modified: {stats['kb/raw']['latest']}

### /kb/clean
- Total files: {stats['kb/clean']['total']}
- Latest modified: {stats['kb/clean']['latest']}

### Repo Commit
- Commit hash: `{commit_hash}`
"""

def main():
    stats = {}
    for folder in ["kb/raw", "kb/clean"]:
        total, latest = get_stats(folder)
        stats[folder] = {"total": total, "latest": latest}

    commit_hash = get_commit_hash()
    new_section = build_section(stats, commit_hash)

    readme_path = "README.md"
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace old section if it exists
        start = content.find("## 1. Data Foundation")
        if start != -1:
            end = content.find("## 2.", start)
            if end == -1:
                end = len(content)
            content = content[:start] + new_section + content[end:]
        else:
            content += "\n" + new_section
    else:
        content = new_section

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("README.md updated successfully.")

if __name__ == "__main__":
    main()
