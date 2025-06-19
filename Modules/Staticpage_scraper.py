from PIL import Image
import io
import os
import requests
import urllib.parse
from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import traceback
import json
import sys
import cloudscraper

class CloudflareWebScraper:
    def __init__(self):
        """
        Initialize the Cloudflare-aware WebScraper
        """
        self.base_download_dir = os.path.join(os.getcwd(), "WebScrap")
        os.makedirs(self.base_download_dir, exist_ok=True)

        self.scraper = None
        self.driver = None

    def setup_cloudflare_scraper(self):
        """
        Setup Cloudflare-bypassing scraper
        """
        try:
            self.scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                },
                delay=10,
            )
            return self.scraper
        except Exception as e:
            print(f"Cloudflare scraper setup failed: {e}")
            return None

    def setup_selenium_webdriver(self):
        """
        Advanced WebDriver setup with Cloudflare considerations
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            service = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=service, options=chrome_options)

            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            return driver
        except Exception as e:
            print(f"WebDriver setup failed: {e}")
            print(f"Please ensure you have a compatible version of Chrome and ChromeDriver installed.")
            print(f"Also, check for potential antivirus interference.")
            return None

    def cloudflare_selenium_bypass(self, url):
        """
        Advanced Selenium-based Cloudflare bypass

        :param url: Target URL
        :return: Page source or None
        """
        self.driver = self.setup_selenium_webdriver()

        if not self.driver:
            return None

        try:
            self.driver.get(url)

            time.sleep(10)

            cloudflare_elements = [
                "#challenge-form",
                ".ray-id",
                "#cf-hcaptcha-container"
            ]

            for selector in cloudflare_elements:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    time.sleep(5)
                except:
                    pass

            time.sleep(5)

            return self.driver.page_source

        except Exception as e:
            print(f"Selenium Cloudflare bypass failed: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None


    def extract_content(self, page_source, url):
        """
        Content extraction with Cloudflare handling

        :param page_source: HTML source of the page
        :param url: Original URL
        :return: Extracted content dictionary
        """
        try:
            soup = BeautifulSoup(page_source, 'html.parser')

            cloudflare_indicators = [
                soup.find(string=re.compile(r'Cloudflare|Security Check|Checking your browser')),
                soup.find('div', {'id': 'cf-wrapper'}),
                soup.find('span', {'class': 'ray-id'})
            ]

            if any(indicator is not None for indicator in cloudflare_indicators):
                print("Cloudflare challenge detected. Bypassing failed.")
                return {
                    'error': 'Cloudflare protection active',
                    'details': 'Unable to bypass Cloudflare security'
                }

            text_elements = soup.find_all(['p', 'div', 'span', 'article', 'section'],
                           string=lambda text: text and len(text.strip()) > 10)
            text_content = ' '.join([elem.get_text(strip=True) for elem in text_elements])

            def is_valid_link(href):
                return href and (href.startswith('http') or href.startswith('/')) \
                       and not any(x in href.lower() for x in ['javascript:', '#', 'mailto:', 'tel:'])

            links = [urllib.parse.urljoin(url, a.get('href'))
                     for a in soup.find_all('a', href=True)
                     if is_valid_link(a.get('href'))]

            images = []
            image_tags = soup.find_all('img', src=True)
            for img in image_tags:
                img_src = img.get('src')
                if img_src:
                    full_img_url = urllib.parse.urljoin(url, img_src)
                    if not any(x in full_img_url.lower() for x in ['pixel', 'placeholder', 'transparent']):
                        images.append(full_img_url)

            domain = urllib.parse.urlparse(url).netloc

            image_count = self.download_images(images, domain)

            return {
                'text_content': text_content,
                'links': list(set(links)),
                'images': list(set(images)),
                'images_downloaded': image_count
            }

        except Exception as e:
            print(f"Content extraction failed: {e}")
            return None

    def download_images(self, images, domain):
        """
        Image download with Cloudflare considerations, dimension check, and PNG conversion.
        """
        domain_dir = os.path.join(self.base_download_dir, domain)
        os.makedirs(domain_dir, exist_ok=True)

        if not self.scraper:
            self.setup_cloudflare_scraper()

        downloaded_count = 0
        downloaded_hashes = set()

        for idx, img_url in enumerate(list(set(images)), 1):
            try:
                if self.scraper:
                    response = self.scraper.get(img_url, timeout=10)

                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if not content_type.startswith('image/'):
                            print(f"Skipping non-image content from {img_url}")
                            continue

                        try:
                            img_data = response.content
                            img = Image.open(io.BytesIO(img_data))

                            if img.width < 215 or img.height < 215:
                                print(f"Skipping image {img_url} due to small dimensions ({img.width}x{img.height})")
                                continue

                            img_hash = hash(img_data)
                            if img_hash in downloaded_hashes:
                                print(f"Skipping duplicate image: {img_url}")
                                continue
                            downloaded_hashes.add(img_hash)

                            filename = re.sub(r'[^\w\-_\. ]', '_',
                                              os.path.basename(urllib.parse.urlparse(img_url).path))
                            if not filename.lower().endswith('.png'):
                                filename = f"{os.path.splitext(filename)[0]}.png"

                            filepath = os.path.join(domain_dir, f"{idx}_{filename}")

                            img.save(filepath, format='PNG')

                            downloaded_count += 1
                            print(f"Downloaded and converted image: {filename}")

                        except IOError:
                            print(f"Could not open or process image from {img_url}. It might be corrupt or not a valid image.")
                        except Exception as e:
                             print(f"Error processing image {img_url}: {e}")

                else:
                    print("Cloudflare scraper not initialized, skipping image download.")

            except Exception as e:
                print(f"Image download failed for {img_url}: {e}")

        return downloaded_count

    def display_static_site_warning(self):
        """
        Displays a warning about scraping static websites
        """
        print("\n" + "="*80)
        print(" STATIC WEBSITE SCRAPER - IMPORTANT NOTICE ".center(80, "="))
        print("="*80)
        print("""
