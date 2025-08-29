import requests
import json
import re
import urllib.parse
from typing import List, Dict, Optional
import time
import random
import os
import tempfile
from PIL import Image
import cloudscraper
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import warnings
import logging
import sys
import platform

# Suppress warnings and logs
warnings.filterwarnings("ignore")
logging.getLogger('selenium').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
os.environ['WDM_LOG'] = '0'

def clear_screen():
    """Enhanced clear screen function that works across all platforms"""
    try:
        # Windows
        if platform.system() == "Windows":
            os.system("cls")
        # Mac and Linux
        else:
            os.system("clear")
    except:
        # Fallback method using print
        print("\n" * 100)

def move_cursor_up(lines=1):
    """Move cursor up n lines"""
    if platform.system() != "Windows":
        print(f"\033[{lines}A", end="")

def clear_line():
    """Clear current line"""
    print("\r" + " " * 100 + "\r", end="")

class OptimizedGifScraper:
    def __init__(self):
        self.session = cloudscraper.create_scraper()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        })
        self.successful_downloads = 0
        self.gif_sources = self._get_reliable_gif_sources()
        self.driver = None
        
    def _get_reliable_gif_sources(self) -> List[Dict]:
        """Define reliable GIF sources"""
        return [
            {
                'name': 'Tenor API',
                'type': 'api',
                'base_url': 'https://tenor.googleapis.com/v2/search',
                'api_key': 'AIzaSyAyimkuYQYF_FXVALexPuGQctUWRURdCYQ',
                'priority': 1,
                'reliable': True
            },
            {
                'name': 'Giphy',
                'type': 'scrape',
                'base_url': 'https://giphy.com/search/',
                'priority': 2,
                'reliable': True
            },
            {
                'name': 'Google Images',
                'type': 'scrape',
                'base_url': 'https://www.google.com/search',
                'search_param': 'q',
                'extra_params': '&tbm=isch&tbs=itp:animated',
                'priority': 3,
                'reliable': True
            }
        ]
    
    def _init_driver(self):
        if not self.driver:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Suppress Chrome logging and warnings
            options.add_argument("--log-level=3")
            options.add_argument("--silent")
            options.add_argument("--disable-logging")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-features=TranslateUI")
            options.add_argument("--disable-web-security")
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("detach", True)
            
            # Set preferences to suppress additional warnings
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_settings.popups": 0
            }
            options.add_experimental_option("prefs", prefs)
            
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Create service with log suppression
            service = Service(ChromeDriverManager().install())
            if platform.system() == "Windows":
                service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag for Windows
            
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self.driver
    
    def search_gifs_multi_source(self, topic: str, target_count: int = 100) -> List[Dict]:
        """Search for GIFs from reliable sources"""
        # Search for more GIFs than needed to account for download failures
        search_target = min(target_count * 3, 600)  # Cap at 600 to avoid excessive searching
        
        print(f"🔍 Searching for GIFs about '{topic}' from reliable sources...")
        print(f"📊 Target: {target_count} working downloads (searching for up to {search_target} candidates)...")
        
        all_gifs = []
        seen_urls = set()
        
        sources = sorted([s for s in self.gif_sources if s.get('reliable', False)], 
                        key=lambda x: x['priority'])
        
        for source in sources:
            if len(all_gifs) >= search_target:
                break
                
            needed = search_target - len(all_gifs)
            print(f"\n📡 Searching {source['name']} for up to {needed} more GIFs...")
            
            try:
                if source['type'] == 'api':
                    gifs = self._search_with_api(source, topic, needed)
                else:
                    gifs = self._search_with_scraping(source, topic, needed)
                
                new_gifs = []
                for gif in gifs:
                    if gif['url'] not in seen_urls:
                        seen_urls.add(gif['url'])
                        gif['source'] = source['name']
                        new_gifs.append(gif)
                        
                        if len(all_gifs) + len(new_gifs) >= search_target:
                            break
                
                all_gifs.extend(new_gifs)
                print(f"✅ Found {len(new_gifs)} GIFs from {source['name']}. Total: {len(all_gifs)}")
                
                time.sleep(random.uniform(1.5, 2.5))
                
            except Exception as e:
                print(f"❌ Error searching {source['name']}: {e}")
                continue
        
        print(f"\n🎯 Search completed! Found {len(all_gifs)} GIF candidates.")
        if len(all_gifs) < target_count:
            print(f"⚠️  Note: Found only {len(all_gifs)} GIFs, less than the {target_count} requested.")
        
        return all_gifs
    
    def _search_with_api(self, source: Dict, topic: str, count: int) -> List[Dict]:
        """Search using APIs with focus on Tenor"""
        gifs = []
        
        try:
            if source['name'] == 'Tenor API':
                gifs = self._search_tenor_api(topic, count)
                
        except Exception as e:
            print(f"API search error for {source['name']}: {e}")
        
        return gifs
    
    def _search_tenor_api(self, topic: str, count: int) -> List[Dict]:
        """Enhanced Tenor API search"""
        gifs = []
        
        try:
            # Try multiple endpoints for better results
            endpoints = [
                f'https://tenor.googleapis.com/v2/search?key=AIzaSyAyimkuYQYF_FXVALexPuGQctUWRURdCYQ&q={urllib.parse.quote_plus(topic)}&limit={min(count, 50)}&contentfilter=medium',
                f'https://g.tenor.com/v1/search?key=LIVDSRZULELA&q={urllib.parse.quote_plus(topic)}&limit={min(count, 50)}&contentfilter=medium'
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        results_key = 'results' if 'results' in data else 'gifs'
                        
                        for gif_data in data.get(results_key, []):
                            media_formats = gif_data.get('media_formats', gif_data.get('media', {}))
                            
                            # Try different formats
                            for format_type in ['gif', 'mediumgif', 'smallgif', 'tinygif']:
                                if format_type in media_formats:
                                    format_info = media_formats[format_type]
                                    url = format_info.get('url')
                                    
                                    if url and self._is_valid_gif_url(url):
                                        gifs.append({
                                            'url': url,
                                            'title': gif_data.get('content_description', gif_data.get('title', topic)),
                                            'topic': topic,
                                            'id': gif_data.get('id', ''),
                                            'source_url': gif_data.get('itemurl', gif_data.get('url', '')),
                                            'width': format_info.get('dims', [0, 0])[0] if isinstance(format_info.get('dims'), list) else 0,
                                            'height': format_info.get('dims', [0, 0])[1] if isinstance(format_info.get('dims'), list) else 0,
                                            'size': format_info.get('size', 0)
                                        })
                                        break
                        
                        if gifs:  # If we got results from this endpoint, use them
                            break
                            
                except Exception as e:
                    print(f"Tenor endpoint error: {e}")
                    continue
                        
        except Exception as e:
            print(f"Tenor API error: {e}")
        
        return gifs
    
    def _search_with_scraping(self, source: Dict, topic: str, count: int) -> List[Dict]:
        """Scrape GIFs using Selenium for Google Images and Giphy with updated methods"""
        gifs = []
        driver = self._init_driver()
        
        try:
            if source['name'] == 'Google Images':
                gifs = self._scrape_google_images_updated(driver, topic, count)
            elif source['name'] == 'Giphy':
                gifs = self._scrape_giphy(driver, topic, count)
        except Exception as e:
            print(f"Scraping error for {source['name']}: {e}")
        
        return gifs[:count]
    
    def _scrape_google_images_updated(self, driver, topic: str, count: int) -> List[Dict]:
        """Completely rewritten Google Images scraping method for 2025"""
        gifs = []
        
        try:
            # Build search URL - use simpler approach
            query = urllib.parse.quote_plus(f"{topic} animated gif")
            url = f"https://www.google.com/search?q={query}&tbm=isch&tbs=itp:animated"
            
            driver.get(url)
            time.sleep(3)
            
            # Handle consent dialog
            try:
                consent_selectors = [
                    "button:contains('Accept')", 
                    "button[id*='accept']",
                    ".QS5gu",
                    "button[data-ved]"
                ]
                for selector in consent_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector.replace(':contains(', '[').replace(')', ']'))
                        if elements:
                            elements[0].click()
                            time.sleep(2)
                            break
                    except:
                        continue
            except:
                pass
            
            seen_urls = set()
            scroll_count = 0
            max_scrolls = 10
            
            # Use a different strategy - extract URLs from page source directly
            while len(gifs) < count and scroll_count < max_scrolls:
                try:
                    # Method 1: Extract from page source using regex
                    page_source = driver.page_source
                    
                    # Find GIF URLs in the page source
                    gif_patterns = [
                        r'https://[^"]*\.gif[^"]*',
                        r'https://media\d*\.giphy\.com/[^"]*\.gif',
                        r'https://[^"]*tenor[^"]*\.gif',
                        r'https://[^"]*imgur[^"]*\.gif'
                    ]
                    
                    for pattern in gif_patterns:
                        urls = re.findall(pattern, page_source)
                        for url in urls:
                            if len(gifs) >= count:
                                break
                            # Clean URL (remove any trailing characters)
                            clean_url = url.split('"')[0].split("'")[0].split('\\')[0]
                            if self._is_valid_gif_url(clean_url) and clean_url not in seen_urls:
                                seen_urls.add(clean_url)
                                gifs.append({
                                    'url': clean_url,
                                    'title': topic,
                                    'topic': topic,
                                    'source_url': clean_url,
                                    'id': f"google_{len(gifs)}"
                                })
                    
                    # Method 2: Find image elements with stable approach
                    if len(gifs) < count:
                        try:
                            # Wait a moment for elements to be stable
                            time.sleep(1)
                            
                            # Find all img elements at once
                            all_images = driver.find_elements(By.TAG_NAME, "img")
                            
                            for img in all_images:
                                if len(gifs) >= count:
                                    break
                                
                                try:
                                    # Get src without clicking
                                    src = img.get_attribute("src")
                                    data_src = img.get_attribute("data-src") 
                                    
                                    # Try both attributes
                                    for url_candidate in [src, data_src]:
                                        if (url_candidate and 
                                            self._is_valid_gif_url(url_candidate) and 
                                            url_candidate not in seen_urls and 
                                            not url_candidate.startswith('data:')):
                                            
                                            seen_urls.add(url_candidate)
                                            gifs.append({
                                                'url': url_candidate,
                                                'title': topic,
                                                'topic': topic,
                                                'source_url': url_candidate,
                                                'id': f"google_{len(gifs)}"
                                            })
                                            break
                                            
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    
                    # Scroll to load more content
                    if len(gifs) < count:
                        # Smooth scroll down
                        driver.execute_script("window.scrollBy(0, 1000);")
                        time.sleep(2)
                        
                        # Try to click "Show more results" if available
                        try:
                            show_more = driver.find_elements(By.CSS_SELECTOR, "input[value*='more'], input[value*='More'], .mye4qd")
                            if show_more:
                                driver.execute_script("arguments[0].click();", show_more[0])
                                time.sleep(3)
                        except:
                            pass
                    
                    scroll_count += 1
                    # Silent scrolling - no output
                    
                except Exception:
                    scroll_count += 1
                    continue
                
        except Exception as e:
            print(f"❌ Google Images error: {e}")
        
        return gifs
    
    def _scrape_giphy(self, driver, topic: str, count: int) -> List[Dict]:
        """Scrape Giphy GIFs - keeping the working implementation"""
        gifs = []
        
        try:
            query = urllib.parse.quote_plus(topic)
            url = f"https://giphy.com/search/{query}"
            driver.get(url)
            time.sleep(3)
            
            # Scroll to load more GIFs
            seen_urls = set()
            last_height = driver.execute_script("return document.body.scrollHeight")
            while len(gifs) < count:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
                imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='giphy.com'][src$='.gif']")
                for img in imgs:
                    src = img.get_attribute("src")
                    if src and self._is_valid_gif_url(src) and src not in seen_urls:
                        seen_urls.add(src)
                        gifs.append({
                            'url': src,
                            'title': topic,
                            'topic': topic,
                            'source_url': src,
                        })
                        if len(gifs) >= count:
                            break
        except Exception as e:
            print(f"Giphy scraping error: {e}")
        
        return gifs[:count]
    
    def _is_valid_gif_url(self, url: str) -> bool:
        """Enhanced GIF URL validation"""
        if not url or not isinstance(url, str):
            return False
        
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Accept reliable GIF formats and hosts
        reliable_indicators = [
            '.gif', 'giphy.com', 'tenor.com', 'media.giphy.com',
            'c.tenor.com', 'media.tenor.com', 'gfycat.com', 'imgur.com'
        ]
        if not any(indicator in url.lower() for indicator in reliable_indicators):
            return False
        
        # Exclude problematic formats
        exclude_patterns = [
            'data:image', 'javascript:', '.svg', '.webp', '.png', 
            '.jpg', '.jpeg', '.mp4', '.webm', 'favicon', 'logo', 'sprite',
            'encrypted', 'base64'
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
        
        return len(url) <= 400
    
    def download_working_gifs(self, gifs: List[Dict], topic: str, target_count: int):
        """Download GIFs with clean progress display matching requested format"""
        try:
            base_folder = "GifScraped"
            topic_folder = os.path.join(base_folder, topic.replace(' ', '_').replace('/', '_'))
            os.makedirs(topic_folder, exist_ok=True)
            
            self.successful_downloads = 0
            downloaded_files = []
            
            # Determine actual target based on available GIFs
            actual_available = len(gifs)
            actual_target = min(target_count, actual_available)
            
            # Add 2 second delay before clearing screen
            time.sleep(7)
            clear_screen()
            
            if actual_available < target_count:
                print(f"📥 Starting Download - Found only {actual_available} GIFs (requested {target_count})")
                print(f"⚠️  Will attempt to download all {actual_available} available GIFs...")
            else:
                print(f"📥 Starting Download - Attempting to get {target_count} working GIFs...")
            
            gif_index = 0
            total_attempts = 0  # Track all attempts including failures
            
            while self.successful_downloads < actual_target and gif_index < actual_available:
                gif = gifs[gif_index]
                total_attempts += 1
                
                result = self._download_and_verify_gif(gif, topic_folder, self.successful_downloads + 1)
                
                if result:
                    downloaded_files.append(result)
                    # Clear the progress bar line first
                    clear_line()
                    # Print success message
                    print(f"✅ Success! Downloaded: {os.path.basename(result)}")
                
                # Calculate progress based on attempts (including failures)
                # Progress bar shows attempts out of actual available/target
                percentage = (gif_index + 1) / actual_target * 100
                filled = int(percentage // 5)  # Each block represents 5%
                bar = "█" * filled + "▒" * (20 - filled)
                
                # Show successful/attempted out of actual target
                progress_line = f"Downloading: [{bar}] {self.successful_downloads}/{actual_target}"
                
                # Print progress bar (will be overwritten on next iteration)
                print(progress_line, end='\r')
                
                gif_index += 1
                time.sleep(0.3)
            
            # Clear the final progress bar and print completion summary
            clear_line()
            print(f"\n🎉 Download completed!")
            
            if actual_available < target_count:
                print(f"Successfully downloaded {self.successful_downloads} working GIFs out of {actual_available} available (requested {target_count}).")
            else:
                print(f"Successfully downloaded {self.successful_downloads} working GIFs out of {actual_target} requested.")
            
            print(f"Total attempts: {total_attempts}")
            if total_attempts > 0:
                print(f"Success rate: {(self.successful_downloads/total_attempts*100):.1f}%")
            print(f"Files saved to: {topic_folder}")
            
            # Show source breakdown
            if downloaded_files:
                sources = {}
                for i, gif in enumerate(gifs[:len(downloaded_files)]):
                    if i < len(downloaded_files):
                        source = gif.get('source', 'Unknown')
                        sources[source] = sources.get(source, 0) + 1
                
                print("\n📊 Source breakdown:")
                for source, count in sources.items():
                    print(f"  {source}: {count} GIFs")
            
        except Exception as e:
            print(f"Error in download process: {e}")
    
    def _download_and_verify_gif(self, gif: Dict, topic_folder: str, gif_number: int) -> Optional[str]:
        """Download and verify a GIF"""
        try:
            url = gif['url']
            if url.endswith('.gifv'):
                url = url[:-1]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/gif,image/*,*/*',
                'Referer': 'https://www.google.com/'
            }
            
            response = self.session.get(url, timeout=30, stream=True, headers=headers)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'gif' not in content_type and 'image' not in content_type:
                return None
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as temp_file:
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        total_size += len(chunk)
                        
                        if total_size > 20 * 1024 * 1024:  # 20MB limit
                            raise Exception("File too large")
                
                temp_path = temp_file.name
            
            if not self._verify_gif_file(temp_path, total_size):
                os.unlink(temp_path)
                return None
            
            source_name = gif.get('source', 'unknown').lower().replace(' ', '').replace('api', '')
            filename = f"{gif_number:03d}_{source_name}_{gif.get('id', 'gif')[:8]}.gif"
            final_path = os.path.join(topic_folder, filename)
            
            counter = 1
            while os.path.exists(final_path):
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{counter}{ext}"
                final_path = os.path.join(topic_folder, filename)
                counter += 1
            
            os.rename(temp_path, final_path)
            self.successful_downloads += 1
            
            return final_path
            
        except Exception:
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass
            return None
    
    def _verify_gif_file(self, filepath: str, file_size: int) -> bool:
        """Verify GIF file"""
        try:
            if file_size < 2000:
                return False
            
            with open(filepath, 'rb') as f:
                header = f.read(6)
                if not (header.startswith(b'GIF87a') or header.startswith(b'GIF89a')):
                    return False
            
            try:
                with Image.open(filepath) as img:
                    if img.format != 'GIF':
                        return False
                    
                    width, height = img.size
                    if width < 100 or height < 100:
                        return False
                    
                    if width > 2000 or height > 2000:
                        return False
                    
                    return True
                        
            except Exception:
                return False
            
        except Exception:
            return False
    
    def _get_file_size_str(self, filepath: str) -> str:
        """Get readable file size"""
        try:
            size = os.path.getsize(filepath)
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size/(1024*1024):.1f} MB"
        except:
            return "Unknown"

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None


