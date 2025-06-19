import requests
import os
import json
import re
from urllib.parse import urlparse, quote, unquote
from PIL import Image
import io
import time
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
import random
import hashlib
from pathlib import Path

class EnhancedGoogleImageScraper:
    def __init__(self):
        """Initialize the Enhanced Google Image Scraper"""
        self.downloaded_count = 0
        self.session = requests.Session()
        self.image_hashes = set()
        self.exclude_terms = []
        self.failed_urls = set()
        
        # Expanded user agents with more realistic ones
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 13; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0'
        ]
        
        # Different search engines as backup
        self.search_engines = [
            'google',
        ]
        
        self._setup_session()
    
    def _setup_session(self):
        """Setup session with more realistic headers"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
    
    def search_and_download_images(self, query: str, exclude_terms: List[str] = None, 
                                 num_images: int = 1000) -> int:
        """Enhanced search with multiple strategies and engines"""
        print(f"🎯 Target: {num_images} images")
        print(f"🔍 Searching: '{query}' (enhanced mode)")
        
        self.exclude_terms = [term.lower().strip() for term in (exclude_terms or [])]
        if self.exclude_terms:
            print(f"🚫 Excluding: {', '.join(self.exclude_terms)}")
        
        print("-" * 60)
        
        # Reset counters
        self.downloaded_count = 0
        self.image_hashes.clear()
        self.failed_urls.clear()
        
        # Create folder
        base_folder = "GoogleImages"
        search_folder = self._sanitize_filename(query)
        full_folder_path = os.path.join(base_folder, search_folder)
        os.makedirs(full_folder_path, exist_ok=True)
        print(f"📁 Saving to: {full_folder_path}")
        
        return self._enhanced_scraping_strategy(query, full_folder_path, num_images)
    
    def _enhanced_scraping_strategy(self, query: str, folder: str, target: int) -> int:
        """Multiple search engines + better anti-detection"""
        all_urls = set()
        
        # Strategy 1: Multiple Google approaches with better stealth
        print("🕵️ Phase 1: Stealthy Google scraping...")
        google_urls = self._scrape_google_enhanced(query)
        all_urls.update(google_urls)
        print(f"   Google: {len(google_urls)} URLs")
        
        # Strategy 2: Direct image hosting sites
        print("📸 Phase 2: Direct image sites...")
        direct_urls = self._scrape_direct_image_sites(query)
        all_urls.update(direct_urls)
        print(f"   Direct sites: {len(direct_urls)} URLs")
        
        total_urls = len(all_urls)
        print(f"\n✅ Total unique URLs collected: {total_urls}")
        
        if total_urls == 0:
            print("❌ No images found across all sources!")
            return 0
        
        # Phase 4: Smart downloading with better success rate
        print(f"\n📥 Phase 3: Smart downloading...")
        return self._smart_download(list(all_urls), folder, target)
    
    def _scrape_google_enhanced(self, query: str) -> set:
        """Enhanced Google scraping with better anti-detection"""
        urls = set()
        
        # More varied search parameters
        search_params = [
            # Basic searches with different time ranges
            {"q": query, "tbm": "isch", "safe": "off"},
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "qdr:w"},  # Past week
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "qdr:m"},  # Past month
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "qdr:y"},  # Past year
            
            # Size variations
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "isz:l"},   # Large
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "isz:m"},   # Medium
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "isz:lt,islt:2mp"},  # >2MP
            
            # Type variations
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "itp:photo"},
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "itp:clipart"},
            
            # Color variations
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "ic:color"},
            {"q": query, "tbm": "isch", "safe": "off", "tbs": "ic:gray"},
        ]
        
        for i, params in enumerate(search_params):
            print(f"      Google variant {i+1}/{len(search_params)}...", end=" ")
            
            # Human-like delay between different search types
            if i > 0:
                time.sleep(random.uniform(3, 8))
            
            variant_urls = self._scrape_google_variant(params)
            urls.update(variant_urls)
            print(f"{len(variant_urls)} URLs")
        
        return urls
    
    def _scrape_google_variant(self, params: dict) -> set:
        """Scrape a specific Google search variant"""
        urls = set()
        
        # Build URL
        param_str = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
        
        # Try multiple pages with longer delays
        for page in range(15):  # Fewer pages but better success rate
            try:
                start = page * 20
                url = f"https://www.google.com/search?{param_str}&start={start}"
                
                # Rotate user agent and session setup for each request
                self._setup_session()
                
                # Longer delay for later pages
                if page > 0:
                    delay = random.uniform(2, 6) if page < 5 else random.uniform(5, 10)
                    time.sleep(delay)
                
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 429:  # Rate limited
                    print("(rate limited, waiting...)", end="")
                    time.sleep(random.uniform(30, 60))
                    continue
                
                response.raise_for_status()
                page_urls = self._extract_image_urls_comprehensive(response.text)
                
                if len(page_urls) < 3 and page > 3:  # If very few results, probably end
                    break
                
                urls.update(page_urls)
                
            except Exception as e:
                if page < 3:  # Keep trying for first few pages
                    continue
                else:
                    break
        
        return urls
    
    def _scrape_direct_image_sites(self, query: str) -> set:
        """Scrape direct image hosting sites"""
        urls = set()
        
        # Sites that often host images and are searchable
        sites = [
            f"site:imgur.com {query}",
            f"site:flickr.com {query}",
            f"site:deviantart.com {query}",
            f"site:pinterest.com {query}",
            f"site:tumblr.com {query}",
        ]
        
        for site_query in sites:
            try:
                search_url = f"https://www.google.com/search?q={quote(site_query)}&tbm=isch&safe=off"
                
                time.sleep(random.uniform(3, 7))
                self._setup_session()
                
                response = self.session.get(search_url, timeout=12)
                response.raise_for_status()
                
                site_urls = self._extract_image_urls_comprehensive(response.text)
                urls.update(site_urls)
                
            except Exception:
                continue
        
        return urls
    
    def _extract_image_urls_comprehensive(self, content: str) -> set:
        """More comprehensive URL extraction"""
        urls = set()

        patterns = [
            # Standard image URLs
            r'"(https?://[^"]*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^"]*)?)"',
            r"'(https?://[^']*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^']*)?)'",
            
            # Data attributes and special cases
            r'data-[a-zA-Z]*=["\']([^"\']*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^"\']*)?)["\']',
            r'src=["\']([^"\']*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^"\']*)?)["\']',
            
            # JSON-like structures
            r'\["([^"]*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^"]*)?)"\]',
            r'"url":\s*"([^"]*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^"]*)?)"',
            
            # Google-specific
            r'imgurl=([^&]*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^&]*)?)',
            
            # Encoded patterns
            r'\\u003d([^\\]*\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|svg)(?:\?[^\\]*)?)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Clean up URL
                clean_url = match.replace('\\u003d', '=').replace('\\u0026', '&')
                clean_url = clean_url.replace('\\/', '/').replace('\\"', '"')
                clean_url = unquote(clean_url)
                
                if self._is_valid_image_url(clean_url):
                    urls.add(clean_url)
        
        return urls
    
    def _smart_download(self, urls: List[str], folder: str, target: int) -> int:
        """Smart downloading with better error handling and retry logic"""
        random.shuffle(urls)
        downloaded = 0
        failed = 0
        
        # Prioritize different types of URLs
        prioritized_urls = self._prioritize_urls(urls)
        
        for i, url in enumerate(prioritized_urls):
            if downloaded >= target:
                break
            
            print(f"[{i+1}/{len(prioritized_urls)}] ", end="")
            
            # Skip if should exclude
            if self._should_exclude_url(url):
                print("🚫 (excluded)")
                continue
            
            # Try download with retry
            success = self._download_with_retry(url, folder, downloaded + 1)
            
            if success:
                downloaded += 1
                print(f"✅ ({downloaded}/{target})")
            else:
                failed += 1
                print("❌")
            
            # Adaptive delay based on success rate
            success_rate = downloaded / (downloaded + failed) if (downloaded + failed) > 0 else 1
            if success_rate < 0.3:  # Low success rate, slow down
                delay = random.uniform(1, 3)
            else:
                delay = random.uniform(0.2, 1.0)
            
            time.sleep(delay)
        
        print(f"\n🎉 Final Results:")
        print(f"✅ Downloaded: {downloaded}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(downloaded/(downloaded+failed)*100):.1f}%")
        
        return downloaded
    
    def _prioritize_urls(self, urls: List[str]) -> List[str]:
        """Prioritize URLs by likely success rate"""
        high_priority = []
        medium_priority = []
        low_priority = []
        
        for url in urls:
            url_lower = url.lower()
            
            # High priority: Direct image URLs from reliable sources
            if any(domain in url_lower for domain in ['imgur.com', 'i.redd.it', 'wikimedia.org']):
                high_priority.append(url)
            # Medium priority: Has clear image extension
            elif any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                medium_priority.append(url)
            # Low priority: Might be dynamic or encoded
            else:
                low_priority.append(url)
        
        # Shuffle within each priority group
        random.shuffle(high_priority)
        random.shuffle(medium_priority)
        random.shuffle(low_priority)
        
        return high_priority + medium_priority + low_priority
    
    def _download_with_retry(self, url: str, folder: str, file_num: int, max_retries: int = 2) -> bool:
        """Download with retry logic"""
        for attempt in range(max_retries):
            try:
                return self._download_single_image(url, folder, file_num)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 3))
                    continue
                return False
        return False
    
    def _download_single_image(self, url: str, folder: str, file_num: int) -> bool:
        """Download a single image with better error handling"""
        # Skip if already failed
        if url in self.failed_urls:
            return False
        
        # Check for duplicates
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if url_hash in self.image_hashes:
            return False
        
        try:
            # Create new session for each download to avoid connection issues
            dl_session = requests.Session()
            dl_session.headers.update({
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://www.google.com/',
                'Accept': 'image/*,*/*;q=0.8',
                'Connection': 'close',  # Don't reuse connections
            })
            
            # Download
            response = dl_session.get(url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
                self.failed_urls.add(url)
                return False
            
            # Read image data
            img_data = b''
            for chunk in response.iter_content(chunk_size=8192):
                img_data += chunk
                if len(img_data) > 30 * 1024 * 1024:  # 30MB limit
                    self.failed_urls.add(url)
                    return False
            
            if len(img_data) < 1024:  # Too small
                self.failed_urls.add(url)
                return False
            
            # Process image
            img = Image.open(io.BytesIO(img_data))
            width, height = img.size
            
            # Size validation
            if width < 100 or height < 100:  # Minimum size
                self.failed_urls.add(url)
                return False
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if len(img.split()) > 3:
                    rgb_img.paste(img, mask=img.split()[-1])
                else:
                    rgb_img.paste(img)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save
            filename = f"{file_num:04d}.png"
            filepath = os.path.join(folder, filename)
            img.save(filepath, 'PNG', optimize=True, quality=95)
            
            self.image_hashes.add(url_hash)
            return True
            
        except Exception as e:
            self.failed_urls.add(url)
            return False
    
    def _should_exclude_url(self, url: str) -> bool:
        """Check if URL should be excluded"""
        if not self.exclude_terms:
            return False
        
        url_lower = url.lower()
        return any(term in url_lower for term in self.exclude_terms)
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Enhanced URL validation"""
        if not url or len(url) < 10:
            return False
        
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Skip obvious non-images
        skip_patterns = ['data:', 'javascript:', 'mailto:', 'tel:', 'blob:']
        url_lower = url.lower()
        
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
        
        # Skip known problematic domains
        bad_domains = ['google.com/search', 'googleapis.com', 'gstatic.com']
        if any(domain in url_lower for domain in bad_domains):
            return False
        
        return True
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.replace(' ', '_')
        return filename[:50]

