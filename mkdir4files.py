import os
import shutil

# Get the current directory
current_directory = "./"

# Loop through all files in the current directory
for filename in os.listdir(current_directory):
    # Check if it's a file (not a directory)
    if os.path.isfile(os.path.join(current_directory, filename)) and filename != "mkdir4files.py":
        # Remove the file extension to create the folder name
        folder_name = os.path.splitext(filename)[0]
        folder_path = os.path.join(current_directory, folder_name)

        # Create the folder if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Move the file into the newly created folder
        shutil.move(os.path.join(current_directory, filename), os.path.join(folder_path, filename))

print("Files have been organized into folders.")
