import os
import subprocess
import json
import sys
import shutil

sys.path.append('/app')
from checksum_verifier import verify_checksums

REPO_PATH = "KSP_app"
CHECKSUM_FILE = "/app/valid_checksums.json"
BRANCH_NAME = "Stock"
DOTNET_SRC_PATH = "dotnet_src"
MANAGED_PATH = os.path.join(REPO_PATH, "KSP_x64_Data", "Managed")
ILSPY_SETTINGS = "/app/ILSpy.xml"
PATCH_FILE = "/app/Assembly-CSharp.patch"

def run_command(command, cwd=None, ignore_errors=False):
    try:
        subprocess.run(command, check=True, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Stderr: {e.stderr.decode()}")
        if not ignore_errors:
            sys.exit(1)

def decompile_dll(dll_name):
    dll_path = os.path.join(MANAGED_PATH, dll_name)
    if not os.path.exists(dll_path):
        print(f"Warning: {dll_name} not found at {dll_path}")
        return

    print(f"Processing {dll_name}...")

    # 1. Deobfuscate with de4dot
    print(f"  Deobfuscating {dll_name}...")
    de4dot_cmd = f"mono /opt/de4dot/de4dot.exe --dont-rename \"{dll_path}\""
    run_command(de4dot_cmd)

    cleaned_dll_name = os.path.splitext(dll_name)[0] + "-cleaned.dll"
    cleaned_dll_path = os.path.join(MANAGED_PATH, cleaned_dll_name)

    if not os.path.exists(cleaned_dll_path):
        print(f"  Error: Cleaned DLL {cleaned_dll_name} was not created.")
        return

    # 2. Replace original with cleaned
    print(f"  Replacing {dll_name} with {cleaned_dll_name}...")
    shutil.move(cleaned_dll_path, dll_path)

    # 3. Decompile with ILSpy
    print(f"  Decompiling {dll_name} to {DOTNET_SRC_PATH}...")
    proj_name = os.path.splitext(dll_name)[0]
    output_dir = os.path.join(DOTNET_SRC_PATH, proj_name)
    os.makedirs(output_dir, exist_ok=True)
    
    ilspy_cmd = (
        f"ilspycmd -lv CSharp7_3 -p --nested-directories --disable-updatecheck "
        f"--ilspy-settingsfile \"{ILSPY_SETTINGS}\" "
        f"-r \"{MANAGED_PATH}\" "
        f"-o \"{output_dir}\" \"{dll_path}\""
    )
    run_command(ilspy_cmd)

    # 4. Update project references
    csproj_path = os.path.join(output_dir, proj_name + ".csproj")
    if os.path.exists(csproj_path):
        update_csproj(csproj_path, proj_name)
    else:
        print(f"  Warning: Expected project file {csproj_path} not found.")

def update_csproj(csproj_path, proj_name):
    print(f"  Patching project file: {csproj_path}")
    with open(csproj_path, 'r') as f:
        content = f.read()
    
    content = content.replace("<TargetFrameworkVersion>v4.0<", "<TargetFrameworkVersion>v4.8.1<")
    content = content.replace("<WarningLevel>4<", "<WarningLevel>1<")
    content = content.replace("<HintPath>KSP_app/", "<HintPath>../../KSP_app/")
    
    if proj_name == "Assembly-CSharp":
        import re
        ref_pattern = r'<Reference Include="Assembly-CSharp-firstpass">.*?</Reference>'
        proj_ref = '<ProjectReference Include="../Assembly-CSharp-firstpass/Assembly-CSharp-firstpass.csproj" />'
        content = re.sub(ref_pattern, proj_ref, content, flags=re.DOTALL)

    with open(csproj_path, 'w') as f:
        f.write(content)

def apply_patch():
    if os.path.exists(PATCH_FILE):
        print(f"Applying patch {PATCH_FILE}...")
        target_dir = os.path.join(DOTNET_SRC_PATH, "Assembly-CSharp")
        if os.path.exists(target_dir):
            run_command(f"patch -p1 -l --binary --verbose < \"{PATCH_FILE}\"", cwd=target_dir, ignore_errors=True)
        else:
            print(f"Target directory for patch {target_dir} not found.")
    else:
        print("Patch file not found, skipping.")

def create_sln():
    print("Creating solution file...")
    run_command("dotnet new sln --force -n KSP_dotnet", cwd=DOTNET_SRC_PATH)
    run_command("dotnet sln add ./Assembly-CSharp/Assembly-CSharp.csproj", cwd=DOTNET_SRC_PATH)

def main():
    if len(sys.argv) != 2:
        print("Usage: python docker_entrypoint.py <archive_name>")
        sys.exit(1)
    archive_name = sys.argv[1]

    # Existing repo check
    git_dir = os.path.join(REPO_PATH, ".git")
    if os.path.isdir(git_dir):
        print(f"Existing repository detected in {REPO_PATH}. Cleaning...")
        run_command(f"git checkout {BRANCH_NAME}", cwd=REPO_PATH)
        run_command("git reset --hard", cwd=REPO_PATH)
        run_command("git clean -fd", cwd=REPO_PATH)
        print(f"Calculating checksums...")        
        with open(CHECKSUM_FILE, 'r') as f:
            valid_checksums = json.load(f)
        root_key = list(valid_checksums.keys())[0]
        verify_checksums(REPO_PATH, valid_checksums[root_key], CHECKSUM_FILE)
    else:
        # Fresh install
        os.makedirs(REPO_PATH, exist_ok=True)
        print(f"Extracting '{archive_name}'...")
        tmp_extract = "workspace/tmp_extract"
        os.makedirs(tmp_extract, exist_ok=True)
        run_command(f'7z x "{archive_name}" -o\"{tmp_extract}\" -y')
        extracted_items = os.listdir(tmp_extract)
        source_dir = tmp_extract
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(tmp_extract, extracted_items[0])):
            source_dir = os.path.join(tmp_extract, extracted_items[0])
        for item in os.listdir(source_dir):
            shutil.move(os.path.join(source_dir, item), os.path.join(REPO_PATH, item))
        shutil.rmtree(tmp_extract)
        with open(CHECKSUM_FILE, 'r') as f:
            valid_checksums = json.load(f)
        root_key = list(valid_checksums.keys())[0]
        verify_checksums(REPO_PATH, valid_checksums[root_key], CHECKSUM_FILE)
        print(f"Creating git repo (this will take a couple seconds)...")        
        run_command("git init", cwd=REPO_PATH)
        run_command(f"git checkout -b {BRANCH_NAME}", cwd=REPO_PATH)
        run_command("git config --global user.email 'you@example.com'", cwd=REPO_PATH)
        run_command("git config --global user.name 'KSP Stock'", cwd=REPO_PATH)
        run_command("git add .", cwd=REPO_PATH)
        run_command("git commit -m 'Initial commit of stock files'", cwd=REPO_PATH)

    # Decompilation
    print("Starting decompilation process...")
    for d in ["Assembly-CSharp", "Assembly-CSharp-firstpass"]:
        path = os.path.join(DOTNET_SRC_PATH, d)
        if os.path.exists(path):
             shutil.rmtree(path)

    # Order matters because Assembly-CSharp depends on firstpass
    decompile_dll("Assembly-CSharp-firstpass.dll")
    decompile_dll("Assembly-CSharp.dll")
    
    apply_patch()
    create_sln()
    print("Decompilation complete.")

if __name__ == "__main__":
    main()