import os

# Define the root directory
root_directory = './'

wrapper = ["(", ")"]

# Walk through the directory and its subdirectories
for dirpath, dirnames, filenames in os.walk(root_directory):
    for filename in filenames:
        # Initialize a new filename
        new_filename = ''
        skip = False  # Flag to indicate if we are inside brackets

        for char in filename:
            if char == wrapper[0]:
                skip = True  # Start skipping characters
            elif char == wrapper[1]:
                skip = False  # Stop skipping characters
            elif not skip:
                new_filename += char  # Add character to new filename if not skipping

        # If the new filename is different, rename the file
        if new_filename != filename:
            # Get the full path for the old and new filenames
            old_file = os.path.join(dirpath, filename)
            new_file = os.path.join(dirpath, new_filename)
            
            # Rename the file
            os.rename(old_file, new_file)
            print(f'Renamed: "{old_file}" to "{new_file}"')
            
input()
