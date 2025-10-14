def remove_lines_from_file(source_file, filter_file, output_file):
    # Read lines from filter_file and store them in a set for quick lookup
    with open(filter_file, 'r', encoding='utf-8') as filter_file_handle:
        filter_lines_set = set(line.strip() for line in filter_file_handle)

    # Read lines from source_file and filter out those that are in filter_file
    with open(source_file, 'r', encoding='utf-8') as source_file_handle:
        filtered_lines = [line for line in source_file_handle if line.strip() not in filter_lines_set]

    # Write the filtered lines to output_file
    with open(output_file, 'w', encoding='utf-8') as output_file_handle:
        output_file_handle.writelines(filtered_lines)

if __name__ == "__main__":
    source_file_path = input("Enter the path to the source text file: ")
    filter_file_path = input("Enter the path to the filter text file: ")
    output_file_path = input("Enter the path to the output text file: ")
    
    remove_lines_from_file(source_file_path, filter_file_path, output_file_path)
    print(f"Filtered lines written to '{output_file_path}'.")
