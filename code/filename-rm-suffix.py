import os

def remove_custom_suffix(root_dir, suffix, keyword):
    suffix_length = len(suffix)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if keyword and keyword.lower() in dirpath.lower():
            for filename in filenames:
                if filename.endswith(suffix):
                    file_path = os.path.join(dirpath, filename)
                    new_filename = filename[:-suffix_length]
                    new_file_path = os.path.join(dirpath, new_filename)
                    os.rename(file_path, new_file_path)
                    print(f"Renamed {file_path} to {new_file_path}")
        elif not keyword: 
            for filename in filenames:
                if filename.endswith(suffix):
                    file_path = os.path.join(dirpath, filename)
                    new_filename = filename[:-suffix_length]  # Remove the suffix
                    new_file_path = os.path.join(dirpath, new_filename)
                    os.rename(file_path, new_file_path)
                    print(f"Renamed {file_path} to {new_file_path}")

root_dir = input("Enter the root directory to start searching from: ")
suffix = input("Enter the suffix to remove (e.g., '.jpg'): ")
keyword = input("Enter the keyword to filter directories (leave blank for all files): ")

remove_custom_suffix(root_dir, suffix, keyword)
