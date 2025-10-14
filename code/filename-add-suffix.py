import os

def add_custom_suffix(root_dir, suffix, keyword):
    """
    Adds a specified suffix to all files in directories that contain the given keyword in their path.
    If no keyword is provided, the suffix is added to all files in the root directory.

    Parameters:
    - root_dir (str): The root directory to start searching from.
    - suffix (str): The suffix to add to the filenames (e.g., '.jpg').
    - keyword (str): The keyword to filter directories (only directories containing this keyword will be processed).
    """
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # If a keyword is provided, check if it's in the current directory path
        if keyword and keyword.lower() in dirpath.lower():
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                new_filename = filename + suffix
                new_file_path = os.path.join(dirpath, new_filename)
                os.rename(file_path, new_file_path)
                print(f"Renamed {file_path} to {new_file_path}")
        elif not keyword:  # If no keyword is provided, apply suffix to all files
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                new_filename = filename + suffix
                new_file_path = os.path.join(dirpath, new_filename)
                os.rename(file_path, new_file_path)
                print(f"Renamed {file_path} to {new_file_path}")

# Get user input for the root directory, suffix, and keyword
root_dir = input("Enter the root directory to start searching from: ")
suffix = input("Enter the suffix to add (e.g., '.jpg'): ")
keyword = input("Enter the keyword to filter directories (leave blank for all files): ")

add_custom_suffix(root_dir, suffix, keyword)
