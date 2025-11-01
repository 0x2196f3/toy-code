import os

def merge_text_files_from_directory(input_directory, output_file_name):
    unique_lines_set = set()

    for filename in os.listdir(input_directory):
        if filename.endswith('.txt'):
            file_path = os.path.join(input_directory, filename)
            with open(file_path, 'r', encoding='utf-8') as text_file:
                for line in text_file:
                    unique_lines_set.add(line.strip())

    sorted_unique_lines = sorted(unique_lines_set)

    with open(output_file_name, 'w', encoding='utf-8') as output_file:
        for line in sorted_unique_lines:
            output_file.write(line + '\n')

if __name__ == "__main__":
    input_directory_path = input("Enter the directory containing the text files: ")
    output_file_name = input("Enter the name for the merged output file (e.g., merged.txt): ")
    merge_text_files_from_directory(input_directory_path, output_file_name)
    print(f"Merged file created as '{output_file_name}'.")
