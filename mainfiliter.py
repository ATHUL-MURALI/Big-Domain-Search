import re

INPUT_FILE = "available9.txt"
OUTPUT_FILE = "filter9.txt"

# Define keywords you care about
KEYWORDS = ["ai", "tech", "data"]

def is_pronounceable(name: str) -> bool:
    """Check if the domain looks pronounceable (has vowels, not weird clusters)."""
    return (
        bool(re.search(r"[aeiou]", name))  # must have at least one vowel
        and not re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", name)  # avoid 4+ consonants in a row
    )

def load_domains(file_path: str):
    """Load domain names from file."""
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def filter_domains(domains):
    """Apply filtering rules."""
    return [
        d for d in domains
        if 3 <= len(d.replace(".com", "")) <= 8
        and is_pronounceable(d.replace(".com", ""))
        # and any(k in d for k in KEYWORDS)
    ]

def save_domains(domains, file_path: str):
    """Save filtered domains to file."""
    with open(file_path, "w") as f:
        f.write("\n".join(domains))

def main():
    print("Loading domains from", INPUT_FILE)
    domains = load_domains(INPUT_FILE)

    print(f"Total domains loaded: {len(domains)}")

    filtered = filter_domains(domains)

    print(f"Filtered domains: {len(filtered)}")
    save_domains(filtered, OUTPUT_FILE)

    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
