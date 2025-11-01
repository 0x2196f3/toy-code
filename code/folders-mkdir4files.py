import os
import shutil

current_directory = "./"

for filename in os.listdir(current_directory):
    if os.path.isfile(os.path.join(current_directory, filename)) and filename != "mkdir4files.py":
        folder_name = os.path.splitext(filename)[0]
        folder_path = os.path.join(current_directory, folder_name)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        shutil.move(os.path.join(current_directory, filename), os.path.join(folder_path, filename))

print("Files have been organized into folders.")
