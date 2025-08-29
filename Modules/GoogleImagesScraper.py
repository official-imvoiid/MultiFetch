import requests
import json
import re
import urllib.parse
from typing import List, Dict, Optional, Tuple
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
import hashlib
import base64
from tqdm import tqdm
import io

# Suppress warnings and logs
warnings.filterwarnings("ignore")
logging.getLogger('selenium').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
os.environ['WDM_LOG'] = '0'

def clear_screen():
    """Enhanced clear screen function that works across all platforms"""
    try:
        if platform.system() == "Windows":
            os.system("cls")
        else:
            os.system("clear")
    except:
        print("\n" * 100)

def clear_line():
    """Clear current line"""
    print("\r" + " " * 100 + "\r", end="")

class GoogleImageScraper:
    def __init__(self, min_width=300, min_height=300, exclude_terms=None):
        self.session = cloudscraper.create_scraper()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        })
        self.successful_downloads = 0
        self.driver = None
        self.min_width = min_width
        self.min_height = min_height
        
        # Blacklist terms to skip (including user-provided)
        self.blacklist_terms = [
            'doll', 'figure', 'poster', 'toy', 'action figure', 
            'figurine', 'statue', 'collectible', 'merchandise',
            'plush', 'plushie', 'model', 'replica', 'thumbnail',
            'thumb', 'icon', 'avatar', 'profile'
        ]
        
        # Add user-provided exclusion terms
        if exclude_terms:
            self.blacklist_terms.extend([term.strip().lower() for term in exclude_terms])
        
        # Track skipped images for stats
        self.skipped_low_res = 0
        self.skipped_blacklist = 0
        self.failed_downloads = 0
        
    def _init_driver(self):
        """Initialize Selenium driver with optimized settings"""
        if not self.driver:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")
            options.add_argument("--silent")
            options.add_argument("--disable-logging")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-features=TranslateUI")
            options.add_argument("--disable-web-security")
            # MUTE AUDIO TO PREVENT SOUND/MUSIC
            options.add_argument("--mute-audio")
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("detach", True)
            
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.images": 1,
                "profile.default_content_settings.popups": 0,
                # DISABLE SOUND/MEDIA
                "profile.default_content_setting_values.media_stream": 2,
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
                "profile.default_content_setting_values.automatic_downloads": 2
            }
            options.add_experimental_option("prefs", prefs)
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            if platform.system() == "Windows":
                service.creation_flags = 0x08000000
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self.driver
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extract original filename from URL"""
        try:
            # Clean the URL first
            clean_url = url.split('?')[0]  # Remove query parameters
            clean_url = clean_url.split('#')[0]  # Remove fragments
            
            # Get the last part of the URL path
            filename = os.path.basename(urllib.parse.urlparse(clean_url).path)
            
            # If no filename or it's empty, check for common patterns
            if not filename or filename == '' or '.' not in filename:
                # Try to extract from the full URL path
                path_parts = urllib.parse.urlparse(clean_url).path.split('/')
                for part in reversed(path_parts):
                    if part and '.' in part:
                        filename = part
                        break
                
                # If still no filename, use "latest" or hash
                if not filename or filename == '':
                    # Check if URL contains common image names
                    if 'latest' in url.lower():
                        return 'latest'
                    elif 'default' in url.lower():
                        return 'default'
                    elif 'image' in url.lower():
                        return 'image'
                    else:
                        # Create a filename from URL hash
                        url_hash = hashlib.md5(url.encode()).hexdigest()
                        return url_hash
            
            # Remove extension as we'll add .png
            name_without_ext = os.path.splitext(filename)[0]
            
            # Clean the filename
            name_without_ext = re.sub(r'[<>:"/\\|?*]', '_', name_without_ext)[:100]
            
            return name_without_ext if name_without_ext else hashlib.md5(url.encode()).hexdigest()
            
        except:
            # Fallback to hash if extraction fails
            return hashlib.md5(url.encode()).hexdigest()
    
    def _check_image_resolution(self, image_path: str = None, image_data: bytes = None) -> Tuple[bool, int, int]:
        """Check if image meets minimum resolution requirements"""
        try:
            if image_path:
                with Image.open(image_path) as img:
                    width, height = img.size
            elif image_data:
                with Image.open(io.BytesIO(image_data)) as img:
                    width, height = img.size
            else:
                return False, 0, 0
            
            if width >= self.min_width and height >= self.min_height:
                return True, width, height
            else:
                self.skipped_low_res += 1
                return False, width, height
                
        except Exception:
            return False, 0, 0
    
    def _should_skip_image(self, url: str, title: str = "") -> bool:
        """Check if image should be skipped based on blacklist"""
        url_lower = url.lower()
        title_lower = title.lower() if title else ""
        
        # Check for thumbnail indicators in URL
        thumbnail_indicators = ['thumb', 'thumbnail', 't_', '_t.', 'small', 'icon', 'avatar']
        for indicator in thumbnail_indicators:
            if indicator in url_lower:
                self.skipped_blacklist += 1
                return True
        
        # Check blacklist terms
        for term in self.blacklist_terms:
            if term in url_lower or term in title_lower:
                self.skipped_blacklist += 1
                return True
        return False
    
    def search_and_download_images(self, topic: str, target_count: int = 1000, output_folder: str = "GoogleImages"):
        """Search and download images with resolution filtering"""
        print(f"📡 Loading Google Images...")
        print(f"⏳ Starting to download images one by one...")
        
        # Create folder structure
        clean_topic = re.sub(r'[<>:"/\\|?*]', '_', topic)[:50]
        topic_folder = os.path.join(output_folder, clean_topic)
        os.makedirs(topic_folder, exist_ok=True)
        print(f"📁 Created directory: {output_folder}\\{clean_topic}\n")
        
        driver = self._init_driver()
        self.successful_downloads = 0
        seen_urls = set()
        
        # Progress bar
        pbar = tqdm(total=target_count, desc="Downloading images", unit="img", position=0, leave=True)
        
        try:
            # Build search URL with safe search off and size filter
            query = urllib.parse.quote_plus(topic)
            # Add size filter to exclude icons/thumbnails
            url = f"https://www.google.com/search?q={query}&tbm=isch&safe=off&tbs=isz:m"
            
            driver.get(url)
            time.sleep(2)
            
            # Handle consent/cookie dialog
            try:
                accept_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'I agree') or contains(@aria-label, 'Accept')]")
                if accept_buttons:
                    accept_buttons[0].click()
                    time.sleep(1)
            except:
                pass
            
            scroll_count = 0
            max_scrolls = 100
            no_new_images_count = 0
            last_download_count = 0
            
            while self.successful_downloads < target_count and scroll_count < max_scrolls:
                try:
                    # Extract URLs from page source
                    page_source = driver.page_source
                    
                    patterns = [
                        r'"ou":"([^"]+)"',
                        r'"tu":"([^"]+)"',
                        r'"ru":"([^"]+)"',
                        r'\\x22ou\\x22:\\x22([^\\]+)',
                        r'"mediaUrl":"([^"]+)"',
                        r'data-src="([^"]+)"',
                        r'data-iurl="([^"]+)"',
                        r'(https?://[^\s"<>]+\.(?:jpg|jpeg|png|gif|webp|bmp)[^\s"<>]*)',
                    ]
                    
                    for pattern in patterns:
                        if self.successful_downloads >= target_count:
                            break
                            
                        matches = re.findall(pattern, page_source, re.IGNORECASE)
                        for match in matches:
                            if self.successful_downloads >= target_count:
                                break
                            
                            # Clean URL
                            clean_url = match.replace('\\u003d', '=').replace('\\u0026', '&').replace('\\/', '/')
                            clean_url = clean_url.replace('\\x3d', '=').replace('\\x26', '&')
                            
                            # Skip if already seen or blacklisted
                            if clean_url in seen_urls:
                                continue
                            if self._should_skip_image(clean_url):
                                continue
                            if not self._is_valid_image_url(clean_url):
                                continue
                            
                            seen_urls.add(clean_url)
                            
                            # Download and check resolution
                            result = self._download_single_image_with_resolution_check(
                                clean_url, topic_folder, self.successful_downloads + 1
                            )
                            
                            if result:
                                filename = os.path.basename(result)
                                # Print above the progress bar
                                tqdm.write(f"✅ Downloaded & Converted: {filename}")
                                pbar.update(1)
                                time.sleep(random.uniform(0.3, 0.8))
                    
                    # Click on thumbnails for full-size images
                    if self.successful_downloads < target_count:
                        try:
                            thumbnail_selectors = [
                                "img.Q4LuWd",
                                "img.YQ4gaf", 
                                "img[jsname='Q4LuWd']",
                                "img.rg_i",
                            ]
                            
                            thumbnails = []
                            for selector in thumbnail_selectors:
                                found = driver.find_elements(By.CSS_SELECTOR, selector)
                                thumbnails.extend(found)
                            
                            thumbnails = list(set(thumbnails))[:50]  # Limit to avoid too many clicks
                            
                            for thumb in thumbnails:
                                if self.successful_downloads >= target_count:
                                    break
                                
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thumb)
                                    time.sleep(0.2)
                                    driver.execute_script("arguments[0].click();", thumb)
                                    time.sleep(0.3)
                                    
                                    # Find full-size image
                                    full_image_selectors = [
                                        "img[jsname='HiaYvf']",
                                        "img.n3VNCb",
                                        "img.iPVvYb",
                                        "img.sFlh5c"
                                    ]
                                    
                                    for selector in full_image_selectors:
                                        full_images = driver.find_elements(By.CSS_SELECTOR, selector)
                                        for full_img in full_images:
                                            src = full_img.get_attribute("src")
                                            
                                            if not src or src in seen_urls:
                                                continue
                                            if self._should_skip_image(src):
                                                continue
                                            if not self._is_valid_image_url(src):
                                                continue
                                            
                                            seen_urls.add(src)
                                            
                                            result = self._download_single_image_with_resolution_check(
                                                src, topic_folder, self.successful_downloads + 1
                                            )
                                            
                                            if result:
                                                filename = os.path.basename(result)
                                                # Print above the progress bar
                                                tqdm.write(f"✅ Downloaded & Converted: {filename}")
                                                pbar.update(1)
                                                time.sleep(random.uniform(0.3, 0.8))
                                            
                                            break
                                    
                                except Exception:
                                    continue
                                    
                        except Exception:
                            pass
                    
                    # Check progress
                    if self.successful_downloads == last_download_count:
                        no_new_images_count += 1
                        if no_new_images_count >= 5:
                            break
                    else:
                        no_new_images_count = 0
                        last_download_count = self.successful_downloads
                    
                    # Scroll for more images
                    if self.successful_downloads < target_count:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        
                        # Try to click "Show more results"
                        try:
                            more_buttons = driver.find_elements(By.XPATH, "//input[contains(@value, 'more') or contains(@value, 'More')]")
                            for btn in more_buttons:
                                if btn.is_displayed():
                                    driver.execute_script("arguments[0].click();", btn)
                                    time.sleep(1)
                                    break
                        except:
                            pass
                    
                    scroll_count += 1
                    
                except Exception:
                    scroll_count += 1
                    continue
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            pbar.close()
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"🎉 Download completed!")
        print(f"✅ Successfully downloaded: {self.successful_downloads} images")
        print(f"⚠️ Skipped (low resolution): {self.skipped_low_res} images")
        print(f"🚫 Skipped (blacklisted): {self.skipped_blacklist} images")
        print(f"❌ Failed downloads: {self.failed_downloads}")
        print(f"📁 Files saved to: {topic_folder}")
        print(f"{'='*60}")
    
    def _download_single_image_with_resolution_check(self, url: str, topic_folder: str, image_number: int) -> Optional[str]:
        """Download image with resolution checking - ALL SAVED AS PNG"""
        try:
            # Extract original filename from URL
            original_name = self._extract_filename_from_url(url)
            
            # Handle base64 images
            if url.startswith('data:image'):
                header, data = url.split(',', 1)
                image_data = base64.b64decode(data)
                
                # Check resolution
                meets_res, width, height = self._check_image_resolution(image_data=image_data)
                if not meets_res:
                    return None
                
                # Always save as PNG with original name
                filename = f"{image_number}_{original_name}.png"
                final_path = os.path.join(topic_folder, filename)
                
                # Convert to PNG
                with Image.open(io.BytesIO(image_data)) as img:
                    # Convert to RGB if needed (for PNG compatibility)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img.save(final_path, 'PNG')
                    else:
                        # Convert to RGB first, then save as PNG
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img.save(final_path, 'PNG')
                
                self.successful_downloads += 1
                return final_path
            
            # Download regular URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://www.google.com/',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            response = self.session.get(url, timeout=10, stream=True, headers=headers)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type and 'octet-stream' not in content_type:
                self.failed_downloads += 1
                return None
            
            # Download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        total_size += len(chunk)
                        
                        if total_size > 50 * 1024 * 1024:  # 50MB limit
                            raise Exception("File too large")
                
                temp_path = temp_file.name
            
            # Check resolution
            meets_res, width, height = self._check_image_resolution(temp_path)
            if not meets_res:
                os.unlink(temp_path)
                return None
            
            # Open and ALWAYS save as PNG with original filename
            with Image.open(temp_path) as img:
                filename = f"{image_number}_{original_name}.png"
                final_path = os.path.join(topic_folder, filename)
                
                # Convert and save as PNG
                if img.mode in ('RGBA', 'LA', 'P'):
                    img.save(final_path, 'PNG')
                else:
                    # Convert to RGB first for non-alpha images
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(final_path, 'PNG')
            
            os.unlink(temp_path)
            self.successful_downloads += 1
            return final_path
            
        except Exception:
            self.failed_downloads += 1
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass
            return None
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Validate image URL"""
        if not url or not isinstance(url, str):
            return False
        
        # Allow data URLs
        if url.startswith('data:image'):
            return True
        
        # Must be http or https
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Exclude problematic patterns
        exclude_patterns = [
            'javascript:', '/gen_204', 'about:', 'chrome:', 'edge:',
            'blank.gif', '1x1', 'pixel', 'tracking', 'spacer'
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
        
        # Check for image-related patterns
        image_patterns = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg',
            'image', 'img', 'photo', 'picture', 'media', 'upload',
            'googleusercontent.com', 'gstatic.com'
        ]
        
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in image_patterns):
            return True
        
        # Accept reasonable length URLs
        if len(url) <= 1000:
            return True
        
        return False
    
    def _verify_and_get_extension(self, filepath: str, url: str) -> Optional[str]:
        """Verify image file and determine proper extension"""
        try:
            with Image.open(filepath) as img:
                format_lower = img.format.lower() if img.format else None
                
                format_map = {
                    'jpeg': '.jpg',
                    'jpg': '.jpg',
                    'png': '.png',
                    'gif': '.gif',
                    'webp': '.webp',
                    'bmp': '.bmp',
                    'ico': '.ico',
                    'tiff': '.tiff'
                }
                
                if format_lower in format_map:
                    return format_map[format_lower]
                
                url_lower = url.lower()
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                    if ext in url_lower:
                        return ext
                
                return '.jpg'
                
        except Exception:
            return None
    
    def close_driver(self):
        """Close the Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None


def show_tos_agreement():
    """Terms of Service agreement"""
    clear_screen()
    print("")
    print("🖼️ Google IMAGE DOWNLOADER")
    print("=" * 60)
    print("\t⚠️ TERMS OF SERVICE & DISCLAIMER")
    print("=" * 60)
    print("📋 TERMS:")
    print("• This tool is for PERSONAL and RESEARCH use ONLY")
    print("• You must RESPECT Google's Terms of Service")
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
        agreement = input("Do you accept these terms? (y/n): ").strip().lower()
        if agreement in ['y', 'yes']:
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
    
    scraper = None
    
    try:
        while True:
            time.sleep(2)
            clear_screen()
            print("""