This tool is designed for scraping STATIC websites like blogs, news sites, and 
informational pages. Please note:

1. LEGAL CONSIDERATIONS: Always check the website's Terms of Service and robots.txt
   before scraping. Many sites prohibit automated scraping.

2. RATE LIMITING: Use delays between requests to avoid overwhelming servers.

3. DYNAMIC CONTENT: This scraper may not capture JavaScript-loaded content on some 
   modern websites that rely heavily on client-side rendering.

4. STRUCTURED DATA: For sites with specific data patterns (e.g., product listings),
   you may need to modify the extraction logic.

5. ETHICAL USE: Only use scraped content in accordance with copyright laws and 
   fair use principles.

Best suited for: News sites, blogs, documentation sites, and simple content websites.
        """)
        print("="*80 + "\n")

    def main(self):
        """
        Main scraping workflow with Cloudflare handling
        """
        print("Cloudflare-Aware Web Scraper")
        
        # Display the static website warning
        self.display_static_site_warning()

        while True:
            url = input("\nEnter the website URL to scrape: ").strip()
            if url.startswith(('http://', 'https://')):
                break
            print("Invalid URL. Please include http:// or https://")

        try:
            page_source = None

            self.setup_cloudflare_scraper()
            if self.scraper:
                try:
                    response = self.scraper.get(url)
                    if response.status_code == 200:
                        page_source = response.text
                        print("CloudScraper successful.")
                    else:
                         print(f"CloudScraper failed with status code: {response.status_code}")

                except Exception as e:
                    print(f"CloudScraper request failed: {e}")
                    page_source = None


            if not page_source:
                 print("Falling back to Selenium bypass.")
                 page_source = self.cloudflare_selenium_bypass(url)


            if not page_source:
                print("\nFailed to bypass Cloudflare protection using both methods.")
                print("Possible solutions:")
                print("1. Check website accessibility and if your IP is blocked.")
                print("2. Consider using a VPN or proxy.")
                print("3. Ensure your Chrome browser and ChromeDriver versions are compatible.")
                print("4. Check for antivirus interference blocking ChromeDriver.")
                return

            result = self.extract_content(page_source, url)

            if result:
                if 'error' in result:
                    print(f"\nCloudflare Protection: {result['error']}")
                    print(result['details'])
                else:
                    print("\n--- Scraping Results ---")
                    print(f"Unique Links Found: {len(result.get('links', []))}")
                    print(f"Images Downloaded: {result.get('images_downloaded', 0)}")

            else:
                print("\nContent extraction failed. Website might have strong anti-scraping measures or a different structure.")

        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            traceback.print_exc()
        finally:
             if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    scraper = CloudflareWebScraper()
    scraper.main()