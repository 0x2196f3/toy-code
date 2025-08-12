import os
import argparse

# Map of common text formats and their single line comment symbols
comment_symbols = {
    'python': '#',
    'java': '//',
    'c': '//',
    'cpp': '//',
    'javascript': '//',
    'ruby': '#',
    'php': '//',
    'perl': '#',
    'swift': '//',
    'go': '//',
    'rust': '//',
    'sql': '--',
    'ini': ';',
    'tpl': '#',
    'yaml': '#',
    'yml': '#',
    'json': '//',  # Note: JSON does not officially support comments, but some parsers may allow them
    'list': '#',
    'txt': '#'
}

def remove_comments_and_empty_lines(file_path, file_format):
    """
    Removes all comment lines and empty lines from an input text file.

    Args:
        file_path (str): Path to the input text file.
        file_format (str): Format of the input text file.

    Returns:
        str: The input text with all comment lines and empty lines removed.
    """
    comment_symbol = comment_symbols.get(file_format.lower())
    if comment_symbol is None:
        raise ValueError(f"Unsupported file format: {file_format}")

    with open(file_path, 'r') as file:
        lines = file.readlines()

    cleaned_lines = [line for line in lines if line.strip() and not line.strip().startswith(comment_symbol)]

    return ''.join(cleaned_lines)


def overwrite_file(file_path, content):
    """
    Overwrites the content of a file.

    Args:
        file_path (str): Path to the file.
        content (str): New content to be written.
    """
    with open(file_path, 'w') as file:
        file.write(content)


def process_file(file_path, file_format):
    try:
        cleaned_content = remove_comments_and_empty_lines(file_path, file_format)
        overwrite_file(file_path, cleaned_content)
        print(f"Comments and empty lines removed from {file_path}")
    except ValueError as e:
        print(e)


def process_folder(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_format = os.path.splitext(file)[1][1:].lower()
            if file_format in comment_symbols:
                process_file(file_path, file_format)


def main():
    parser = argparse.ArgumentParser(description="Remove comments and empty lines from text files")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively search for text files in the folder")
    args = parser.parse_args()

    path = input("Enter the file or folder path: ")

    if args.recursive:
        process_folder(path)
    else:
        file_format = input("Enter the file format (e.g., python, java, txt, etc.): ")
        process_file(path, file_format)


if __name__ == '__main__':
    main()

