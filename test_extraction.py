
from crawler.price_crawler import PoolPriceCrawler

def test():
    crawler = PoolPriceCrawler()
    # Test with a known pool website
    url = "https://www.gangnam.go.kr/office/gnsports/contents/gnsports_sh_0101/fclty/view.do"
    print(f"Crawling {url}...")
    result = crawler.crawl_pool_website(url, "강남구민체육센터")
    print(f"Result: {result}")

if __name__ == "__main__":
    test()
