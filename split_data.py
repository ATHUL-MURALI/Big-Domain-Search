def split_file(filename, num_parts):
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    total_lines = len(lines)
    lines_per_part = total_lines // num_parts
    extra_lines = total_lines % num_parts
    
    start = 0
    for i in range(1, num_parts + 1):
        end = start + lines_per_part + (1 if i <= extra_lines else 0)
        with open(f'combination{i}.txt', 'w', encoding='utf-8') as output_file:
            output_file.writelines(lines[start:end])
        start = end

if __name__ == "__main__":
    num_pieces = int(13)
    split_file("combinations.txt", num_pieces)
