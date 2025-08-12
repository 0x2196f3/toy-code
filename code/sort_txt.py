def sort_and_clean_file(file_path):
    try:
        # Read the lines from the file
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Remove empty lines and strip whitespace
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        # Sort the lines
        cleaned_lines.sort()

        # Write the sorted lines back to the file
        with open(file_path, 'w') as file:
            for line in cleaned_lines:
                file.write(line + '\n')

        print("File sorted and cleaned successfully.")

    except FileNotFoundError:
        print("The specified file was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    file_path = input("Enter the path to the text file: ")
    sort_and_clean_file(file_path)
