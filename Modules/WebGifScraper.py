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
                'name': 'Giphy API',
                'type': 'api',
                'base_url': 'https://api.giphy.com/v1/gifs/search',
                'api_key': 'GlVGYHkr3WSBnllca54iNt0yFbjz7L65',
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
    
    def search_gifs_multi_source(self, topic: str, target_count: int = 100) -> List[Dict]:
        """Search for GIFs from reliable sources"""
        print(f"🔍 Searching for {target_count} working GIFs about '{topic}' from reliable sources...")
        
        all_gifs = []
        seen_urls = set()
        
        sources = sorted([s for s in self.gif_sources if s.get('reliable', False)], 
                        key=lambda x: x['priority'])
        
        for source in sources:
            if len(all_gifs) >= target_count:
                break
                
            needed = target_count - len(all_gifs)
            print(f"\n📡 Searching {source['name']} for {needed} more GIFs...")
            
            try:
                if source['type'] == 'api':
                    gifs = self._search_with_api(source, topic, needed * 2)
                else:
                    gifs = self._search_with_scraping(source, topic, needed * 2)
                
                new_gifs = []
                for gif in gifs:
                    if gif['url'] not in seen_urls:
                        seen_urls.add(gif['url'])
                        gif['source'] = source['name']
                        new_gifs.append(gif)
                        
                        if len(all_gifs) + len(new_gifs) >= target_count:
                            break
                
                all_gifs.extend(new_gifs)
                print(f"✅ Found {len(new_gifs)} GIFs from {source['name']}. Total: {len(all_gifs)}")
                
                time.sleep(random.uniform(1.5, 2.5))
                
            except Exception as e:
                print(f"❌ Error searching {source['name']}: {e}")
                continue
        
        print(f"\n🎯 Search completed! Found {len(all_gifs)} GIFs from reliable sources.")
        return all_gifs[:target_count]
    
    def _search_with_api(self, source: Dict, topic: str, count: int) -> List[Dict]:
        """Search using APIs with focus on Tenor"""
        gifs = []
        
        try:
            if source['name'] == 'Tenor API':
                gifs = self._search_tenor_api(topic, count)
            elif source['name'] == 'Giphy API':
                gifs = self._search_giphy_api(topic, count)
                
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
    

    def _search_giphy_api(self, topic: str, count: int) -> List[Dict]:
        """Search Giphy API"""
        gifs = []
        
        try:
            params = {
                'api_key': 'GlVGYHkr3WSBnllca54iNt0yFbjz7L65',
                'q': topic,
                'limit': min(count, 50),
                'rating': 'g',
                'lang': 'en'
            }
            
            response = self.session.get('https://api.giphy.com/v1/gifs/search', 
                                      params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                for gif_data in data.get('data', []):
                    images = gif_data.get('images', {})
                    
                    for quality in ['original', 'fixed_height', 'downsized_large']:
                        if quality in images and 'url' in images[quality]:
                            url = images[quality]['url']
                            if self._is_valid_gif_url(url):
                                gifs.append({
                                    'url': url,
                                    'title': gif_data.get('title', topic),
                                    'topic': topic,
                                    'id': gif_data.get('id', ''),
                                    'source_url': gif_data.get('url', ''),
                                    'width': images[quality].get('width', 0),
                                    'height': images[quality].get('height', 0),
                                    'size': images[quality].get('size', 0)
                                })
                                break
                        
        except Exception as e:
            print(f"Giphy API error: {e}")
        
        return gifs
    
    def _search_with_scraping(self, source: Dict, topic: str, count: int) -> List[Dict]:
        """Simple scraping for Google Images"""
        gifs = []
        
        try:
            search_param = source.get('search_param', 'q')
            extra_params = source.get('extra_params', '')
            query = urllib.parse.quote_plus(topic + ' gif')
            url = f"{source['base_url']}?{search_param}={query}{extra_params}"
            
            response = self.session.get(url, timeout=20)
            if response.status_code == 200:
                # Simple regex patterns for Google Images
                patterns = [
                    r'"ou":"([^"]*\.gif[^"]*)"',
                    r'(https?://[^\s<>"&]*\.gif[^\s<>"&]*)',
                ]
                
                all_matches = set()
                for pattern in patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    for match in matches:
                        url_candidate = urllib.parse.unquote(match)
                        if self._is_valid_gif_url(url_candidate):
                            all_matches.add(url_candidate)
                
                for url_candidate in list(all_matches)[:count]:
                    gifs.append({
                        'url': url_candidate,
                        'title': topic,
                        'topic': topic,
                    })
                
        except Exception as e:
            print(f"Scraping error: {e}")
        
        return gifs
    
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
            '.jpg', '.jpeg', '.mp4', '.webm', 'favicon', 'logo', 'sprite'
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
        
        return len(url) <= 400
    
    def download_working_gifs(self, gifs: List[Dict], topic: str, target_count: int):
        """Download GIFs with improved error handling"""
        try:
            base_folder = "GifScraped"
            topic_folder = os.path.join(base_folder, topic.replace(' ', '_').replace('/', '_'))
            os.makedirs(topic_folder, exist_ok=True)
            
            self.successful_downloads = 0
            downloaded_files = []
            
            print(f"\n📥 Starting download - attempting to get {target_count} working GIFs...")
            
            gif_index = 0
            attempts = 0
            max_attempts = min(len(gifs), target_count * 3)
            
            while self.successful_downloads < target_count and attempts < max_attempts and gif_index < len(gifs):
                gif = gifs[gif_index]
                attempts += 1
                
                print(f"Attempt {attempts}: Downloading from {gif.get('source', 'Unknown')}...")
                print(f"Progress: {self.successful_downloads}/{target_count}")
                
                result = self._download_and_verify_gif(gif, topic_folder, self.successful_downloads + 1)
                
                if result:
                    downloaded_files.append(result)
                    print(f"✅ Success! Downloaded: {os.path.basename(result)}")
                    print(f"   Size: {self._get_file_size_str(result)}")
                else:
                    print(f"❌ Download failed, trying next...")
                
                gif_index += 1
                time.sleep(0.8)
            
            print(f"\n🎉 Download completed!")
            print(f"Successfully downloaded {self.successful_downloads} working GIFs out of {target_count} requested.")
            print(f"Total attempts: {attempts}")
            print(f"Success rate: {(self.successful_downloads/attempts*100):.1f}%")
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


def show_tos_agreement():
    """TOS agreement"""
    print("""
WEB GIF SCRAPER
By using this tool, you agree to:
1. Use responsibly and respect Terms of Service
2. Educational/personal use only
3. Respect intellectual property laws
4. Tenor API prioritized for best results
5. You are solely responsible for usage
Required: pip install requests pillow cloudscraper
""")

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
        
        gifs = scraper.search_gifs_multi_source(topic, num_gifs * 3)
        
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


if __name__ == "__main__":
    main()