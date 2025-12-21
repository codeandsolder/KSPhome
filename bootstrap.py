import os
import subprocess
import sys
import platform

DOCKER_IMAGE_NAME = "ksp-repo-builder"
INIT_FILES_DIR = "init_files"

DISCLAIMER = """
================================================================================
LEGAL DISCLAIMER:
By proceeding with this decompilation process, you confirm that you have a 
legal right to do so under your local jurisdiction (e.g., for interoperability, 
security research, or fixing errors in software you own). You acknowledge that 
decompiling software may be subject to End User License Agreements (EULA) and 
local laws. You agree the author of this script bears no liability, implicit,
explicit, or the third kind, for any negative consequences of its' execution.

Type "I CONFIRM" to proceed: """

def check_docker():
    """Verify Docker is installed and accessible."""
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def find_archive():
    """Look for supported KSP archive files in the root directory."""
    for ext in ["7z", "zip"]:
        filename = f"Kerbal Space Program.{ext}"
        if os.path.exists(filename):
            return filename
    return None

def main():
    # 1. Legal Confirmation
    user_input = input(DISCLAIMER).strip()
    if user_input != "I CONFIRM":
        print("Confirmation failed. Aborting.")
        sys.exit(0)

    # 2. Environment Check
    if not check_docker():
        print("ERROR: Docker is not installed or not running. Please start Docker and try again.")
        sys.exit(1)

    archive_name = find_archive()
    if not archive_name:
        print("ERROR: 'Kerbal Space Program.7z' or '.zip' not found in the root directory.")
        sys.exit(1)

    if not os.path.exists(os.path.join(INIT_FILES_DIR, "valid_checksums.json")):
        print(f"ERROR: Missing 'valid_checksums.json' in '{INIT_FILES_DIR}'.")
        sys.exit(1)

    # 3. Build & Run
    try:
        print(f"\n[*] Building Docker image: {DOCKER_IMAGE_NAME}...")
        subprocess.run(["docker", "build", "-t", DOCKER_IMAGE_NAME, INIT_FILES_DIR], check=True)

        print("\n[*] Starting Dockerfile...")
        subprocess.run([
            "docker", "run", "--rm", "-t",
            "-v", f"{os.getcwd()}:/workspace",
            DOCKER_IMAGE_NAME, archive_name
        ], check=True)
        
        print("\n[+] Workflow completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Error during execution: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] Process interrupted by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
