import asyncio
from curl_cffi.requests import AsyncSession
from selectolax.parser import HTMLParser
import random

class ProxyRotator:
    def __init__(self):
        self.proxies = []
        self.current_proxy = None

    async def initialize(self):
        self.proxies = await self.get_proxies()
        self.rotate_proxy()

    async def get_proxies(self) -> list[str]:
        """Get a list of proxies from the API."""
        async with AsyncSession() as session:
            response = await session.get("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text")
            return response.text.splitlines()

    def rotate_proxy(self) -> None:
        """Select a new proxy from the list."""
        if self.proxies:
            self.current_proxy = random.choice(self.proxies)

    async def request_content(self, session: AsyncSession, URL: str) -> str:
        """Request the content of a URL and return it as a string."""
        while True:
            if not self.current_proxy:
                assert False, "No more proxies available."
            try:
                response = await session.get(URL, impersonate="safari", proxy=self.current_proxy)
                if response.status_code == 200:
                    return response.text
                else:
                    print(f"Error: {response.status_code}, URL: {URL}")
                    self.proxies.remove(self.current_proxy)
                    self.rotate_proxy()
            except Exception as error:
                print(f"Error: {error}, URL: {URL}")
                self.proxies.remove(self.current_proxy)
                self.rotate_proxy()

async def scrape_amazon_product(session: AsyncSession, ASIN: str, proxy_rotator: ProxyRotator) -> None:
    """Scrape the price of an Amazon product given its ASIN."""
    URL = f"https://www.amazon.com/dp/{ASIN}"

    captcha_found = True
    while captcha_found:
        html = await proxy_rotator.request_content(session, URL)
        tree = HTMLParser(html)

        captcha_title = tree.css_first("h4")
        if captcha_title and "Enter the characters you see below" in captcha_title.text():
            print(f"Error: CAPTCHA, URL: {URL}")
            proxy_rotator.rotate_proxy()
        else:
            captcha_found = False

    title_element = tree.css_first("h1 span")
    price_symbol_element = tree.css_first("span.a-price-symbol")
    price_whole_element = tree.css_first("span.a-price-whole")
    price_fraction_element = tree.css_first("span.a-price-fraction")

    product_title = title_element.text().strip() if title_element else "Title not found"
    pryce_symbol = price_symbol_element.text() if price_symbol_element else "Symbol not found"
    pryce_whole = price_whole_element.text().replace(".", "") if price_whole_element else "Whole part not found"
    price_fraction = price_fraction_element.text() if price_fraction_element else "Fraction not found"

    print(f"Product Title: {product_title}")
    print(f"Price Symbol: {pryce_symbol}")
    print(f"Price Whole: {pryce_whole}")
    print(f"Price Fraction: {price_fraction}")

async def main():
    ASINs = ["B09LNW3CY2", "B009KYJAJY", "B0B2D77YB8", "B0D3KPGFHL"]
    proxy_rotator = ProxyRotator()
    await proxy_rotator.initialize()
    async with AsyncSession() as session:
        tasks = [scrape_amazon_product(session, ASIN, proxy_rotator) for ASIN in ASINs]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())