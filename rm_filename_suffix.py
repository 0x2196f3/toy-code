import os

def remove_custom_suffix(root_dir, suffix, keyword):
    """
    Removes a specified suffix from all files in directories that contain the given keyword in their path.
    If no keyword is provided, the suffix is removed from all files in the root directory.

    Parameters:
    - root_dir (str): The root directory to start searching from.
    - suffix (str): The suffix to remove from the filenames (e.g., '.jpg').
    - keyword (str): The keyword to filter directories (only directories containing this keyword will be processed).
    """
    suffix_length = len(suffix)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if keyword and keyword.lower() in dirpath.lower():
            for filename in filenames:
                if filename.endswith(suffix):
                    file_path = os.path.join(dirpath, filename)
                    new_filename = filename[:-suffix_length]  # Remove the suffix
                    new_file_path = os.path.join(dirpath, new_filename)
                    os.rename(file_path, new_file_path)
                    print(f"Renamed {file_path} to {new_file_path}")
        elif not keyword:  # If no keyword is provided, remove suffix from all files
            for filename in filenames:
                if filename.endswith(suffix):
                    file_path = os.path.join(dirpath, filename)
                    new_filename = filename[:-suffix_length]  # Remove the suffix
                    new_file_path = os.path.join(dirpath, new_filename)
                    os.rename(file_path, new_file_path)
                    print(f"Renamed {file_path} to {new_file_path}")

# Get user input for the root directory, suffix, and keyword
root_dir = input("Enter the root directory to start searching from: ")
suffix = input("Enter the suffix to remove (e.g., '.jpg'): ")
keyword = input("Enter the keyword to filter directories (leave blank for all files): ")

remove_custom_suffix(root_dir, suffix, keyword)
