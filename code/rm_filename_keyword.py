import os

# Define the root directory
root_directory = './'

# Define the keywords to remove
keywords_to_remove = ['big2048.com@', 'guochan2048.com', '[BT-btt.com]', '[ThZu.Cc]', ]  # Add your keywords here

# Walk through the directory and its subdirectories
for dirpath, dirnames, filenames in os.walk(root_directory):
    for dirname in dirnames:
        new_dirname = dirname
        
        # Remove keywords from the directory name
        for keyword in keywords_to_remove:
            new_dirname = new_dirname.replace(keyword, '')

        # Strip any leading or trailing whitespace that may result from the removal
        new_dirname = new_dirname.strip()

        # If the new directory name is different, rename the directory
        if new_dirname != dirname:
            # Get the full path for the old and new directory names
            old_dir = os.path.join(dirpath, dirname)
            new_dir = os.path.join(dirpath, new_dirname)
            
            # Rename the directory
            os.rename(old_dir, new_dir)
            print(f'Renamed directory: "{old_dir}" to "{new_dir}"')
            
    for filename in filenames:
        # Initialize a new filename
        new_filename = filename
        
        # Remove keywords from the filename
        for keyword in keywords_to_remove:
            new_filename = new_filename.replace(keyword, '')

        # Strip any leading or trailing whitespace that may result from the removal
        new_filename = new_filename.strip()

        # If the new filename is different, rename the file
        if new_filename != filename:
            # Get the full path for the old and new filenames
            old_file = os.path.join(dirpath, filename)
            new_file = os.path.join(dirpath, new_filename)
            
            # Rename the file
            os.rename(old_file, new_file)
            print(f'Renamed: "{old_file}" to "{new_file}"')
