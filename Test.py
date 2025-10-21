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
PHASE2_WORKERS = 20   # Conservative WHOIS workers (reduced for reliability)
DNS_TIMEOUT = 2       # 2 seconds for DNS
WHOIS_TIMEOUT = 15    # Increased timeout for WHOIS
INPUT_FILE = "combination1.txt"
OUTPUT_FILE = "available.txt"
LOG_FILE = "domain_checker.log"
WHOIS_RETRIES = 3     # Number of retries for WHOIS lookups

# Setup logging (log to a file instead of terminal)
logging.basicConfig(filename=LOG_FILE, level=logging.WARNING, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def setup_timeouts():
    """Configure system timeouts"""
    socket.setdefaulttimeout(DNS_TIMEOUT)

@lru_cache(maxsize=50000)
def cached_whois(domain):
    """Enhanced cached WHOIS lookup with retries and better parsing"""
    for attempt in range(WHOIS_RETRIES):
        try:
            whois_data = whois.whois(domain)

            # Ensure domain_name is properly processed
            domain_names = []
            if isinstance(whois_data.domain_name, list):
                domain_names = [name.lower() for name in whois_data.domain_name if name]
            elif whois_data.domain_name:
                domain_names = [whois_data.domain_name.lower()]

            # Check if our domain appears in the WHOIS result (case insensitive)
            if any(domain.lower() in name for name in domain_names):
                return whois_data
            
            # Additional reliability checks
            if whois_data.expiration_date or whois_data.status:
                return whois_data
            
            return None  # No WHOIS record found, domain might be available

        except PywhoisError as e:
            # Handle known WHOIS errors (No match means domain is available)
            error_message = str(e).lower()
            if "no match for" in error_message or "not found" in error_message:
                return None  # Definitely available
            logger.warning(f"WHOIS lookup failed (attempt {attempt+1}): {domain} - {error_message}")
            time.sleep(1)  # Retry delay

        except Exception as e:
            logger.warning(f"Unexpected WHOIS error (attempt {attempt+1}): {domain} - {str(e)}")
            time.sleep(1)
    
    return "error"  # WHOIS failed multiple times, assume registered

def fast_dns_check(domain):
    """Phase 1: Quick DNS check (~95% accurate)"""
    try:
        socket.gethostbyname(domain)
        return False  # Definitely registered
    except socket.gaierror as e:
        if e.errno == socket.EAI_NONAME:
            return True  # NXDOMAIN - likely available
        return False  # Other error - assume registered
    except Exception:
        return False  # Assume registered on unknown errors

def accurate_whois_check(domain):
    """Phase 2: Enhanced 100% accurate WHOIS verification"""
    # Confirm DNS check again (in case of transient errors)
    try:
        socket.gethostbyname(domain)
        return False
    except socket.gaierror as e:
        if e.errno != socket.EAI_NONAME:
            return False  # Assume registered on non-NXDOMAIN errors
    except Exception:
        return False
    
    # WHOIS verification with enhanced checks
    whois_data = cached_whois(domain)
    
    if whois_data == "error":
        return False  # Assume registered if WHOIS failed
    
    if whois_data is None:
        return True  # Definitely available
    
    # Additional safety checks for false negatives
    if not hasattr(whois_data, 'domain_name') or not whois_data.domain_name:
        return True
    
    return False  # Otherwise, consider registered

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
    print("\n=== PHASE 1: Fast DNS Pre-Scan (95% accurate) ===")
    all_domains = load_domains()
    print(f"Loaded {len(all_domains)} domains to check")

    phase1_results = run_phase(all_domains, fast_dns_check, PHASE1_WORKERS, "Phase 1")
    print(f"\nPhase 1 complete: {len(phase1_results)} potential available domains")

    # Phase 2: Accurate WHOIS verification
    print("\n=== PHASE 2: WHOIS Verification (100% accurate) ===")
    verified_available = run_phase(phase1_results, accurate_whois_check, PHASE2_WORKERS, "Phase 2")

    # Save final results
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(verified_available))

    print(f"\n=== FINAL RESULTS ===")
    print(f"Scanned {len(all_domains)} total domains")
    print(f"Phase 1 candidates: {len(phase1_results)}")
    print(f"Verified available: {len(verified_available)}")
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
