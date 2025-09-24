import os
import re

RAW_DIR = "kb/raw"
CLEAN_DIR = "kb/clean"

def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)

    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)

    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    text = re.sub(r"```[\s\S]*?```", " ", text)

    text = re.sub(r"`[^`]+`", " ", text)

    text = re.sub(r"<!--.*?-->", " ", text)

    text = re.sub(r"#.*", " ", text)

    text = re.sub(r"//.*", " ", text)

    text = re.sub(r"\s+", " ", text).strip()
    return text

def process_repo():
    if not os.path.exists(CLEAN_DIR):
        os.makedirs(CLEAN_DIR)

    for root, _, files in os.walk(RAW_DIR):
        for f in files:
            raw_path = os.path.join(root, f)
            rel_path = os.path.relpath(raw_path, RAW_DIR)
            clean_path = os.path.join(CLEAN_DIR, rel_path)

            os.makedirs(os.path.dirname(clean_path), exist_ok=True)

            try:
                with open(raw_path, "r", encoding="utf-8", errors="ignore") as infile:
                    raw_text = infile.read()
                cleaned = clean_text(raw_text)
                with open(clean_path, "w", encoding="utf-8") as outfile:
                    outfile.write(cleaned)
                print(f"Cleaned: {rel_path}")
            except Exception as e:
                print(f"Skipping {rel_path}: {e}")

if __name__ == "__main__":
    process_repo()
