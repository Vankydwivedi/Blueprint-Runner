#!/usr/bin/env python3
import os
import re
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

USE_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))

DEFAULT_PROMPT = """
Generate a minimal Scrypto blueprint (Rust) that compiles with scrypto and is runnable in a scrypto package.
Return the Rust code only inside a fenced code block, language tag 'rust' preferred.
The blueprint should be trivial — one blueprint with a `new` constructor and a simple method `hello` that returns a string.
"""

ROOT = Path.cwd()
OUTPUT_DIR = ROOT / "output" / "trivial_blueprint"
SRC_DIR = OUTPUT_DIR / "src"
LIB_RS = SRC_DIR / "lib.rs"
CARGO_TOML = OUTPUT_DIR / "Cargo.toml"
README = ROOT / "README.md"
RESULTS = ROOT / "results.json"

def ensure_dirs():
    SRC_DIR.mkdir(parents=True, exist_ok=True)

def write_cargo_if_missing():
    if not CARGO_TOML.exists():
        CARGO_TOML.write_text(
            '[package]\nname = "trivial_blueprint"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\nscrypto = "1.3.0"\n'
        )
        print(f"Wrote default {CARGO_TOML}")

def default_librs():
    LIB_RS.write_text("""use scrypto::prelude::*;

blueprint! {
    struct Trivial {}

    impl Trivial {
        pub fn new() -> ComponentAddress {
            Self {}.instantiate().globalize()
        }

        pub fn hello(&self) -> String {
            "hello from trivial blueprint".to_string()
        }
    }
}
""")
    print(f"Wrote default {LIB_RS}")

def extract_rust_code_from_text(text):
    m = re.search(r"```(?:rust)?\n(.*?)```", text, re.S | re.I)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"(use\s+scrypto[\s\S]*)", text)
    if m2:
        return m2.group(1).strip()
    return None

def call_openai_chat(prompt, system="You are a helpful assistant that outputs Rust Scrypto blueprints."):
    try:
        import openai
    except Exception as e:
        raise RuntimeError("OpenAI python package not installed. Install with `pip install openai`") from e
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    resp = openai.ChatCompletion.create(
        model=os.environ.get("OPENAI_MODEL","gpt-4o-mini"),
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":prompt}
        ],
        max_tokens=1500,
        temperature=0.0,
    )
    return resp["choices"][0]["message"]["content"]

def run_cargo_scrypto_test(workdir: Path):
    cmd = ["cargo", "scrypto", "test"]
    print("Running:", " ".join(cmd), "in", str(workdir))
    try:
        p = subprocess.run(cmd, cwd=str(workdir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    except FileNotFoundError:
        return 127, "cargo not found in PATH"
    return p.returncode, p.stdout

def append_readme_section(readme_path: Path, heading: str, content: str):
    header = f"\n## {heading}\n\n"
    ts = datetime.utcnow().isoformat() + "Z"
    to_write = header + f"Timestamp: {ts}\n\n```\n{content}\n```\n"
    with open(readme_path, "a", encoding="utf-8") as f:
        f.write(to_write)
    print(f"Appended test log to {readme_path}")

def save_results(passed: bool, retries: int, stdout: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "package": str(OUTPUT_DIR),
        "passed": passed,
        "retry_count": retries,
        "last_stdout": stdout[:10000]
    }
    results = {}
    if RESULTS.exists():
        try:
            with open(RESULTS, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            results = {}
    results.setdefault("runs", []).append(entry)
    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote results to {RESULTS}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", "-p", default=DEFAULT_PROMPT, help="Prompt to send to the LLM")
    args = parser.parse_args()

    ensure_dirs()
    write_cargo_if_missing()

    if not USE_OPENAI:
        print("OPENAI_API_KEY not set; writing default blueprint and running tests on generated package.")
        default_librs()
        rc, out = run_cargo_scrypto_test(OUTPUT_DIR)
        append_readme_section(README, "2 — cargo scrypto test output (initial run)", out)
        passed = (rc == 0)
        save_results(passed, retries=0, stdout=out)
        print("Done. Paste any errors here if it failed.")
        return

    try:
        print("Calling model to generate blueprint...")
        resp = call_openai_chat(args.prompt)
        extracted = extract_rust_code_from_text(resp)
        if not extracted:
            print("Failed to extract code from model response. Writing fallback blueprint.")
            default_librs()
        else:
            LIB_RS.write_text(extracted)
            print(f"Wrote model-generated code to {LIB_RS}")

        if not CARGO_TOML.exists():
            write_cargo_if_missing()

        rc, out = run_cargo_scrypto_test(OUTPUT_DIR)
        append_readme_section(README, "2 — cargo scrypto test output (attempt 1)", out)
        if rc == 0:
            print("Tests passed on attempt 1.")
            save_results(True, retries=0, stdout=out)
            return

        print("Tests failed on attempt 1. Will attempt one automatic retry with the model (if possible).")
        followup_prompt = args.prompt + "\n\nThe project failed to compile/run with the following compiler/test output. Please reply with a corrected Rust Scrypto `lib.rs` inside a fenced ```rust ... ``` block that compiles.\n\nCompiler output:\n```\n" + out[:4000] + "\n```\nPlease only return the corrected Rust code in a fenced code block."
        resp2 = call_openai_chat(followup_prompt)
        extracted2 = extract_rust_code_from_text(resp2)
        if not extracted2:
            print("Model did not return code on retry. Aborting.")
            save_results(False, retries=1, stdout=out + "\n\nModel retry produced no code.")
            return
        LIB_RS.write_text(extracted2)
        print(f"Wrote retry code to {LIB_RS}")

        rc2, out2 = run_cargo_scrypto_test(OUTPUT_DIR)
        append_readme_section(README, "2 — cargo scrypto test output (attempt 2)", out2)
        passed = (rc2 == 0)
        save_results(passed, retries=1, stdout=out2)
        if passed:
            print("Tests passed on retry.")
        else:
            print("Retry failed. See README and results.json for details.")

    except Exception as e:
        print("Error during generation/test:", str(e))
        save_results(False, retries=0, stdout=str(e))

if __name__ == "__main__":
    main()
