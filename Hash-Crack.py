import hashlib
import time
import os
from multiprocessing import Process, Queue, cpu_count

HASHES = [
    "0be4570119a425e1dc3e7b44ba41b5ffb8f34736e3c1a9eaccf1f4bc1a33166d",
    "0c25ced546ad8fa8b83dd79adf5d192f9c6e6e098ea622899b05a409a1ab1403",
    "e35857d99d31fe1a93e65059b47ab16fac874bc5ad2d9a3486641cb440559d49",
    "f55a24947785f8670f99f7a1099bd76c4e4cde9d4a1a8e36e7e65e32796bc9bc",
    "6a59e34058e40724cabb3f8fa8358b4cdf43ff0f7fa07d50b5ed2e15dccaa0bd",
]

WORDLIST = "rockyou.txt"
results = {}

def run_sequential():
    print("=" * 70)
    print("[*] SEQUENTIAL HASH CRACKING - Starting...")
    print("=" * 70)

    for idx, target_hash in enumerate(HASHES, 1):
        print(f"\n[*] Cracking: {target_hash}")
        start = time.time()
        password = None

        try:
            with open(WORDLIST, 'rb') as f:
                for line in f:
                    word = line.strip().decode('utf-8', errors='ignore')
                    if hashlib.sha256(word.encode()).hexdigest() == target_hash:
                        password = word
                        break
        except FileNotFoundError:
            print(f"[-] Wordlist not found: {WORDLIST}")

        elapsed = time.time() - start
        results[idx] = {"sequential": elapsed, "parallel": None, "password": password}
        print(f"[+] SUCCESS! Password: {password}" if password else "[-] Not found")
        print(f"[*] Time: {elapsed:.4f}s")

def crack_segment(target_hashes, wordlist_path, byte_start, byte_end, result_queue):
    remaining_hashes = set(target_hashes)
    try:
        with open(wordlist_path, 'rb') as f:
            f.seek(byte_start)
            
            if byte_start != 0:
                f.readline()

            while f.tell() < byte_end and remaining_hashes:
                line = f.readline()
                if not line:
                    break

                word = line.strip().decode('utf-8', errors='ignore')
                hashed_word = hashlib.sha256(word.encode()).hexdigest()

                if hashed_word in remaining_hashes:
                    result_queue.put((hashed_word, word))
                    remaining_hashes.discard(hashed_word)
    except Exception as e:
        print(f"[!] Worker error: {e}")

def run_parallel():
    print("\n" + "=" * 70)
    num_workers = cpu_count() 
    print(f"[*] PARALLEL HASH CRACKING - {num_workers} workers total")
    print("=" * 70)

    if not os.path.exists(WORDLIST):
        return

    file_size = os.path.getsize(WORDLIST)
    chunk_size = file_size // num_workers
    
    result_queue = Queue()
    processes = []
    start_time = time.time()

    for i in range(num_workers):
        byte_start = i * chunk_size
        byte_end = file_size if i == num_workers - 1 else (i + 1) * chunk_size
        p = Process(
            target=crack_segment,
            args=(HASHES, WORDLIST, byte_start, byte_end, result_queue)
        )
        processes.append(p)
        p.start() 

    found_count = 0
    cracked = {}

    while found_count < len(HASHES):
        try:
            h, pwd = result_queue.get(timeout=2)
            if h not in cracked:
                cracked[h] = pwd
                found_count += 1
                print(f"[+] Found: {pwd}")
        except:
            if not any(p.is_alive() for p in processes):
                break

    for p in processes:
        p.terminate()
        p.join()

    total_time = time.time() - start_time
    print(f"[*] Total parallel time: {total_time:.4f}s")

    for idx, target_hash in enumerate(HASHES, 1):
        if idx not in results:
            results[idx] = {"sequential": None, "parallel": None, "password": None}
        results[idx]["parallel"] = total_time
        results[idx]["cracked"] = cracked.get(target_hash)

    results["parallel_total"] = total_time

def print_report():
    print("\n" + "=" * 70)
    print("[*] FINAL REPORT")
    print("=" * 70)
    total_seq = sum(results[i]["sequential"] for i in range(1, len(HASHES) + 1))
    total_par = results.get("parallel_total", 0)
    
    print(f"Sequential TOTAL: {total_seq:.4f}s")
    print(f"Parallel TOTAL:   {total_par:.4f}s")
    if total_par > 0:
        print(f"Speedup:          {total_seq / total_par:.2f}x")

if __name__ == '__main__':
    run_sequential()
    run_parallel()
    print_report()