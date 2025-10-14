import os

# Define the root directory
root_directory = './'

# Define a mapping of keywords to replacement values.
# For each file, any occurrence of a key in its name will be replaced by the associated value.
keyword_to_replace = {
    'big2048.com@': '',       # Replace with an empty string
    'guochan2048.com': 'example',  # Replace with "example"
    '[BT-btt.com]': 'text',    # Replace with "text"
    '[ThZu.Cc]': 'value'       # Replace with "value"
}

# Walk through the directory and its subdirectories
for dirpath, dirnames, filenames in os.walk(root_directory):
    # Process filenames for replacement
    for filename in filenames:
        new_filename = filename
        
        # Replace each keyword according to the mapping
        for keyword, replacement in keyword_to_replace.items():
            new_filename = new_filename.replace(keyword, replacement)
        
        # Strip unwanted leading or trailing whitespace that may result from the replacement
        new_filename = new_filename.strip()
        
        # If the filename has changed, perform the renaming
        if new_filename != filename:
            old_file = os.path.join(dirpath, filename)
            new_file = os.path.join(dirpath, new_filename)
            
            try:
                os.rename(old_file, new_file)
                print(f'Renamed file: "{old_file}" to "{new_file}"')
            except Exception as e:
                print(f'Error renaming file "{old_file}" to "{new_file}": {e}')
