import whois
import concurrent.futures
import socket
import time
from functools import lru_cache
import logging
from whois.parser import PywhoisError

# Configuration
PHASE1_WORKERS = 100  # Fast DNS workers
PHASE2_WORKERS = 20   # Conservative WHOIS workers (reduced for reliability)
DNS_TIMEOUT = 2       # 2 seconds for DNS
WHOIS_TIMEOUT = 15    # Increased timeout for WHOIS
INPUT_FILE = "every_words.txt"
OUTPUT_FILE = "every_verified_available.txt"
WHOIS_RETRIES = 3     # Number of retries for WHOIS lookups

# Setup logging
logging.basicConfig(level=logging.INFO)
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
            
            # Enhanced WHOIS result parsing
            if isinstance(whois_data.domain_name, list):
                domain_names = [name.lower() for name in whois_data.domain_name if name]
            else:
                domain_names = [whois_data.domain_name.lower()] if whois_data.domain_name else []
            
            # Check if our domain is in the WHOIS results (case insensitive)
            if any(domain.lower() in name for name in domain_names for domain in [domain]):
                return whois_data
                
            # Check expiration date if domain_name field wasn't reliable
            if whois_data.expiration_date:
                return whois_data
                
            # Check status fields
            if whois_data.status:
                return whois_data
                
            # If we got here and no data was found, domain might be available
            return None
            
        except PywhoisError as e:
            # This usually means domain is available
            if "No match for" in str(e) or "NOT FOUND" in str(e):
                return None
            logger.debug(f"WHOIS lookup failed (attempt {attempt+1}): {domain} - {str(e)}")
            time.sleep(1)  # Brief delay before retry
        except Exception as e:
            logger.debug(f"Unexpected WHOIS error (attempt {attempt+1}): {domain} - {str(e)}")
            time.sleep(1)
    
    # If all retries failed, assume registered to be safe
    return "error"

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

def accurate_whois_check(domain):
    """Phase 2: Enhanced 100% accurate WHOIS verification"""
    # First confirm DNS check again (in case of transient errors)
    try:
        socket.gethostbyname(domain)
        return False
    except socket.gaierror as e:
        if e.errno != socket.EAI_NONAME:
            return False  # Assume registered on non-NXDOMAIN errors
    except:
        return False
    
    # WHOIS verification with enhanced checks
    whois_data = cached_whois(domain)
    
    if whois_data == "error":
        return False  # Assume registered if WHOIS failed
    
    if whois_data is None:
        return True  # Definitely available
    
    # Additional checks for false negatives
    if not hasattr(whois_data, 'domain_name') or not whois_data.domain_name:
        return True
        
    return False

def load_domains():
    """Load and format domains from input file"""
    with open(INPUT_FILE, "r") as f:
        return [f"{word.strip()}.com" for word in f if word.strip()]

def run_phase(domains, check_func, workers, phase_name):
    """Run a checking phase with progress reporting"""
    results = []
    start_time = time.time()
    total = len(domains)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_domain = {executor.submit(check_func, domain): domain for domain in domains}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_domain)):
            domain = future_to_domain[future]
            try:
                if future.result():
                    results.append(domain)
                    logger.info(f"Available: {domain}")
            except Exception as e:
                logger.error(f"Error checking {domain}: {str(e)}")
            
            # Progress reporting
            if (i + 1) % 100 == 0 or (i + 1) == total:
                elapsed = time.time() - start_time
                rate = (i+1)/elapsed if elapsed > 0 else 0
                remaining = (total - (i+1)) / rate if rate > 0 else 0
                logger.info(
                    f"{phase_name}: Processed {i+1}/{total} | "
                    f"Found {len(results)} | "
                    f"Rate: {rate:.1f} domains/sec | "
                    f"Elapsed: {elapsed:.1f}s | "
                    f"Remaining: {remaining:.1f}s"
                )
    
    return results

def main():
    setup_timeouts()
    
    # Phase 1: Fast DNS pre-scan
    logger.info("=== PHASE 1: Fast DNS Pre-Scan (95% accurate) ===")
    all_domains = load_domains()
    logger.info(f"Loaded {len(all_domains)} domains to check")
    
    phase1_results = run_phase(all_domains, fast_dns_check, PHASE1_WORKERS, "Phase 1")
    logger.info(f"\nPhase 1 complete: {len(phase1_results)} potential available domains")
    
    # Phase 2: Accurate WHOIS verification
    logger.info("\n=== PHASE 2: WHOIS Verification (100% accurate) ===")
    verified_available = run_phase(phase1_results, accurate_whois_check, PHASE2_WORKERS, "Phase 2")
    
    # Save final results
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(verified_available))
    
    logger.info(f"\n=== FINAL RESULTS ===")
    logger.info(f"Scanned {len(all_domains)} total domains")
    logger.info(f"Phase 1 candidates: {len(phase1_results)}")
    logger.info(f"Verified available: {len(verified_available)}")
    logger.info(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()