def show_tos_agreement():
    """TOS agreement"""
    print("")
    print("🎨 WEBGIF SCRAPER")
    print("=" * 60)
    print("\t⚠️  TERMS OF SERVICE & DISCLAIMER")
    print("=" * 60)
    print("📋 TERMS:")
    print("• This tool is for PERSONAL and RESEARCH use ONLY")
    print("• You must RESPECT Plaforms's Terms of Service")
    print("• Downloaded content must NOT be redistributed commercially")
    print("• You are responsible for respecting artists' rights")
    print("• Use downloaded content in accordance with copyright laws")
    print()
    print("🚫 DISCLAIMER:")
    print("• Developer is NOT responsible for misuse of this tool")
    print("• Users are solely responsible for their actions")
    print("• This tool is provided 'AS IS' without warranties")
    print("• By using this tool, you accept full responsibility")
    print("=" * 60)

    while True:
        agreement = input("Do you agree to these terms? (y/n): ").strip().lower()
        if agreement in ['y', 'yes']:
            print("✅ Terms accepted. Starting GIF scraper...\n")
            return True
        elif agreement in ['n', 'no']:
            print("❌ Terms declined. Exiting...")
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def main():
    """Main function"""
    if not show_tos_agreement():
        return
    
    scraper = OptimizedGifScraper()
    
    try:
        # Add 2 second delay before clearing screen after TOS agreement
        time.sleep(2)
        clear_screen()
        topic = input("Enter your search term: ").strip()
        if not topic:
            topic = "cats"
            print(f"Using default topic: {topic}")
        
        try:
            num_gifs = int(input("Enter number of GIFs to download (default 100): ").strip() or "100")
        except ValueError:
            num_gifs = 100
            print(f"Using default number: {num_gifs}")
        
        print(f"\n🎯 Target: {num_gifs} verified GIFs about '{topic}'")
        print("📡 Using Tenor API as primary source...")
        
        gifs = scraper.search_gifs_multi_source(topic, num_gifs)
        
        if gifs:
            print(f"\n✅ Found {len(gifs)} potential GIFs!")
            scraper.download_working_gifs(gifs, topic, num_gifs)
        else:
            print("❌ No GIFs found for this search term!")
            print("Try a different search term or check your internet connection.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        scraper.close_driver()


if __name__ == "__main__":
    main()