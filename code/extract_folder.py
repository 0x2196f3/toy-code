import os
import shutil

# Get the current directory
current_directory = './'

# List all items in the current directory
for item in os.listdir(current_directory):
    item_path = os.path.join(current_directory, item)
    
    # Check if the item is a directory
    if os.path.isdir(item_path):
        # List all files in the directory
        for file_name in os.listdir(item_path):
            source_file = os.path.join(item_path, file_name)
            destination_file = os.path.join(current_directory, file_name)
            
            # Check if the file already exists in the destination
            if not os.path.exists(destination_file):
                # Copy the file to the current directory
                shutil.move(source_file, destination_file)
                print(f'Moved: {source_file} to {destination_file}')
            else:
                print(f'Skipped (already exists): {destination_file}')
