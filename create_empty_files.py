import os

# Define source and destination directories
source_dir = './empty'
dest_dir = './'

# Ensure destination directory exists
os.makedirs(dest_dir, exist_ok=True)

# Iterate over all entries in the source directory
for filename in os.listdir(source_dir):
    source_path = os.path.join(source_dir, filename)
    
    # Process only files (skip directories)
    if os.path.isfile(source_path):
        # Check if file is non-empty
        if os.path.getsize(source_path) > 0:
            dest_path = os.path.join(dest_dir, filename)
            # Create an empty file in destination
            with open(dest_path, 'w'):
                pass  # Just opening in write mode creates an empty file
            print(f"Created empty file: {dest_path}")
        else:
            print(f"Skipped empty file: {source_path}")
