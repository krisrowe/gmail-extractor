import time
import shutil
import random
import string
from pathlib import Path
from datetime import datetime, timedelta
from email_archive import EmailStore

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

def run_benchmark(count=10000):
    temp_dir = Path("./bench_temp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    print(f"--- Setting up Benchmark ({count} emails) ---")
    store = EmailStore(temp_dir)
    
    start_time = time.time()
    for i in range(count):
        msg_id = f"msg_{i}"
        # Spread dates over last year
        date = datetime.now() - timedelta(days=random.randint(0, 365))
        
        headers = {
            "Subject": f"Benchmark Email {i} " + generate_random_string(20),
            "From": "sender@example.com",
            "To": "user@example.com",
            "Labels": ["Inbox", "Benchmark", "Work"]
        }
        body = {
            "text": generate_random_string(500), # 500 chars body
            "html": "<p>" + generate_random_string(500) + "</p>"
        }
        store.save(msg_id, date, headers, body)
        
        if i % 1000 == 0 and i > 0:
            print(f"Generated {i}...")
            
    setup_time = time.time() - start_time
    print(f"Setup complete. Time: {setup_time:.2f}s ({(count/setup_time):.0f} saves/sec)")
    
    # --- Benchmark 1: Listing (Triage Scan) ---
    print("\n--- Benchmark 1: Listing (ls *.meta) ---")
    start = time.time()
    items = store.list()
    duration = time.time() - start
    print(f"Listed {len(items)} items in {duration:.4f}s")
    print(f"Rate: {(len(items)/duration):.0f} ops/sec")
    
    # --- Benchmark 2: Random Access (Metadata Only) ---
    print("\n--- Benchmark 2: Random Read (Metadata Only) ---")
    target_ids = [f"msg_{random.randint(0, count-1)}" for _ in range(1000)]
    start = time.time()
    for mid in target_ids:
        data = store.get(mid, include_content=False)
        assert data["subject"].startswith("Benchmark")
    duration = time.time() - start
    print(f"Read 1000 metadata files in {duration:.4f}s")
    print(f"Latency: {(duration/1000)*1000:.2f} ms/op")
    
    # --- Benchmark 3: Random Access (Full Content) ---
    print("\n--- Benchmark 3: Random Read (Full Content) ---")
    start = time.time()
    for mid in target_ids:
        data = store.get(mid, include_content=True)
        assert len(data["body"]["text"]) == 500
    duration = time.time() - start
    print(f"Read 1000 full emails (Meta+Body) in {duration:.4f}s")
    print(f"Latency: {(duration/1000)*1000:.2f} ms/op")
    
    # --- Benchmark 4: Date Filtering ---
    print("\n--- Benchmark 4: Date Filtering (Last 30 Days) ---")
    cutoff = datetime.now() - timedelta(days=30)
    start = time.time()
    recent = store.list(since=cutoff)
    duration = time.time() - start
    print(f"Filtered {len(recent)} recent emails in {duration:.4f}s")
    
    # Cleanup
    print("\nCleaning up...")
    shutil.rmtree(temp_dir)
    print("Done.")

if __name__ == "__main__":
    run_benchmark(count=10000)
