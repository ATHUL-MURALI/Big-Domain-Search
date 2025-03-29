import re

def extract_words_with_pet(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        text = infile.read()
        words = re.findall(r'\b\w*built\w*\b', text, re.IGNORECASE)
        outfile.write('\n'.join(words))

# Usage
input_filename = 'every_verified_available.txt'
output_filename = 'extracted.txt'
extract_words_with_pet(input_filename, output_filename)