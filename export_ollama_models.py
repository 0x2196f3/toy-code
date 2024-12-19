import os
import json
import shutil
import zipfile
from concurrent.futures import ProcessPoolExecutor

# Define the paths
manifests_dir = './manifests/registry.ollama.ai/library'
blobs_dir = './blobs'

def process_json_file(json_file_path):
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Get the parent folder name
    parent_folder_name = os.path.basename(os.path.dirname(json_file_path))
    
    # Create a directory for the current JSON file
    json_filename = os.path.splitext(os.path.basename(json_file_path))[0]  # Remove .json extension
    temp_folder_name = f"{parent_folder_name}-{json_filename}"
    temp_folder_path = os.path.join('.', temp_folder_name)
    os.makedirs(temp_folder_path, exist_ok=True)

    # Extract the "layers" and copy the corresponding files
    if 'layers' in data:
        for layer in data['layers']:
            if 'digest' in layer:
                digest = layer['digest']
                # Replace ":" with "-" for the filename
                filename = digest.replace(":", "-")
                source_file_path = os.path.join(blobs_dir, filename)
                
                # Check if the source file exists and copy it
                if os.path.exists(source_file_path):
                    shutil.copy(source_file_path, temp_folder_path)
                else:
                    print(f"File {source_file_path} does not exist.")

    # Create a zip file from the folder with maximum compression
    zip_file_path = os.path.join('.', f"{temp_folder_name}.zip")
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
        # Add the JSON file to the zip
        zip_file.write(json_file_path, os.path.basename(json_file_path))  # Add JSON file to the zip
        
        # Add copied files to the zip
        for root, dirs, files in os.walk(temp_folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Add file to the zip file, preserving the directory structure
                zip_file.write(file_path, os.path.relpath(file_path, temp_folder_path))

    # Remove the temporary folder
    shutil.rmtree(temp_folder_path)

    print(f"Created zip file: {zip_file_path}")

def main():
    # Walk through the manifests directory to find all JSON files
    json_files = []
    for root, dirs, files in os.walk(manifests_dir):
        for file in files:
            # Check if the file is a JSON file (you can also check for valid JSON content if needed)
            json_files.append(os.path.join(root, file))

    # Use ProcessPoolExecutor to process JSON files in parallel
    with ProcessPoolExecutor() as executor:
        executor.map(process_json_file, json_files)

if __name__ == "__main__":
    main()
