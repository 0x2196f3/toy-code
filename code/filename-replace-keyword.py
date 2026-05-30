import os

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

root_directory = './'

keyword_to_replace = {
    'big2048.com@': '',
    'guochan2048.com': 'example',
    '[BT-btt.com]': 'text',
    '[ThZu.Cc]': 'value'
}

for dirpath, dirnames, filenames in os.walk(root_directory):
    for filename in filenames:
        new_filename = filename
        
        for keyword, replacement in keyword_to_replace.items():
            new_filename = new_filename.replace(keyword, replacement)
        
        new_filename = new_filename.strip()
        
        if new_filename != filename:
            old_file = os.path.join(dirpath, filename)
            new_file = os.path.join(dirpath, new_filename)
            
            try:
                os.rename(old_file, new_file)
                print(f'Renamed file: "{old_file}" to "{new_file}"')
            except Exception as e:
                print(f'Error renaming file "{old_file}" to "{new_file}": {e}')
