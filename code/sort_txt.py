import locale

def sort_and_clean_file(file_path):
    def read_lines_with_fallback(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.readlines(), 'utf-8'
        except UnicodeDecodeError:
            with open(path, 'r', encoding='gbk') as f:
                return f.readlines(), 'gbk'

    try:
        lines, used_enc = read_lines_with_fallback(file_path)

        # Remove empty lines and strip whitespace
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        # Sort case-insensitively but preserve original casing
        cleaned_lines.sort(key=lambda s: s.casefold())

        # Write the sorted lines back to the file using the same encoding that succeeded
        with open(file_path, 'w', encoding=used_enc) as file:
            for line in cleaned_lines:
                file.write(line + '\n')

        print(f"File sorted and cleaned successfully (read using {used_enc}).")

    except FileNotFoundError:
        print("The specified file was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    file_path = input("Enter the path to the text file: ")
    sort_and_clean_file(file_path)
