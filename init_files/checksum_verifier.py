import os
import hashlib
import json
import concurrent.futures

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None

def verify_file(current_full_path, current_rel_path, expected_hash):
    if not os.path.exists(current_full_path):
        return (False, f"Missing file: {current_rel_path}")
    
    calculated = calculate_sha256(current_full_path)
    if calculated != expected_hash:
        return (False, f"Checksum mismatch for: {current_rel_path}\n  Expected: {expected_hash}\n  Actual:   {calculated}")
    
    return (True, None)

def verify_checksums(directory, checksum_data, checksum_file):    
    files_to_verify = []

    def collect_files(current_dir, data, rel_path_acc):
        for name, value in data.items():
            current_rel_path = os.path.join(rel_path_acc, name)
            current_full_path = os.path.join(current_dir, name)

            if isinstance(value, dict):
                if os.path.isdir(current_full_path):
                    collect_files(current_full_path, value, current_rel_path)
            elif isinstance(value, str):
                files_to_verify.append((current_full_path, current_rel_path, value))

    collect_files(directory, checksum_data, "")

    print(f"Verifying {len(files_to_verify)} files...")
    
    success = True
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(verify_file, f[0], f[1], f[2]): f for f in files_to_verify}
        
        for future in concurrent.futures.as_completed(futures):
            result, message = future.result()
            if not result:
                print(message)
                success = False

    return success