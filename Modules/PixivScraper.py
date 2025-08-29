import os
import json
import time
import hashlib
import sqlite3
from urllib.parse import urljoin, urlparse, quote
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import re
import sys
from PIL import Image
import io
from tqdm import tqdm

def clear_screen():
    # For Windows
    if os.name == "nt":
        os.system("cls")
    # For Linux / macOS
    else:
        os.system("clear")

def show_terms_and_disclaimer():
    """Show terms of service and disclaimer"""
    print("")
    print("🎨 PIXIV IMAGE DOWNLOADER")
    print("=" * 60)
    print("⚠️  TERMS OF SERVICE & DISCLAIMER")
    print("=" * 60)
    print("📋 TERMS:")
    print("• This tool is for PERSONAL and RESEARCH use ONLY")
    print("• You must RESPECT Pixiv's Terms of Service")
    print("• Downloaded content must NOT be redistributed commercially")
    print("• You are responsible for respecting artists rights")
    print("• Use downloaded content in accordance with copyright laws")
    print()
    print("🚫 DISCLAIMER:")
    print("• Developer is NOT responsible for misuse of this tool")
    print("• Users are solely responsible for their actions")
    print("• This tool is provided 'AS IS' without warranties")
    print("• By using this tool, you accept full responsibility")
    print("=" * 60)
    
    while True:
        consent = input("Do you agree to these terms? (yes/no): ").strip().lower()
        if consent in ['yes', 'y']:
            return True
        elif consent in ['no', 'n']:
            print("❌ You must agree to the terms to use this tool.")
            sys.exit(0)
        else:
            print("❌ Please enter 'yes' or 'no'")

def show_phpsessid_instructions():
    """Show instructions for getting PHPSESSID"""
    clear_screen()
    print("\n🔑 HOW TO GET YOUR PIXIV PHPSESSID:")
    print("=" * 60)
    print("🔍 METHOD 1 - Browser Cookie Editor (RECOMMENDED):")
    print("1. Install a browser cookie editor extension")
    print("2. Go to pixiv.net and login")
    print("3. Open the cookie editor extension")
    print("4. Find and copy the 'PHPSESSID' value")
    print()
    print("🔍 METHOD 2 - Developer Tools:")
    print("1. Open your browser and go to pixiv.net")
    print("2. Login to your account")
    print("3. Open Developer Tools (F12)")
    print("4. Go to Application/Storage tab > Cookies > pixiv.net")
    print("5. Find 'PHPSESSID' and copy its value")
    print("=" * 60)

