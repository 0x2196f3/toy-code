import os

# Define the directory
directory = './'

# Iterate over all files in the directory
for filename in os.listdir(directory):
    # Initialize a new filename
    new_filename = ''
    skip = False  # Flag to indicate if we are inside brackets

    for char in filename:
        if char == '[':
            skip = True  # Start skipping characters
        elif char == ']':
            skip = False  # Stop skipping characters
        elif not skip:
            new_filename += char  # Add character to new filename if not skipping

    # If the new filename is different, rename the file
    if new_filename != filename:
        # Get the full path for the old and new filenames
        old_file = os.path.join(directory, filename)
        new_file = os.path.join(directory, new_filename)
        
        # Rename the file
        os.rename(old_file, new_file)
        print(f'Renamed: "{filename}" to "{new_filename}"')
