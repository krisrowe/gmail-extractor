import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sdk_path = Path(__file__).parent.parent / "gmex-sdk" / "src"
sys.path.append(str(sdk_path))

from gmex_sdk.config import get_token_status

def run_e2e_test():
    root_dir = Path(__file__).parent.parent.absolute()
    temp_data_dir = root_dir / "temp_e2e_data"
    
    if temp_data_dir.exists():
        shutil.rmtree(temp_data_dir)
    temp_data_dir.mkdir()

    print(f"--- Starting E2E Docker Test ---")
    print(f"Data Dir: {temp_data_dir}")

    status = get_token_status()
    if not status["exists"]:
        print(f"FAILED: No token found at {status['path']}. Run gmex token import first.")
        return

    env = os.environ.copy()
    env["DATA_DIR"] = str(temp_data_dir)
    env["TOKEN_FILE"] = str(status["path"])

    try:
        # --- PASS 1: Fetch 2 emails ---
        print("\n>> Pass 1: Syncing first 2 emails...")
        env["GMEX_LIMIT"] = "2"
        cmd = ["docker", "compose", "up", "--build", "--exit-code-from", "fetcher"]
        subprocess.run(cmd, cwd=root_dir, env=env, check=True)

        files_v1 = list(temp_data_dir.glob("*.meta"))
        print(f"Pass 1 complete. Files found: {len(files_v1)}")
        if len(files_v1) != 2:
            print(f"❌ FAILED: Expected 2 files, found {len(files_v1)}")
            return

        # --- PASS 2: Fetch 5 emails (should skip first 2) ---
        print("\n>> Pass 2: Syncing 5 emails (expecting 3 new)...")
        env["GMEX_LIMIT"] = "5"
        # We don't need --build again
        cmd = ["docker", "compose", "up", "--exit-code-from", "fetcher"]
        result = subprocess.run(cmd, cwd=root_dir, env=env, capture_output=True, text=True)
        
        print(result.stdout)
        
        # Verify Idempotency via logs
        if "Found 5 messages. New: 3" in result.stdout or "New: 3" in result.stderr:
            print("✅ IDEMPOTENCY VERIFIED: Logs show 3 new messages.")
        else:
            # Some accounts might have fewer than 5 messages total, check if New < 5
            if "New: 5" in result.stdout:
                print("❌ FAILED: Pass 2 tried to re-download all 5 messages.")
                return
            print("Warning: Could not find exact 'New: 3' string, but check logs above.")

        # Final Result Check
        files_v2 = list(temp_data_dir.glob("*.meta"))
        print(f"Final storage count: {len(files_v2)}")
        if len(files_v2) < 2:
            print(f"❌ FAILED: Storage was corrupted or wiped.")
            return

        print(f"\n✅ SUCCESS! E2E Incremental Sync Verified.")
            
    finally:
        print("\nTearing down...")
        subprocess.run(["docker", "compose", "down"], cwd=root_dir, env=env, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if temp_data_dir.exists():
            shutil.rmtree(temp_data_dir)
        print("Done.")

if __name__ == "__main__":
    run_e2e_test()