def main():
    """Enhanced main function"""
    print("\nENHANCED GOOGLE IMAGE SCRAPER")
    print("By using this Enhanced Google Image Scraper, you agree to the following terms:")
    print("1.This tool is intended solely for educational,Fair Use and research purposes.")
    print("2.You must comply with Google's Terms of Service.")
    print("3.You are solely responsible for your use of this tool and any consequences thereof.")
    print("4.This tool is provided as-is with no warranties of any kind.")
    print("5.Use at your own risk. The developers are not liable for any damages.")
    print("6.Proceeding, you acknowledge that you have read, understood, and agree to be bound by these terms.")

    while True:
        accept = input("\nDo you accept these terms? (y/n): ").strip().lower()
        if accept in ['y', 'yes']:
            break
        elif accept in ['n', 'no']:
            print("Terms not accepted. Exiting.")
            return
        else:
            print("Please enter 'y' or 'n'")
    
    scraper = EnhancedGoogleImageScraper()
    
    try:
        while True:
            print("\n" + "=" * 55)
            
            query = input("Enter search term: ").strip()
            if not query:
                print("Please enter a search term!")
                continue
            
            exclude_input = input("Terms to exclude (comma-separated, or Enter to skip): ").strip()
            exclude_terms = []
            if exclude_input:
                exclude_terms = [term.strip() for term in exclude_input.split(',') if term.strip()]
            
            while True:
                num_input = input("Number of images (default 1000): ").strip()
                if not num_input:
                    num_images = 1000
                    break
                try:
                    num_images = int(num_input)
                    if num_images > 0:
                        break
                    print("Please enter a positive number!")
                except ValueError:
                    print("Please enter a valid number!")
            
            print(f"\n🚀 Starting ENHANCED image collection...")
            start_time = time.time()
            downloaded = scraper.search_and_download_images(query, exclude_terms, num_images)
            end_time = time.time()
            
            print(f"\n{'='*55}")
            print(f"🎉 ENHANCED RESULTS:")
            print(f"📊 Downloaded: {downloaded} images")
            print(f"⚡ Average speed: {downloaded/(end_time-start_time):.1f} images/second")
            print(f"⏱️  Total time: {end_time - start_time:.1f} seconds")
            print(f"📁 Location: GoogleImages/{scraper._sanitize_filename(query)}")
            
            cont = input("\nDownload more images? (y/n): ").strip().lower()
            if cont not in ['y', 'yes']:
                break
                
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopped by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()