import requests
from bs4 import BeautifulSoup
import os
import time
import re
import random
from urllib.parse import quote_plus, urlparse
import threading
from tqdm import tqdm
import urllib.request
import mimetypes
from PIL import Image
import io

def clear_screen():
    # For Windows
    if os.name == "nt":
        os.system("cls")
    # For Linux / macOS
    else:
        os.system("clear")

def display_header():
    """Display the professional header with terms and conditions"""
    print("")
    print("🎨 DEVIANTART IMAGE DOWNLOADER")
    print("=" * 60)
    print("\t⚠️  TERMS OF SERVICE & DISCLAIMER")
    print("=" * 60)
    print("📋 TERMS:")
    print("• This tool is for PERSONAL and RESEARCH use ONLY")
    print("• You must RESPECT DeviantArt's Terms of Service")
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

class DeviantArtScraper:
    def __init__(self, topic, max_images=1000, output_dir="DeviantArt"):
        self.topic = topic
        self.max_images = max_images
        # Create folder structure: DeviantArt/topic_name/
        self.output_dir = os.path.join(output_dir, topic)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        self.downloaded_count = 0
        self.processed_urls = set()
        self.progress_bar = None  # Initialize as None, create when first download succeeds

        clear_screen()
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"📁 Created directory: {self.output_dir}")
    
    def download_image(self, img_url, base_url):
        """Downloads the image from the URL and ensures it's in JPG format"""
        try:
            # Get the file extension from the URL or content-type
            parsed_url = urlparse(img_url)
            file_name = os.path.basename(parsed_url.path)
            
            # Skip icons and small images based on URL patterns
            if any(pattern in img_url.lower() for pattern in ['/avatars/', '/icons/', '/emoticons/', '/thumbs/', 'thumbnail', 'icon', 'avatar']):
                return False
            
            # If it's just the artwork page URL rather than direct image
            if 'deviantart.com' in img_url and '/art/' in img_url:
                # try to extract the actual image from the page
                image_urls = self.extract_image_urls(img_url)
                if image_urls and image_urls[0] != img_url:  # If we found an actual image
                    return self.download_image(image_urls[0], base_url)
                else:
                    return False
            
            # Download the image content
            response = requests.get(img_url, headers=self.headers, stream=True)
            if response.status_code != 200:
                return False
            
            # Get content type from response headers
            content_type = response.headers.get('Content-Type', '')
            
            # Skip if not an image content type
            if 'image' not in content_type:
                return False
                
            # Check image size before downloading completely
            try:
                img = Image.open(io.BytesIO(response.content))
                width, height = img.size
                
                # Skip small images that are likely icons (under 500px width or height)
                if width < 500 or height < 500:
                    return False
                
                # Generate a base filename without extension (will add .jpg later)
                if not file_name or file_name == '':
                    timestamp = int(time.time())
                    file_name = f"deviantart_{timestamp}"
                else:
                    # Remove any existing extension
                    file_name = os.path.splitext(file_name)[0]
                
                # Add timestamp to prevent overwriting
                timestamp = int(time.time())
                file_name = f"{self.downloaded_count + 1}_{file_name}_{timestamp}.jpg"  # Force JPG extension with counter
                
                # Full path to save the image
                file_path = os.path.join(self.output_dir, file_name)
                
                # If image has transparency (like PNG with alpha channel), convert to RGB
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    img = background
                
                # Save as JPG
                img.convert('RGB').save(file_path, 'JPEG', quality=95)
                
                # Create progress bar on first successful download
                if self.progress_bar is None:
                    self.progress_bar = tqdm(total=self.max_images, desc="Downloading images", unit="img")
                
                self.progress_bar.write(f"✅ Downloaded & converted: {file_name}")
                return True
                
            except Exception as e:
                return False
                
        except Exception as e:
            return False
    
    def extract_image_urls(self, page_url):
        # Skip if we've already processed this URL
        if page_url in self.processed_urls:
            return []
        
        # Add URL to processed set
        base_url = page_url.split('#')[0]  # Remove any fragment part
        self.processed_urls.add(base_url)
        
        image_urls = []
        try:
            response = requests.get(base_url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Method 1: Try to find the download button href - best quality option
                download_buttons = soup.select('a[data-hook="download_button"]')
                if download_buttons:
                    for button in download_buttons:
                        href = button.get('href')
                        if href:
                            image_urls.append(href)
                            return image_urls  # This is likely the best quality image
                
                # Method 2: Find main full-resolution image
                main_img = soup.select_one('img[data-hook="deviation_std_img"]')
                if main_img and main_img.get('src'):
                    img_url = main_img.get('src')
                    # Try to get full-resolution version
                    img_url = re.sub(r'/v\d+/.*?/', '/f/', img_url)
                    img_url = img_url.replace('/200H/', '/').replace('/250/', '/')
                    img_url = img_url.replace('/400T/', '/').replace('/300W/', '/')
                    image_urls.append(img_url)
                    return image_urls
                
                # Method 3: Look for other image elements that might be full-sized artwork
                image_elements = []
                image_elements.extend(soup.select('img.dev-content-full'))
                image_elements.extend(soup.select('img.dev-content-normal'))
                image_elements.extend(soup.select('img.fullview'))
                
                # If still not found, look for any reasonable sized images
                if not image_elements:
                    for img in soup.find_all('img'):
                        src = img.get('src', '')
                        # Only consider DeviantArt or wixmp (their CDN) images
                        if (('deviantart' in src or 'wixmp.com' in src) and 
                            not any(pattern in src.lower() for pattern in ['/avatars/', '/icons/', '/emoticons/', '/thumbs/', 'thumbnail', 'icon', 'avatar'])):
                            
                            # Check if it has width attribute and it's big enough
                            width = img.get('width')
                            if width and int(width) >= 500:
                                image_elements.append(img)
                            # Or add it if it seems like a content image
                            elif re.search(r'/f/|/intermediary/|/pre\d+/', src):
                                image_elements.append(img)
                
                for img in image_elements:
                    img_url = img.get('src') or img.get('data-src')
                    if img_url:
                        # Try to get full-resolution version
                        img_url = img_url.replace('/200H/', '/').replace('/250/', '/')
                        img_url = img_url.replace('/400T/', '/').replace('/300W/', '/')
                        image_urls.append(img_url)
                
                if not image_urls:
                    # If no images found, we'll still return the artwork page itself
                    # The download method will handle it properly
                    image_urls.append(base_url)
        except Exception as e:
            pass
        
        return image_urls
    
    def search_and_download(self):
        page = 1
        consecutive_empty_pages = 0
        max_empty_pages = 3  # Stop after 3 consecutive empty pages
        
        while self.downloaded_count < self.max_images and consecutive_empty_pages < max_empty_pages:
            # DeviantArt search URL
            search_term = quote_plus(self.topic)
            search_url = f"https://www.deviantart.com/search?q={search_term}&page={page}"
            
            # Use print instead of progress_bar.write since progress_bar might not exist yet
            print(f"🔍 Searching page {page} for '{self.topic}'...")
            try:
                response = requests.get(search_url, headers=self.headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find artwork links
                    artwork_links = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        # DeviantArt artwork URLs usually follow this pattern
                        if re.search(r'deviantart\.com/[^/]+/art/', href):
                            # Remove any fragments and duplicates
                            base_href = href.split('#')[0]
                            if base_href not in artwork_links:
                                artwork_links.append(base_href)
                    
                    if not artwork_links:
                        consecutive_empty_pages += 1
                        print(f"❌ No artwork links found on page {page}. Empty pages: {consecutive_empty_pages}/{max_empty_pages}")
                        page += 1
                        time.sleep(random.uniform(1.5, 3.0))  # Reduced delay
                        continue
                    else:
                        consecutive_empty_pages = 0  # Reset counter when we find links
                    
                    print(f"📊 Page {page}: Found {len(artwork_links)} artworks")
                    
                    # Process each artwork page
                    for link in artwork_links:
                        if self.downloaded_count >= self.max_images:
                            break
                        
                        image_urls = self.extract_image_urls(link)
                        
                        for img_url in image_urls:
                            if self.downloaded_count >= self.max_images:
                                break
                                
                            # Download the image
                            if self.download_image(img_url, link):
                                self.downloaded_count += 1
                                if self.progress_bar:  # Only update if progress bar exists
                                    self.progress_bar.update(1)
                                
                                # Brief delay between downloads (reduced)
                                time.sleep(random.uniform(0.3, 1.0))
                    
                    # If we still need more images, move to the next page
                    if self.downloaded_count < self.max_images:
                        page += 1
                        # Random delay between page requests (reduced)
                        time.sleep(random.uniform(1.5, 3.0))
                    else:
                        break
                else:
                    print(f"❌ Failed to access search page. Status code: {response.status_code}")
                    break
            except Exception as e:
                print(f"❌ Error during search: {e}")
                break
        
        if self.progress_bar:
            self.progress_bar.close()
        print(f"\n🎉 Downloaded {self.downloaded_count} images related to '{self.topic}' to '{self.output_dir}'")

def main():
    # Display professional header and terms
    display_header()
    
    # Get user agreement to terms
    while True:
        agreement = input("Do you agree to these terms? (yes/no): ").lower().strip()
        if agreement in ['yes', 'y']:
            break
        elif agreement in ['no', 'n']:
            print("❌ Terms not accepted. Exiting...")
            return
        else:
            print("⚠️  Please enter 'yes' or 'no'")
    
    # Get user inputs
    clear_screen()
    topic = input("Enter your search topic: ")
    try:
        max_images = int(input("Enter maximum number of images to download (default 1000): ") or 1000)
    except ValueError:
        max_images = 1000
        print("⚠️  Invalid input. Using default value of 1000 images.")
    
    output_dir = input(f"Enter output directory (default 'DeviantArt'): ") or "DeviantArt"
    
    print(f"Will download up to {max_images} images to folder: '{output_dir}/{topic}'")
    print(f"🚀 Start DeviantArt image downloader for topic: '{topic}'?")
    
    proceed = input("Do you want to proceed? (y/n): ")
    if proceed.lower() != 'y':
        print("❌ Operation cancelled.")
        return
    
    scraper = DeviantArtScraper(topic, max_images, output_dir)
    scraper.search_and_download()

if __name__ == "__main__":
    main()