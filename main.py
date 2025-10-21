import whois
import concurrent.futures
import socket
import time
from functools import lru_cache
import logging
from whois.parser import PywhoisError
from tqdm import tqdm

# Configuration
PHASE1_WORKERS = 100  # Fast DNS workers
DNS_TIMEOUT = 2       # 2 seconds for DNS
INPUT_FILE = "anim.txt"
OUTPUT_FILE = "anima.txt"
LOG_FILE = "domain_checker.log"

# Setup logging (log to a file instead of terminal)
logging.basicConfig(filename=LOG_FILE, level=logging.WARNING, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def setup_timeouts():
    """Configure system timeouts"""
    socket.setdefaulttimeout(DNS_TIMEOUT)

def fast_dns_check(domain):
    """Phase 1: Quick DNS check (~95% accurate)"""
    try:
        socket.gethostbyname(domain)
        return False  # Definitely registered
    except socket.gaierror as e:
        if e.errno == socket.EAI_NONAME:
            return True  # NXDOMAIN - likely available
        return False  # Other error - assume registered
    except:
        return False  # Assume registered on other errors

def load_domains():
    """Load and filter domains from input file, only allowing alphabetic words with no spaces"""
    with open(INPUT_FILE, "r") as f:
        return [f"{word.strip()}.com" for word in f if word.strip().isalpha() and " " not in word.strip()]

def run_phase(domains, check_func, workers, phase_name):
    """Run a checking phase with efficient progress tracking using tqdm"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_domain = {executor.submit(check_func, domain): domain for domain in domains}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_domain), total=len(domains), desc=phase_name):
            domain = future_to_domain[future]
            try:
                if future.result():
                    results.append(domain)
            except Exception as e:
                logger.error(f"Error checking {domain}: {str(e)}")
    
    return results

def main():
    setup_timeouts()
    
    # Phase 1: Fast DNS pre-scan
    print("\n=== PHASE 1: Fast DNS Pre-Scan ===")
    all_domains = load_domains()
    print(f"Loaded {len(all_domains)} domains to check")
    
    phase1_results = run_phase(all_domains, fast_dns_check, PHASE1_WORKERS, "Phase 1")
    print(f"\nPhase 1 complete: {len(phase1_results)} potential available domains")
    
    # Save Phase 1 results to file
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(phase1_results))
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Scanned {len(all_domains)} total domains")
    print(f"Available (Phase 1 only): {len(phase1_results)}")
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