class SimplifiedPixivDownloader:
    def __init__(self, phpsessid, download_dir="PixivImages", db_path="pixiv_downloads.db"):
        self.phpsessid = phpsessid
        self.download_dir = Path(download_dir)
        self.db_path = db_path
        self.download_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'total_found': 0,
            'converted': 0
        }
        
        # Image counter for numbering
        self.image_counter = 1
        
        # Progress bar (will be initialized when we know max_images)
        self.progress_bar = None
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.pixiv.net/',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Set cookies
        self.session.cookies.set('PHPSESSID', phpsessid, domain='.pixiv.net')
        
        # Initialize database
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for tracking downloads"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                artwork_id INTEGER PRIMARY KEY,
                title TEXT,
                artist_name TEXT,
                artist_id INTEGER,
                tags TEXT,
                file_path TEXT,
                file_hash TEXT,
                download_date TEXT,
                page_count INTEGER DEFAULT 1,
                bookmark_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                width INTEGER,
                height INTEGER,
                r18 BOOLEAN DEFAULT FALSE,
                ai_type INTEGER DEFAULT 0,
                source_tag TEXT,
                original_url TEXT,
                image_number INTEGER
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_artist ON downloads(artist_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_tags ON downloads(tags)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_date ON downloads(download_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_number ON downloads(image_number)')
        
        conn.commit()
        conn.close()
        
    def is_already_downloaded(self, artwork_id):
        """Check if artwork is already downloaded"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT file_path, file_hash FROM downloads WHERE artwork_id = ?', (artwork_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            file_path, file_hash = result
            # Check if file still exists
            if os.path.exists(file_path):
                return True, file_path
            else:
                # File was deleted, remove from database
                self.remove_from_database(artwork_id)
                return False, None
        return False, None
        
    def remove_from_database(self, artwork_id):
        """Remove entry from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM downloads WHERE artwork_id = ?', (artwork_id,))
        conn.commit()
        conn.close()
        
    def calculate_file_hash(self, file_path):
        """Calculate MD5 hash of file for duplicate detection"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            if self.progress_bar is not None:
                self.progress_bar.write(f"Error calculating hash for {file_path}: {e}")
            return None
            
    def search_artworks(self, tag, page=1):
        """Search for artworks by tag - ALWAYS get all content"""
        # URL encode the tag
        encoded_tag = quote(tag)
        url = f'https://www.pixiv.net/ajax/search/artworks/{encoded_tag}'
        
        params = {
            'word': tag,
            'order': 'date_d',  # newest first
            'mode': 'all',  # ALWAYS get all content
            'p': page,
            's_mode': 's_tag',  # tag search to get more results
            'type': 'illust_and_ugoira',  # illustrations and animations
            'lang': 'en',
            'version': '1e9c39b3d21e894af4a4bdb8d70aa7e6cc7adef5'
        }
        
        try:
            if self.progress_bar is not None:
                self.progress_bar.write(f"🔍 Searching page {page} for '{tag}'...")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('error'):
                if self.progress_bar is not None:
                    self.progress_bar.write(f"❌ API Error: {data.get('message', 'Unknown error')}")
                return None
                
            return data.get('body', {})
        except requests.exceptions.RequestException as e:
            if self.progress_bar is not None:
                self.progress_bar.write(f"❌ Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            if self.progress_bar is not None:
                self.progress_bar.write(f"❌ JSON decode error: {e}")
            return None
            
    def get_artwork_details(self, artwork_id):
        """Get detailed information about an artwork"""
        url = f'https://www.pixiv.net/ajax/illust/{artwork_id}'
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('error'):
                if self.progress_bar is not None:
                    self.progress_bar.write(f"❌ Error getting artwork {artwork_id}: {data.get('message', 'Unknown error')}")
                return None
                
            return data.get('body', {})
        except requests.exceptions.RequestException as e:
            if self.progress_bar is not None:
                self.progress_bar.write(f"❌ Failed to get artwork details for {artwork_id}: {e}")
            return None
            
    def get_artwork_pages(self, artwork_id):
        """Get all pages of an artwork (for manga/multiple images)"""
        url = f'https://www.pixiv.net/ajax/illust/{artwork_id}/pages'
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('error'):
                if self.progress_bar is not None:
                    self.progress_bar.write(f"❌ Error getting pages for {artwork_id}: {data.get('message', 'Unknown error')}")
                return None
                
            return data.get('body', [])
        except requests.exceptions.RequestException as e:
            if self.progress_bar is not None:
                self.progress_bar.write(f"❌ Failed to get artwork pages for {artwork_id}: {e}")
            return None
            
    def sanitize_filename(self, filename, max_length=100):
        """Sanitize filename for filesystem with proper Unicode handling"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        
        # Trim whitespace and dots
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename.encode('utf-8')) > max_length:
            # Truncate while preserving UTF-8 encoding
            filename_bytes = filename.encode('utf-8')[:max_length]
            try:
                filename = filename_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # If truncation breaks UTF-8, find safe cut point
                for i in range(max_length, max_length - 4, -1):
                    try:
                        filename = filename_bytes[:i].decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        continue
                        
        return filename or f"artwork_{int(time.time())}"
        
    def convert_to_png_fast(self, image_data, output_path):
        """Convert any image format to PNG with SPEED OPTIMIZATION"""
        try:
            # Open image from bytes
            img = Image.open(io.BytesIO(image_data))
            
            # SPEED OPTIMIZATION: Skip unnecessary conversions for already RGB/RGBA images
            if img.mode == 'RGB':
                # Already RGB, just save directly
                pass
            elif img.mode == 'RGBA':
                # Already RGBA, just save directly  
                pass
            elif img.mode == 'P':
                # Palette mode - convert to RGBA to preserve transparency
                img = img.convert('RGBA')
            elif img.mode == 'LA':
                # Grayscale with alpha - convert to RGBA
                img = img.convert('RGBA')
            else:
                # Other modes - convert to RGB (fastest)
                img = img.convert('RGB')
            
            # SPEED OPTIMIZATION: Use fast PNG save settings
            img.save(output_path, 'PNG', 
                    optimize=False,  # Disable optimization for speed
                    compress_level=1)  # Fastest compression (1-9, 1 is fastest)
            
            self.stats['converted'] += 1
            return True
        except Exception as e:
            if self.progress_bar is not None:
                self.progress_bar.write(f"❌ Failed to convert image to PNG: {e}")
            return False
            
    def download_and_convert_image(self, url, output_path, referer_id, artist_name):
        """Download image and convert to PNG with numbered filename - OPTIMIZED"""
        headers = {
            'Referer': f'https://www.pixiv.net/artworks/{referer_id}',
            'User-Agent': self.session.headers['User-Agent'],
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=headers, timeout=60, stream=True)
                response.raise_for_status()
                
                # SPEED OPTIMIZATION: Read image data more efficiently
                image_data = response.content  # Get all content at once instead of chunking
                
                # Create directory if it doesn't exist
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert to PNG and save with fast method
                if self.convert_to_png_fast(image_data, output_path):
                    if self.progress_bar is not None:
                        self.progress_bar.write(f"✅ Downloaded & converted: {output_path.name}")
                    return True
                else:
                    return False
                    
            except requests.exceptions.RequestException as e:
                if self.progress_bar is not None:
                    self.progress_bar.write(f"❌ Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return False
                    
        return False
        
    def save_to_database(self, artwork_data, file_path, file_hash, source_tag, image_number):
        """Save download information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO downloads 
            (artwork_id, title, artist_name, artist_id, tags, file_path, file_hash, 
             download_date, page_count, bookmark_count, like_count, view_count,
             width, height, r18, ai_type, source_tag, original_url, image_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            artwork_data['id'],
            artwork_data.get('title', 'Unknown'),
            artwork_data.get('userName', 'Unknown'),
            artwork_data.get('userId', 0),
            ','.join([str(tag) for tag in artwork_data.get('tags', [])]),
            str(file_path),
            file_hash,
            datetime.now().isoformat(),
            artwork_data.get('pageCount', 1),
            artwork_data.get('bookmarkCount', 0),
            artwork_data.get('likeCount', 0),
            artwork_data.get('viewCount', 0),
            artwork_data.get('width', 0),
            artwork_data.get('height', 0),
            artwork_data.get('xRestrict', 0) > 0,
            artwork_data.get('aiType', 0),
            source_tag,
            artwork_data.get('url', ''),
            image_number
        ))
        
        conn.commit()
        conn.close()
        
    def download_artwork(self, artwork_data, source_tag, max_images=None):
        """Download a single artwork with new numbering system"""
        artwork_id = artwork_data['id']
        
        # Check if already downloaded
        is_downloaded, existing_path = self.is_already_downloaded(artwork_id)
        if is_downloaded:
            self.stats['skipped'] += 1
            return True
            
        # Check if we've reached max images
        if max_images and self.stats['downloaded'] >= max_images:
            return False
            
        # Get detailed artwork information
        details = self.get_artwork_details(artwork_id)
        if not details:
            self.stats['failed'] += 1
            return False
            
        title = details.get('title', f'Artwork_{artwork_id}')
        artist_name = details.get('userName', 'Unknown_Artist')
        page_count = details.get('pageCount', 1)
        
        # Create safe artist name
        safe_artist = self.sanitize_filename(artist_name)
        
        # Create tag directory: PixivImages/TopicName/
        tag_dir = self.download_dir / self.sanitize_filename(source_tag)
        tag_dir.mkdir(parents=True, exist_ok=True)
        
        success = False
        
        if page_count == 1:
            # Single image
            try:
                image_url = details['urls']['original']
                filename = f"{self.image_counter}_{safe_artist}.png"
                file_path = tag_dir / filename
                
                if self.download_and_convert_image(image_url, file_path, artwork_id, safe_artist):
                    file_hash = self.calculate_file_hash(file_path)
                    self.save_to_database(details, file_path, file_hash, source_tag, self.image_counter)
                    self.stats['downloaded'] += 1
                    if self.progress_bar is not None:
                        self.progress_bar.update(1)
                    self.image_counter += 1
                    success = True
                else:
                    self.stats['failed'] += 1
                    
            except Exception as e:
                if self.progress_bar is not None:
                    self.progress_bar.write(f"❌ Error downloading single image {artwork_id}: {e}")
                self.stats['failed'] += 1
                
        else:
            # Multiple images (manga)
            pages = self.get_artwork_pages(artwork_id)
            if not pages:
                self.stats['failed'] += 1
                return False
                
            success_count = 0
            for i, page in enumerate(pages):
                # Check if we've reached max images
                if max_images and self.stats['downloaded'] >= max_images:
                    break
                    
                try:
                    image_url = page['urls']['original']
                    filename = f"{self.image_counter}_{safe_artist}.png"
                    file_path = tag_dir / filename
                    
                    if self.download_and_convert_image(image_url, file_path, artwork_id, safe_artist):
                        file_hash = self.calculate_file_hash(file_path)
                        self.save_to_database(details, file_path, file_hash, source_tag, self.image_counter)
                        success_count += 1
                        self.stats['downloaded'] += 1
                        if self.progress_bar is not None:
                            self.progress_bar.update(1)
                        self.image_counter += 1
                        
                    # Small delay between pages
                    time.sleep(0.3)  # Reduced delay for speed
                    
                except Exception as e:
                    if self.progress_bar is not None:
                        self.progress_bar.write(f"❌ Error downloading page {i+1}: {e}")
                    continue
                    
            if success_count > 0:
                success = True
            else:
                self.stats['failed'] += 1
                
        return success
        
    def bulk_download_by_tag(self, tag, max_images=None, delay=0.8):  # Reduced delay for speed
        """Download all artworks for a given tag - GETS ALL PAGES"""
        # Initialize progress bar ]
        if max_images is not None:
            self.progress_bar = tqdm(total=max_images, desc="Downloading images", unit="img")
        else:
            # For unlimited downloads, use a counter-style progress bar
            self.progress_bar = tqdm(desc="Downloading images", unit="img", total=None)
        
        page = 1
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while True:
            # Check if we've reached max images
            if max_images and self.stats['downloaded'] >= max_images:
                self.progress_bar.write(f"🎯 Reached target of {max_images} images!")
                break
                
            # Check for too many consecutive failures
            if consecutive_failures >= max_consecutive_failures:
                self.progress_bar.write(f"❌ Too many consecutive failures ({consecutive_failures}). Stopping.")
                break
                
            search_results = self.search_artworks(tag, page)
            if not search_results:
                consecutive_failures += 1
                self.progress_bar.write(f"❌ Failed to get search results for page {page}")
                if consecutive_failures < max_consecutive_failures:
                    self.progress_bar.write(f"🔄 Retrying in 5 seconds... (Attempt {consecutive_failures}/{max_consecutive_failures})")
                    time.sleep(5)
                continue
                
            # Reset consecutive failures on successful request
            consecutive_failures = 0
            
            # Get artworks from the results
            illust_manga = search_results.get('illustManga', {})
            artworks = illust_manga.get('data', [])
            total_on_page = len(artworks)
            
            # Check if we've reached the end
            if not artworks:
                self.progress_bar.write("✅ No more artworks found - reached end of results")
                break
                
            # Check if this is the last page according to API
            is_last_page = illust_manga.get('isLastPage', False)
            total_available = illust_manga.get('total', 0)
            
            self.stats['total_found'] += total_on_page
            self.progress_bar.write(f"📊 Page {page}: Found {total_on_page} artworks")
            
            page_success = 0
            for i, artwork in enumerate(artworks, 1):
                try:
                    if self.download_artwork(artwork, tag, max_images):
                        page_success += 1
                    else:
                        # If download_artwork returns False due to max_images, break
                        if max_images and self.stats['downloaded'] >= max_images:
                            break
                        
                    # Rate limiting - faster but still respectful
                    time.sleep(delay)
                    
                except KeyboardInterrupt:
                    self.progress_bar.write("\nℹ️  Download interrupted by user")
                    self.progress_bar.close()
                    return self.print_final_stats()
                except Exception as e:
                    self.progress_bar.write(f"❌ Error processing artwork {artwork.get('id', 'unknown')}: {e}")
                    self.stats['failed'] += 1
                    continue
            
            # Check if we've reached max images
            if max_images and self.stats['downloaded'] >= max_images:
                self.progress_bar.write(f"🎯 Reached target of {max_images} images!")
                break
                
            # Check if there are more pages
            if is_last_page:
                self.progress_bar.write("✅ Reached last page according to API")
                break
                
            # Continue to next page
            page += 1
            
            # Shorter delay between pages for speed
            time.sleep(1.5)
        
        self.progress_bar.close()
        return self.print_final_stats()
        
    def print_final_stats(self):
        """Print final download statistics"""
        print("\n" + "=" * 60)
        print("🎉 DOWNLOAD COMPLETED!")
        print("=" * 60)
        print(f"📊 Final Statistics:")
        print(f"   📥 Total Downloaded: {self.stats['downloaded']}")
        print(f"   ⚡ Total Converted to PNG: {self.stats['converted']}")
        print(f"   ⭐️  Total Skipped: {self.stats['skipped']}")
        print(f"   ❌ Total Failed: {self.stats['failed']}")
        print(f"   🔍 Total Found: {self.stats['total_found']}")
        print(f"   📁 Download Directory: {self.download_dir.absolute()}")
        print("=" * 60)
        
        success_rate = (self.stats['downloaded'] / max(self.stats['total_found'], 1)) * 100
        print(f"✨ Success Rate: {success_rate:.1f}%")
        
        return self.stats

def get_user_input():
    """Get user input for tag and image count"""
    clear_screen()
    print("\n🎨 Simplified Pixiv Downloader")
    print("🔞 Always downloads ALL content (NSFW content will appear if your Pixiv account settings have NSFW enabled.)")
    print("📁 Structure: PixivImages/TopicName/1_ArtistName.png, 2_ArtistName.png")
    print("⚡ Fast PNG conversion mode enabled")
    print("=" * 60)
    
    # Get tag name
    while True:
        tag = input("🏷️  Enter tag name: ").strip()
        if tag:
            break
        print("❌ Please enter a valid tag name")
    
    # Get number of images
    while True:
        count = input("📊 Number of images to download (press Enter for ALL): ").strip()
        if not count:
            max_images = None
            break
        elif count.isdigit() and int(count) > 0:
            max_images = int(count)
            break
        else:
            print("❌ Please enter a valid number or press Enter for all")
    
    return tag, max_images

def main():
    """Main function with TOS and interactive input"""
    # Show terms and get consent
    if not show_terms_and_disclaimer():
        return
    
    # Show PHPSESSID instructions
    show_phpsessid_instructions()
    
    # Check for PHPSESSID
    phpsessid = input("\n🔑 Enter your Pixiv PHPSESSID: ").strip()
    if not phpsessid:
        print("❌ PHPSESSID is required!")
        print("💡 Use a browser cookie editor extension for easier access!")
        sys.exit(1)
    
    # Get user preferences
    tag, max_images = get_user_input()
    clear_screen()
    print(f"\n🚀 Starting download with settings:")
    print(f"   🏷️  Tag: {tag}")
    print(f"   📊 Images: {max_images or 'ALL AVAILABLE'}")
    print(f"   🔞 Content: ALL (NSFW content will appear if your Pixiv account settings have NSFW enabled.)")
    print(f"   🎨 Format: All converted to PNG (FAST MODE)")
    print(f"   📂 Structure: PixivImages/{tag}/1_ArtistName.png, 2_ArtistName.png...")
    
    # Initialize downloader
    downloader = SimplifiedPixivDownloader(
        phpsessid=phpsessid,
        download_dir="PixivImages",
        db_path="pixiv_downloads.db"
    )
    
    # Start bulk download
    try:
        downloader.bulk_download_by_tag(
            tag=tag,
            max_images=max_images,
            delay=0.8  # Faster delay
        )
    except KeyboardInterrupt:
        print("\nℹ️  Download interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()