import os

def remove_empty_files(directory):
    # Walk through the directory
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            # Check if the file is empty
            if os.path.isfile(file_path) and os.path.getsize(file_path) == 0:
                print(f'Removing empty file: {file_path}')
                os.remove(file_path)

# Specify the directory you want to clean up
directory_to_clean = './'
remove_empty_files(directory_to_clean)
