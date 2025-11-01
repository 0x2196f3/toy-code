import os

source_dir = './'
dest_dir = './empty'

os.makedirs(dest_dir, exist_ok=True)

for filename in os.listdir(source_dir):
    source_path = os.path.join(source_dir, filename)
    
    if os.path.isfile(source_path):
        if os.path.getsize(source_path) > 0:
            dest_path = os.path.join(dest_dir, filename)
            with open(dest_path, 'w'):
                pass
            print(f"Created empty file: {dest_path}")
        else:
            print(f"Skipped empty file: {source_path}")
