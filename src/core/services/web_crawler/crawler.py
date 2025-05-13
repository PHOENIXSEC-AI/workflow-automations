import asyncio
import chromadb

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, RoundRobinProxyStrategy
from crawl4ai.proxy_strategy import ProxyConfig
from typing import List, Dict, Optional

from core.services.web_crawler.proxy import load_proxies_config

CONTENT_STORAGE = '.workflow-automation/data/chroma'

client = chromadb.PersistentClient(path=CONTENT_STORAGE)

async def crawl_with_proxy_rotation(urls: List[str]):
    """
    Crawl multiple URLs with proxy rotation
    """
    # Proxies defined in CSV file are loaded in ENV
    load_proxies_config()

    proxy_configs = ProxyConfig.from_env()
    # Set up proxy rotation using ProxyConfig
    proxy_strategy = RoundRobinProxyStrategy(proxy_configs)
    
    # Create browser and run configs
    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(proxy_rotation_strategy=proxy_strategy)
    
    # Create crawler and run
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        results = await crawler.arun_many(urls=urls, config=run_cfg)
        return results

# async def main():
#     # Example: Using proxy rotation
#     urls = ["https://httpbin.org/ip"] * 6
#     results = await crawl_with_proxy_rotation(urls)
    
#     for i, result in enumerate(results):
#         if result.success:
#             print(f"\nURL {i+1} result:", result.markdown[:100] + "...")
#         else:
#             print(f"\nURL {i+1} error:", result.error_message)

# if __name__ == "__main__":
#     # Run the async main function
#     asyncio.run(main())