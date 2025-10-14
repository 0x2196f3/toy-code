import os

FILE_NAME = ".DS_Store"

def remove_ds_store_files(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == FILE_NAME:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f'Removed: {file_path}')
                except Exception as e:
                    print(f'Error removing {file_path}: {e}')

if __name__ == "__main__":
    current_directory = "./"
    remove_ds_store_files(current_directory)
