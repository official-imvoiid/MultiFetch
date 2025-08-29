import os
import sys
import time
import hashlib
import random
import requests
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')
os.environ['WDM_LOG_LEVEL'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'

# Suppress absl logging
try:
    import absl.logging
    absl.logging.set_verbosity(absl.logging.ERROR)
    absl.logging.set_stderrthreshold(absl.logging.ERROR)
except:
    pass

def clear_screen():
    # For Windows
    if os.name == "nt":
        os.system("cls")
    # For Linux / macOS
    else:
        os.system("clear")

def get_user_modifiers():
    """Get modifiers from user with interactive selection"""
    # Default modifiers list
    default_modifiers = [
        "HD", "FanArt", "Anime", "Ai", "Best", "4K", "Illustration", "PfP", "Character",
        "pixiv", "ConceptArt", "Art Station", "DigitalArt", "Kawaii", "Anime Style", 
        "Icon", "Ai Artworks", "Character Design", "Illustrative", "Original Art", 
        "Ultra HD", "solo", "High Quality Art", "Conceptual Art", "Digital illustration",
        "Anime Portrait", "High Quality", "Anime Screencap", "Cute", "Art", "Images",
        "photos", "Wallpaper", "DeviantArt", "Scene", "Profile", "Profile Pic"
    ]
    
    while True:
        # Ask if user wants to see and modify modifiers
        clear_screen()
        print("Modifiers are those which will be added to your base search term when it no longer yields new images.")
        show_modifiers = input("Would you like to see and modify the current list of modifiers? (y/n): ").lower().strip()
        
        if show_modifiers == 'y':
            print("\nCurrent modifiers:")
            for i, modifier in enumerate(default_modifiers, 1):
                print(f"{i}. {modifier}")
            
            print("\nThese modifiers will be added to your base search term when it no longer yields new images.")
            print("For example: 'Kurumi HD', 'Kurumi FanArt', etc.")
            
            # Ask if user wants to add more modifiers
            add_more = input("\nWould you like to add more modifiers? (y/n): ").lower().strip()
            
            if add_more == 'y':
                print("Enter additional modifiers (one per line, enter blank line when done):")
                while True:
                    new_modifier = input().strip()
                    if not new_modifier:  # Empty line breaks the loop
                        break
                    if new_modifier not in default_modifiers:
                        default_modifiers.append(new_modifier)
                        print(f"Added '{new_modifier}' to modifiers list")
                    else:
                        print(f"'{new_modifier}' already exists in the list")
            
            # Ask if user wants to remove any modifiers
            remove_modifiers = input("\nWould you like to remove any modifiers? (y/n): ").lower().strip()
            
            if remove_modifiers == 'y':
                print("Enter the numbers of modifiers to remove (comma-separated, e.g., 1,3,5):")
                try:
                    remove_indices = input().strip()
                    if remove_indices:
                        indices_to_remove = [int(x.strip()) - 1 for x in remove_indices.split(',')]
                        # Remove in reverse order to avoid index shifting
                        for index in sorted(indices_to_remove, reverse=True):
                            if 0 <= index < len(default_modifiers):
                                removed = default_modifiers.pop(index)
                                print(f"Removed '{removed}'")
                except ValueError:
                    print("Invalid input. Keeping all modifiers.")
            
            # Clear screen and ask if user wants to edit modifiers again
            clear_screen()
            print(f"\nFinal modifiers list ({len(default_modifiers)} items):")
            for i, modifier in enumerate(default_modifiers, 1):
                print(f"{i}. {modifier}")
            print("")
            edit_again = input("Do you want to edit modifiers again? (y/n): ").lower().strip()
            
            if edit_again != 'y':
                break
        else:
            break
    
    clear_screen()
    return default_modifiers

def get_download_directory():
    """Get download directory from user"""
    base_dir = input("Enter output directory (default 'Pinterest'): ").strip()
    if not base_dir:
        return "Pinterest"
    return base_dir

def download_pinterest_images():
    """Display the terms and conditions FIRST"""
    print("=" * 60)
    print("\t⚠️  TERMS OF SERVICE & DISCLAIMER")
    print("=" * 60)
    print("📋 TERMS:")
    print("• This tool is for PERSONAL and RESEARCH use ONLY")
    print("• You must RESPECT Pinterest's Terms of Service")
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
    print("\nAgreement: By continuing, you agree to respect Pinterest's Terms of Service.")
    agreement = input("Do you agree? (y/n): ").lower()
    if agreement != 'y':
        print("Exiting program.")
        return
    
    # Set up Chrome driver options
    chrome_options = Options()
    
    # Ask user if they want to run in headless mode
    clear_screen()
    headless_choice = input("\nRun in headless mode (browser will run in background)? (y/n, default: y): ").lower()
    run_headless = headless_choice != 'n'
    
    if run_headless:
        chrome_options.add_argument("--headless")
        print("Running in headless mode - browser will work in the background.")
    else:
        print("Running with visible browser window.")
        chrome_options.add_argument("--start-maximized")
    
    # Common options with additional suppressions for warnings
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-webgl")
    chrome_options.add_argument("--disable-3d-apis")
    chrome_options.add_argument("--silent")
    
    if run_headless:
        chrome_options.add_argument("--window-size=1920,1080")
    
    # Get search term from user
    base_search_term = input("Enter Pinterest search term: ")
    
    # Get download directory from user
    base_download_dir = get_download_directory()
    
    # Create folder structure
    topic_folder = base_search_term.replace(' ', '_').replace('/', '_').replace('\\', '_')
    download_dir = os.path.join(base_download_dir, topic_folder)
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    print(f"\nImages will be saved to: {download_dir}")
    
    # Ask for the number of images
    try:
        target_input = input("How many images would you like to download? (Default: 1000): ")
        target_count = int(target_input) if target_input.strip() else 1000
    except ValueError:
        target_count = 1000
    
    # Get modifiers from user (with interactive selection)
    modifiers = get_user_modifiers()
    
    downloaded_count = 0
    unique_hashes = set()
    processed_pins = set()
    progress_bar = None
    
    driver = None
    try:
        clear_screen()
        print("\nSetting up Chrome WebDriver...")
        print("\nWait For a Few Seconds...")
        
        # Suppress ChromeDriverManager output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        try:
            service = Service(ChromeDriverManager().install())
            service.log_path = os.devnull
        finally:
            sys.stdout.close()
            sys.stderr.close()
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(45)
        
        # Stealth setup
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        wait = WebDriverWait(driver, 20)
        short_wait = WebDriverWait(driver, 5)
        
        print("Navigating to Pinterest...")
        driver.get("https://www.pinterest.com")
        time.sleep(5)
        
        # Handle popup
        try:
            close_buttons = short_wait.until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@aria-label, 'close')]")))
            for button in close_buttons:
                if button.is_displayed():
                    button.click()
                    time.sleep(2)
                    break
        except:
            pass
        
        # PHASE 1: Base term search
        print(f"PHASE 1: Searching for images with base term: '{base_search_term}'")
        encoded_search = urllib.parse.quote(base_search_term)
        
        driver.get(f"https://www.pinterest.com/search/pins/?q={encoded_search}")
        
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test-id='pin']")))
        except TimeoutException:
            driver.refresh()
            time.sleep(5)
        
        time.sleep(random.uniform(3.0, 5.0))
        
        scroll_attempts = 0
        failed_attempts = 0
        max_failed_attempts = 100
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        print(f"Collecting images for '{base_search_term}'...")
        print("")  # Add blank line for progress bar
        
        # Initialize progress bar at the start - simplified description
        progress_bar = tqdm(total=target_count, desc="Downloading", unit="img", position=0, leave=True, ncols=100)
        
        while failed_attempts < max_failed_attempts and downloaded_count < target_count:
            scroll_attempts += 1
            
            try:
                pins = driver.find_elements(By.CSS_SELECTOR, "div[data-test-id='pin']")
                
                new_pins = []
                for pin in pins:
                    try:
                        pin_id = pin.get_attribute("data-test-pin-id") or str(hash(pin.text))
                        if pin_id not in processed_pins:
                            new_pins.append(pin)
                            processed_pins.add(pin_id)
                    except:
                        continue
                
                if not new_pins:
                    failed_attempts += 1
                else:
                    failed_attempts = 0
                
                for pin in new_pins:
                    try:
                        if downloaded_count >= target_count:
                            break
                        
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", pin)
                        time.sleep(random.uniform(0.3, 0.7))
                        
                        img_url = None
                        img_elements = pin.find_elements(By.TAG_NAME, "img")
                        for img in img_elements:
                            img_url = img.get_attribute("src")
                            if not img_url:
                                img_url = img.get_attribute("data-src")
                            if img_url and len(img_url) > 10 and ("pinimg" in img_url):
                                break
                        
                        if not img_url:
                            continue
                        
                        # Get higher resolution
                        img_url = img_url.replace("/236x/", "/originals/")
                        img_url = img_url.replace("/474x/", "/originals/")
                        img_url = img_url.replace("/736x/", "/originals/")
                        img_url = img_url.split("?")[0]
                        
                        try:
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                'Referer': 'https://www.pinterest.com/'
                            }
                            
                            response = requests.get(img_url, headers=headers, timeout=10)
                            
                            if response.status_code == 200:
                                img_content = response.content
                                img_hash = hashlib.md5(img_content).hexdigest()
                                
                                if img_hash not in unique_hashes:
                                    unique_hashes.add(img_hash)
                                    
                                    content_type = response.headers.get('Content-Type', '')
                                    if 'jpeg' in content_type or 'jpg' in content_type:
                                        file_extension = 'jpg'
                                    elif 'png' in content_type:
                                        file_extension = 'png'
                                    elif 'gif' in content_type:
                                        file_extension = 'gif'
                                    elif 'webp' in content_type:
                                        file_extension = 'webp'
                                    else:
                                        file_extension = 'jpg'
                                    
                                    # Extract filename from URL
                                    url_parts = img_url.split('/')
                                    original_name = url_parts[-1].split('.')[0] if url_parts else ""
                                    timestamp = str(int(time.time()))
                                    
                                    file_path = os.path.join(download_dir, 
                                        f"{downloaded_count+1}_{original_name}_{timestamp}.{file_extension}")
                                    
                                    with open(file_path, 'wb') as file:
                                        file.write(img_content)
                                    
                                    downloaded_count += 1
                                    
                                    # Update progress bar and print download info
                                    progress_bar.update(1)
                                    tqdm.write(f"✓ Downloaded: {os.path.basename(file_path)}")
                                    
                        except Exception:
                            pass
                    
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        pass
                
            except Exception:
                failed_attempts += 1
            
            # Scroll
            try:
                scroll_method = random.randint(1, 5)
                
                if scroll_method == 1:
                    driver.execute_script("window.scrollBy({top: 1000, left: 0, behavior: 'smooth'});")
                elif scroll_method == 2:
                    html = driver.find_element(By.TAG_NAME, 'html')
                    html.send_keys(Keys.PAGE_DOWN)
                elif scroll_method == 3:
                    driver.execute_script("window.scrollBy(0, 1200);")
                elif scroll_method == 4:
                    if pins and len(pins) > 3:
                        random_pin = random.choice(pins)
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_pin)
                else:
                    for _ in range(3):
                        driver.execute_script("window.scrollBy(0, 400);")
                        time.sleep(0.3)
                
                time.sleep(random.uniform(2.0, 4.0))
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    failed_attempts += 1
                else:
                    last_height = new_height
                
                if scroll_attempts % 10 == 0:
                    time.sleep(random.uniform(5.0, 8.0))
                    
            except Exception:
                failed_attempts += 1
        
        # PHASE 2: Use modifiers if needed
        if downloaded_count < target_count:
            tqdm.write(f"\nPHASE 2: Using modifiers to find more images...")
            
            for modifier in modifiers:
                if downloaded_count >= target_count:
                    break
                
                search_term = f"{base_search_term} {modifier}"
                tqdm.write(f"Searching for: '{search_term}'")
                
                encoded_search = urllib.parse.quote(search_term)
                driver.get(f"https://www.pinterest.com/search/pins/?q={encoded_search}")
                
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test-id='pin']")))
                except TimeoutException:
                    continue
                
                time.sleep(random.uniform(3.0, 5.0))
                
                modifier_scroll_attempts = 0
                max_modifier_scrolls = 50
                no_new_pins_streak = 0
                max_no_new_streak = 60
                last_height = driver.execute_script("return document.body.scrollHeight")
                
                while (modifier_scroll_attempts < max_modifier_scrolls and 
                       no_new_pins_streak < max_no_new_streak and 
                       downloaded_count < target_count):
                    
                    modifier_scroll_attempts += 1
                    
                    try:
                        pins = driver.find_elements(By.CSS_SELECTOR, "div[data-test-id='pin']")
                        
                        new_pins = []
                        for pin in pins:
                            try:
                                pin_id = pin.get_attribute("data-test-pin-id") or str(hash(pin.text))
                                if pin_id not in processed_pins:
                                    new_pins.append(pin)
                                    processed_pins.add(pin_id)
                            except:
                                continue
                        
                        for pin in new_pins:
                            try:
                                if downloaded_count >= target_count:
                                    break
                                
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", pin)
                                time.sleep(random.uniform(0.3, 0.7))
                                
                                img_url = None
                                img_elements = pin.find_elements(By.TAG_NAME, "img")
                                for img in img_elements:
                                    img_url = img.get_attribute("src")
                                    if not img_url:
                                        img_url = img.get_attribute("data-src")
                                    if img_url and len(img_url) > 10 and ("pinimg" in img_url):
                                        break
                                
                                if not img_url:
                                    continue
                                
                                img_url = img_url.replace("/236x/", "/originals/")
                                img_url = img_url.replace("/474x/", "/originals/")
                                img_url = img_url.replace("/736x/", "/originals/")
                                img_url = img_url.split("?")[0]
                                
                                try:
                                    headers = {
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                        'Referer': 'https://www.pinterest.com/'
                                    }
                                    
                                    response = requests.get(img_url, headers=headers, timeout=10)
                                    
                                    if response.status_code == 200:
                                        img_content = response.content
                                        img_hash = hashlib.md5(img_content).hexdigest()
                                        
                                        if img_hash not in unique_hashes:
                                            unique_hashes.add(img_hash)
                                            
                                            content_type = response.headers.get('Content-Type', '')
                                            if 'jpeg' in content_type or 'jpg' in content_type:
                                                file_extension = 'jpg'
                                            elif 'png' in content_type:
                                                file_extension = 'png'
                                            elif 'gif' in content_type:
                                                file_extension = 'gif'
                                            elif 'webp' in content_type:
                                                file_extension = 'webp'
                                            else:
                                                file_extension = 'jpg'
                                            
                                            url_parts = img_url.split('/')
                                            original_name = url_parts[-1].split('.')[0] if url_parts else ""
                                            timestamp = str(int(time.time()))
                                            
                                            file_path = os.path.join(download_dir, 
                                                f"{downloaded_count+1}_{modifier}_{original_name}_{timestamp}.{file_extension}")
                                            
                                            with open(file_path, 'wb') as file:
                                                file.write(img_content)
                                            
                                            downloaded_count += 1
                                            
                                            # Update progress bar and print download info
                                            progress_bar.update(1)
                                            tqdm.write(f"✓ Downloaded: {os.path.basename(file_path)}")
                                            no_new_pins_streak = 0
                                        
                                except Exception:
                                    pass
                            
                            except Exception:
                                continue
                        
                        if no_new_pins_streak > 0:
                            no_new_pins_streak += 1
                        
                        driver.execute_script("window.scrollBy(0, 1200);")
                        time.sleep(random.uniform(2.0, 4.0))
                        
                        new_height = driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            no_new_pins_streak += 1
                        else:
                            last_height = new_height
                            
                    except Exception:
                        no_new_pins_streak += 1
                
                time.sleep(random.uniform(6.0, 10.0))
        
        progress_bar.close()
        
        print(f"\n✓ Successfully downloaded {downloaded_count} images to {download_dir}")
        
    except Exception as e:
        if progress_bar:
            progress_bar.close()
        print(f"\n✗ An error occurred: {str(e)}")
    
    finally:
        if driver:
            driver.quit()
        print("Browser closed. Script finished.")

if __name__ == "__main__":
    print("")
    print("🎨 Pinterest IMAGE DOWNLOADER")
    download_pinterest_images()