import os
import csv
from typing import List, Dict

from crawl4ai.proxy_strategy import ProxyConfig


PROXIES_CONFIG = 'src/core/services/web_crawler/proxies.csv'


def load_proxies_config() -> List[str]:
    """
    Load proxies from a CSV file into environment variables.
    
    Expected CSV format:
    ip:port:username:password
    
    Environment variables set:
    - PROXIES: Comma-separated list of all proxies
    - PROXY_COUNT: Total number of proxies available
    
    Returns:
        List[str]: List of proxy strings in format "ip:port:username:password"
    """
    proxies = []
    
    if not os.path.exists(PROXIES_CONFIG):
        raise FileNotFoundError(f"Proxy CSV file not found: {PROXIES_CONFIG}")
    
    with open(PROXIES_CONFIG, 'r') as f:
        for idx, line in enumerate(f):
            parts = line.strip().split(':')
            if len(parts) == 4:
                ip, port, user, passwd = parts[0], parts[1], parts[2], parts[3]
                proxies.append(f"{ip}:{port}:{user}:{passwd}")
            else:
                raise ValueError(f"Invalid Proxies at row: {idx} - Expected 4 values, Got {len(parts)}")
    
    
    os.environ["PROXIES"] = ','.join(proxies)
    # Set the total count of proxies in environment
    os.environ["PROXY_COUNT"] = str(len(proxies))
    
    return proxies

# if __name__ == "__main__":
#     proxies_cfg = load_proxies_config()
#     proxies = _load_csv('src/core/services/web_crawler/proxies.csv')
#     print()