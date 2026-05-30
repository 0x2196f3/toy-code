import os

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)


root_directory = './'

wrapper = ["(", ")"]

for dirpath, dirnames, filenames in os.walk(root_directory):
    for filename in filenames:
        new_filename = ''
        skip = False

        for char in filename:
            if char == wrapper[0]:
                skip = True
            elif char == wrapper[1]:
                skip = False
            elif not skip:
                new_filename += char

        if new_filename != filename:
            old_file = os.path.join(dirpath, filename)
            new_file = os.path.join(dirpath, new_filename)
            
            os.rename(old_file, new_file)
            print(f'Renamed: "{old_file}" to "{new_file}"')
            
input()
