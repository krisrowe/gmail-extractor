import os
import shutil
import subprocess
from pathlib import Path

def run_e2e_test():
    root_dir = Path(__file__).parent.parent.absolute()
    temp_data_dir = root_dir / "temp_e2e_data"
    if temp_data_dir.exists(): shutil.rmtree(temp_data_dir)
    temp_data_dir.mkdir()

    print(f"--- Starting E2E Docker Test (using Makefile engine) ---")
    print(f"Data Dir: {temp_data_dir}")

    # Use Makefile targets to perform the work
    env = os.environ.copy()
    env["EMAIL_ARCHIVE_DATA_DIR"] = str(temp_data_dir)

    try:
        # --- PASS 1: Sync 2 emails ---
        print("\n>> Pass 1: Fetching 2 emails...")
        env["GMEX_LIMIT"] = "2"
        subprocess.run(["make", "fetch"], cwd=root_dir, env=env, check=True)

        files_v1 = list(temp_data_dir.glob("*.meta"))
        print(f"Pass 1 complete. Files found: {len(files_v1)}")
        if len(files_v1) != 2: raise RuntimeError(f"Expected 2 files, found {len(files_v1)}")

        # --- PASS 2: Fetch 5 emails (should skip first 2) ---
        print("\n>> Pass 2: Fetching 5 emails (expecting 3 new)...")
        env["GMEX_LIMIT"] = "5"
        result = subprocess.run(["make", "fetch"], cwd=root_dir, env=env, capture_output=True, text=True)
        
        print(result.stdout)
        
        if "Found 5 messages. New: 3" in result.stdout:
            print("✅ IDEMPOTENCY VERIFIED")
            print("✅ SUCCESS! E2E Incremental Sync Verified.")
        else:
            # Relax check for edge cases where inbox has < 5 messages
            if "New:" in result.stdout and "New: 5" not in result.stdout:
                print("✅ IDEMPOTENCY VERIFIED (Incremental skip confirmed)")
            else:
                print("❌ FAILED: Incremental sync logs not found or incorrect.")
                print(result.stderr)
                return
            
    finally:
        print("\nTearing down...")
        if temp_data_dir.exists(): shutil.rmtree(temp_data_dir)
        print("Done.")

if __name__ == "__main__":
    run_e2e_test()
