import itertools
import string

def generate_combinations(limit=5, filename="every_words.txt"):
    letters = string.ascii_lowercase  # "abcdefghijklmnopqrstuvwxyz"
    
    with open(filename, "w") as file:
        for length in range(1, limit + 1):  # Generate words from length 1 to limit
            for combination in itertools.product(letters, repeat=length):
                word = "".join(combination)
                file.write(word + "\n")
    
    print(f"Combinations saved to {filename}")

# Run the function
generate_combinations()
