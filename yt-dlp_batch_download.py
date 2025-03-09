import subprocess

# Path to your file with URLs (one URL per line)
file_path = "./urls.txt"

# Base command template. We use a placeholder {url} to substitute the URL from the file.
# The original base string is:
# .\yt-dlp.exe "https://www.youtube.com/watch?v=xxxxxxxxx" --cookies-from-browser firefox
# We replace the URL portion with {url}
command_template = r'.\yt-dlp.exe "{url}" --cookies-from-browser firefox'

def run_command(command):
    print(f"Running command: {command}")
    # Open the subprocess with stdout and stderr piped
    # Merging stderr into stdout so that we only have one stream to read from
    process = subprocess.Popen(
        ["powershell", "-Command", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Stream the output line by line in real time
    with process.stdout:
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
    # Wait for the process to terminate and get the exit code
    process.wait()
    print(f"Completed with exit code: {process.returncode}\n")

def run_commands_from_file(filepath):
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Process each URL (skip empty lines or whitespace only)
    for line in lines:
        url = line.strip()
        if not url:
            continue

        # Replace the placeholder with current URL
        command = command_template.format(url=url)
        run_command(command)
        time.sleep(30)

if __name__ == "__main__":
    run_commands_from_file(file_path)
