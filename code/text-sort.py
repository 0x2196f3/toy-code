import locale
import argparse
from typing import List, Tuple


def sort_and_clean_file(lines: List[str], encoding: str) -> List[str]:
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    cleaned_lines.sort(key=lambda s: s.casefold())

    return cleaned_lines


def read_lines_with_fallback(path: str) -> Tuple[List[str], str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines(), "utf-8"
    except UnicodeDecodeError:
        with open(path, "r", encoding="gbk") as f:
            return f.readlines(), "gbk"


def write_lines(path: str, lines: List[str], encoding: str) -> None:
    with open(path, "w", encoding=encoding) as f:
        for line in lines:
            f.write(line + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort and clean a text file.")
    parser.add_argument("--file", "-f", help="Path to the text file (optional).")
    args = parser.parse_args()

    if args.file:
        file_path = args.file
    else:
        file_path = input("Enter the path to the text file: ")

    try:
        lines, used_enc = read_lines_with_fallback(file_path)
        result_lines = sort_and_clean_file(lines, used_enc)
        write_lines(file_path, result_lines, used_enc)
        print(f"File sorted and cleaned successfully (read using {used_enc}).")
    except FileNotFoundError:
        print("The specified file was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
