import os

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

root_directory = './'

keywords_to_remove = ['Meitantei.Conan.1996.S01E0', '[Fabre-RAW] Detective Conan 0', ]  # Add your keywords here

for dirpath, dirnames, filenames in os.walk(root_directory):
    for dirname in dirnames:
        new_dirname = dirname
        
        for keyword in keywords_to_remove:
            new_dirname = new_dirname.replace(keyword, '')

        new_dirname = new_dirname.strip()

        if new_dirname != dirname:
            old_dir = os.path.join(dirpath, dirname)
            new_dir = os.path.join(dirpath, new_dirname)
            
            os.rename(old_dir, new_dir)
            print(f'Renamed directory: "{old_dir}" to "{new_dir}"')
            
    for filename in filenames:
        new_filename = filename
        
        for keyword in keywords_to_remove:
            new_filename = new_filename.replace(keyword, '')

        new_filename = new_filename.strip()

        if new_filename != filename:
            old_file = os.path.join(dirpath, filename)
            new_file = os.path.join(dirpath, new_filename)
            
            os.rename(old_file, new_file)
            print(f'Renamed: "{old_file}" to "{new_file}"')
