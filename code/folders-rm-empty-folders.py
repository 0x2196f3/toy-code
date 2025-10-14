import os

def remove_empty_folders(path):
    # Walk through the directory
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        for dirname in dirnames:
            folder_path = os.path.join(dirpath, dirname)
            try:
                # Attempt to remove the directory
                os.rmdir(folder_path)
                print(f'Removed empty folder: {folder_path}')
            except OSError:
                # If the directory is not empty, an error will be raised
                pass

if __name__ == "__main__":
    remove_empty_folders(os.path.dirname(os.path.abspath(__file__)))
    print("done")
    input()
