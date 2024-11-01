import subprocess
import os
import shutil
# Get the absolute path to the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, "content")):
    shutil.rmtree(os.path.join(current_dir, "content"))
# Path to the download_anime.py script
script_path = os.path.join(current_dir, "download.py")

# Read URLs from the file
urls = []
with open("urls.txt", "r") as f:
    urls = f.read().splitlines()

# Construct the command to open multiple tabs
commands = []
for url in urls:
    commands.append(f'cmd /k python {script_path} {url}')

os.chdir(current_dir)

# Join the commands with the `;` separator
final = ''
for command in commands:
    final = f'{final}wt -w 0 nt {command}; '
final = final.strip('; ')
# Run the command in Windows Terminal
subprocess.Popen(final)