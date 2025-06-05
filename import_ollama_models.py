import os
import zipfile
import shutil

# Define the paths
blobs_dir = './blobs'
manifests_dir = './manifests/registry.ollama.ai/library'

def is_llm_model_zip(zip_file_path):
    # Implement logic to determine if the zip file contains LLM models
    # For example, check for specific files or naming conventions
    with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
        # Check for the presence of a specific file that indicates it's an LLM model
        return any(file.endswith('.json') for file in zip_file.namelist())

def extract_zip_file(zip_file_path):
    # Create a directory for extraction based on the zip file name
    zip_filename = os.path.splitext(os.path.basename(zip_file_path))[0]
    extract_dir = os.path.join(manifests_dir, zip_filename)
    os.makedirs(extract_dir, exist_ok=True)

    # Extract the zip file
    with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
        zip_file.extractall(extract_dir)

    print(f"Extracted {zip_file_path} to {extract_dir}")

def main():
    # Walk through the current directory to find all zip files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.zip'):
                zip_file_path = os.path.join(root, file)
                if is_llm_model_zip(zip_file_path):
                    extract_zip_file(zip_file_path)
                else:
                    print(f"Skipping non-LLM model zip file: {zip_file_path}")

if __name__ == "__main__":
    main()