==================================================================
		             📌 NOTE-READ IT
==================================================================
1. The scraper can retrieve 500–600 relevant images from Google.
   - Due to Google's 2025 update, results may stop or become
     irrelevant after this limit.
2. Recommended Usage:
   - Use the default 600 image setting.
   - Or allow full scraping, then manually review and delete
     irrelevant images.
3. 📏 Minimum Resolution: 300 × 300 pixels
   🔴 Safe Search: OFF
==================================================================
""")
            # Get search topic
            topic = input("Enter search term: ").strip()
            if not topic:
                print("Search term cannot be empty!")
                time.sleep(2)
                continue
            
            # Get exclusion terms
            exclude_input = input("Terms to exclude (comma-separated, or Enter to skip): ").strip()
            exclude_terms = []
            if exclude_input:
                exclude_terms = [term.strip() for term in exclude_input.split(',')]
                print(f"🔍 Excluding: {', '.join(exclude_terms)}")
            
            # Get number of images
            print("")
            num_input = input("Number of images (default 600): ").strip()
            if num_input:
                try:
                    num_images = int(num_input)
                    if num_images <= 0:
                        num_images = 600
                except ValueError:
                    num_images = 600
            else:
                num_images = 600
            
            # Get output folder
            output_input = input("Output folder (default GoogleImages): ").strip()
            output_folder = output_input if output_input else "GoogleImages"
            
            print(f"\n🎯 Target: {num_images} images about '{topic}'")
            print(f"📁 Output folder: {output_folder}")
            print(f"🔴 Safe search: DISABLED")
            print(f"📏 Min resolution: 300x300")
            if exclude_terms:
                print(f"🚫 Excluding: {', '.join(exclude_terms)}")
            
            # Initialize scraper
            scraper = GoogleImageScraper(
                min_width=300,
                min_height=300,
                exclude_terms=exclude_terms
            )
            
            # Clear screen before starting download
            time.sleep(5)
            clear_screen()
            
            # Search and download images
            scraper.search_and_download_images(topic, num_images, output_folder)
            
            # Ask if user wants to download more
            print("\n" + "═" * 60)
            again = input("Download more images? (y/n): ").strip().lower()
            
            if again not in ['y', 'yes']:
                break
            
            # Clean up for next search
            if scraper:
                scraper.close_driver()
                scraper = None
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        if scraper:
            scraper.close_driver()
        clear_screen()
        print("👋 Thank you for using Google Image Scraper!")


if __name__ == "__main__":
    main()