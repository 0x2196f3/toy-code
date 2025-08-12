import sys
import re

def remove_single_line_comments(file_path, comment_symbol):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Regular expression to match single-line comments
    comment_pattern = re.compile(rf'\s*{re.escape(comment_symbol)}.*')

    # Remove single-line comments
    cleaned_lines = []
    for line in lines:
        cleaned_line = comment_pattern.sub('', line)
        cleaned_lines.append(cleaned_line)

    # Write the cleaned lines back to the file or to a new file
    output_file_path = f'{file_path}.cleaned'
    with open(output_file_path, 'w') as output_file:
        output_file.writelines(cleaned_lines)

    print(f"Single-line comments removed. Cleaned code saved to: {output_file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 rm_code_comments.py <file_path> <comment_symbol>")
        sys.exit(1)

    file_path = sys.argv[1]
    comment_symbol = sys.argv[2]

    remove_single_line_comments(file_path, comment_symbol)
