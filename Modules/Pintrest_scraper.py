import os
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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import logging
import traceback

def download_pinterest_images():
    # Set up Chrome driver options
    chrome_options = Options()
    
    # Ask user if they want to run in headless mode
    headless_choice = input("Run in headless mode (browser will run in background)? (y/n, default: y): ").lower()
    run_headless = headless_choice != 'n'
    
    if run_headless:
        chrome_options.add_argument("--headless=new")  # Modern headless mode
        print("Running in headless mode - browser will work in the background.")
    else:
        print("Running with visible browser window.")
        chrome_options.add_argument("--start-maximized")
    
    # Common options for both modes
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Headless mode needs window size defined
    if run_headless:
        chrome_options.add_argument("--window-size=1920,1080")
    
    # Create downloads directory if it doesn't exist
    download_dir = os.path.join(os.getcwd(), "Pinterest")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # Get search term from user
    base_search_term = input("Enter Pinterest search term: ")
    
    # Ask for the number of images to download
    try:
        target_input = input("How many images would you like to download? (Default: 1000): ")
        target_count = int(target_input) if target_input.strip() else 1000
    except ValueError:
        logging.warning("Invalid number entered, using default of 1000 images")
        target_count = 1000
    
    # List of modifiers to cycle through after base term is exhausted
    modifiers = ["HD", "FanArt", "Anime", "Ai", "Best", "4K", "Illustration", "PfP", "Character", 
                "pixiv", "ConceptArt", "Art Station", "DigitalArt", "Kawaii", "Anime Style", "Icon",
                "Ai Artworks", "Character Design", "Illustrative", "Original Art", "Ultra HD", "solo", 
                "High Quality Art", "Conceptual Art", "Digital illustration", "Anime Portrait","High Quality", 
                "Anime Screencap", "Cute", "Art", "Images", "photos", "Wallpaper", "DeviantArt", "Scene","Profile","Profile Pic"]
    
    # Inform about modifiers and Pinterest's anti-scraping
    print("\nINFORMATION: Pinterest has strict anti-scraping measures.")
    print(f"If your target of {target_count} images is large, you might need to use modifiers.")
    print("When the base search term is exhausted, modifiers will be added to find more images.")
    
    show_modifiers = input("\nWould you like to see and modify the current list of modifiers? (y/n): ").lower()
    if show_modifiers == 'y':
        print("\nCurrent modifiers:")
        for i, mod in enumerate(modifiers, 1):
            print(f"{i}. {mod}")
        
        print("\nThese modifiers will be added to your base search term when it no longer yields new images.")
        print("For example: '" + base_search_term + " HD', '" + base_search_term + " FanArt', etc.")
        
        add_more = input("\nWould you like to add more modifiers? (y/n): ").lower()
        if add_more == 'y':
            print("Enter additional modifiers (one per line, enter blank line when done):")
            while True:
                new_mod = input().strip()
                if not new_mod:
                    break
                modifiers.append(new_mod)
                print(f"Added '{new_mod}' to modifiers list")
    
    # Terms of Service agreement
    print("\n" + "="*80)
    print("IMPORTANT: RESPECT PINTEREST TERMS OF SERVICE AND CREATORS")
    print("="*80)
    print("By using this tool, you agree to:")
    print("1. Respect Pinterest's Terms of Service")
    print("2. Respect the rights of content creators")
    print("3. Use downloaded content responsibly and legally")
    
    agreement = input("\nDo you agree to these terms? (y/n): ").lower()
    if agreement != 'y':
        print("You must agree to the terms to continue. Exiting program.")
        return
    
    downloaded_count = 0
    unique_hashes = set()
    processed_pins = set()
    
    # Memory management - clear these variables periodically
    clear_memory_interval = 200  # Clear memory every 200 images
    
    driver = None
    try:
        # Use webdriver_manager to handle ChromeDriver installation
        logging.info("Setting up Chrome WebDriver...")
        print("\nSetting up Chrome WebDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set a page load timeout to prevent hanging
        driver.set_page_load_timeout(45)
        
        # Basic stealth setup to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Create a more forgiving wait
        wait = WebDriverWait(driver, 20)
        short_wait = WebDriverWait(driver, 5)
        
        # Directly go to Pinterest
        logging.info("Navigating to Pinterest main page...")
        print("Navigating to Pinterest...")
        driver.get("https://www.pinterest.com")
        
        # Wait for Pinterest to load
        time.sleep(5)
        
        # Handle login popup if it appears
        try:
            close_buttons = short_wait.until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@aria-label, 'close')]")))
            for button in close_buttons:
                if button.is_displayed():
                    button.click()
                    logging.info("Closed a popup dialog")
                    time.sleep(2)
                    break
        except:
            logging.info("No popup dialog to close")
        
        # PHASE 1: Exhaustively search with base term first
        # ------------------------------------------------
        logging.info(f"PHASE 1: Exhaustively searching base term: '{base_search_term}'")
        print(f"\nPHASE 1: Searching for images with base term: '{base_search_term}'")
        encoded_search = urllib.parse.quote(base_search_term)
        
        try:
            # Navigate to search results for base term
            driver.get(f"https://www.pinterest.com/search/pins/?q={encoded_search}")
            
            # Wait for the page to load and pins to appear
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test-id='pin']")))
                logging.info("Pinterest search page loaded successfully")
            except TimeoutException:
                logging.error("No pins found or page didn't load properly for base term.")
                print("No pins found initially. Refreshing page...")
                driver.refresh()
                time.sleep(5)
            
            # Initial random delay
            time.sleep(random.uniform(3.0, 5.0))
            
            # Initialize variables for base term search
            scroll_attempts = 0
            no_new_pins_count = 0
            failed_attempts = 0
            max_failed_attempts = 100  # Move to next phase after 100 failed attempts
            last_height = driver.execute_script("return document.body.scrollHeight")
            last_pin_count = 0
            last_download_count = 0
            no_downloads_counter = 0
            
            # Scroll and download loop for base search term until exhausted
            logging.info(f"Exhaustively collecting images for '{base_search_term}'...")
            print(f"Collecting images for '{base_search_term}'...")
            
            while failed_attempts < max_failed_attempts and downloaded_count < target_count:
                scroll_attempts += 1
                
                # Show progress info
                if scroll_attempts % 5 == 0 or downloaded_count % 10 == 0:  # Only show every 5 scrolls or 10 downloads to reduce console spam
                    print(f"Progress: Downloaded {downloaded_count}/{target_count} images - Scroll #{scroll_attempts}")
                
                logging.info(f"Base term: '{base_search_term}' - Scroll {scroll_attempts} - Failed attempts: {failed_attempts}/{max_failed_attempts} - Downloaded {downloaded_count}/{target_count}")
                
                # Memory management - periodically restart browser if needed
                if downloaded_count > 0 and downloaded_count % clear_memory_interval == 0:
                    logging.info("Performing memory cleanup...")
                    processed_pins.clear()  # Clear processed pins set to free memory
                    
                # Get all pins currently loaded
                try:
                    pins = driver.find_elements(By.CSS_SELECTOR, "div[data-test-id='pin']")
                    current_pin_count = len(pins)
                    logging.info(f"Found {current_pin_count} pins on page")
                    
                    if current_pin_count > last_pin_count:
                        failed_attempts = 0  # Reset failed attempts if we found new pins
                        logging.info(f"Found {current_pin_count - last_pin_count} new pins")
                        last_pin_count = current_pin_count
                    else:
                        no_new_pins_count += 1
                        if no_new_pins_count >= 3:  # Count as a failed attempt if no new pins for 3 consecutive scrolls
                            failed_attempts += 1
                            no_new_pins_count = 0
                            logging.info(f"Failed attempt: {failed_attempts}/{max_failed_attempts}")
                
                except WebDriverException as e:
                    logging.error(f"Error getting pins: {e}")
                    failed_attempts += 1
                    time.sleep(2)
                    continue
                
                # Process available pins - prioritize new pins
                try:
                    if len(pins) > 0:
                        # Get pins we haven't processed yet
                        new_pins = []
                        for pin in pins:
                            try:
                                pin_id = pin.get_attribute("data-test-pin-id") or str(hash(pin.text))
                                if pin_id not in processed_pins:
                                    new_pins.append(pin)
                                    processed_pins.add(pin_id)
                            except:
                                continue
                        
                        if new_pins:
                            logging.info(f"Found {len(new_pins)} unprocessed pins to examine")
                        else:
                            logging.info("No new pins to process")
                            failed_attempts += 1
                        
                        # Process the pins
                        for pin in new_pins:
                            try:
                                if downloaded_count >= target_count:
                                    break
                                
                                # Scroll to the pin with smooth behavior for more natural interaction
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", pin)
                                    time.sleep(random.uniform(0.3, 0.7))
                                except:
                                    continue
                                
                                # Extract image URL - try multiple ways
                                img_url = None
                                try:
                                    img_elements = pin.find_elements(By.TAG_NAME, "img")
                                    for img in img_elements:
                                        img_url = img.get_attribute("src")
                                        if not img_url:
                                            img_url = img.get_attribute("data-src")
                                        
                                        if img_url and len(img_url) > 10 and ("pinimg" in img_url):
                                            break
                                except:
                                    continue
                                
                                if not img_url:
                                    continue
                                
                                # Try to get higher resolution by manipulating URL
                                img_url = img_url.replace("/236x/", "/originals/")
                                img_url = img_url.replace("/474x/", "/originals/")
                                img_url = img_url.replace("/736x/", "/originals/")
                                img_url = img_url.split("?")[0]  # Remove URL parameters
                                
                                # Download the image
                                try:
                                    headers = {
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                        'Referer': 'https://www.pinterest.com/'
                                    }
                                    
                                    response = requests.get(img_url, headers=headers, timeout=10)
                                    
                                    if response.status_code == 200:
                                        # Check for duplicate images
                                        img_content = response.content
                                        img_hash = hashlib.md5(img_content).hexdigest()
                                        
                                        if img_hash not in unique_hashes:
                                            unique_hashes.add(img_hash)
                                            
                                            # Determine file extension
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
                                            
                                            # Create a more informative filename
                                            file_path = os.path.join(download_dir, f"{base_search_term}_{downloaded_count+1}.{file_extension}")
                                            
                                            with open(file_path, 'wb') as file:
                                                file.write(img_content)
                                            
                                            downloaded_count += 1
                                            if downloaded_count % 5 == 0:  # Only show every 5 images to reduce console spam
                                                print(f"Downloaded image {downloaded_count}/{target_count}")
                                            logging.info(f"Downloaded image {downloaded_count}/{target_count} - {os.path.basename(file_path)}")
                                        else:
                                            logging.info("Duplicate image found, skipping...")
                                except Exception as download_error:
                                    logging.error(f"Error downloading image: {download_error}")
                            
                            except StaleElementReferenceException:
                                continue
                            except Exception as pin_error:
                                logging.error(f"Error processing pin: {pin_error}")
                    
                    # Check if we downloaded anything new in this iteration
                    if downloaded_count == last_download_count:
                        no_downloads_counter += 1
                        if no_downloads_counter >= 5:  # If no new downloads for 5 iterations, count as failed attempt
                            failed_attempts += 1
                            no_downloads_counter = 0
                    else:
                        no_downloads_counter = 0
                        last_download_count = downloaded_count
                        
                except Exception as processing_error:
                    logging.error(f"Error processing pins: {processing_error}")
                    failed_attempts += 1
                
                # Scroll using one of several methods
                try:
                    scroll_method = random.randint(1, 5)
                    
                    if scroll_method == 1:
                        # Smooth scroll
                        driver.execute_script("window.scrollBy({top: 1000, left: 0, behavior: 'smooth'});")
                    elif scroll_method == 2:
                        # Page down key
                        html = driver.find_element(By.TAG_NAME, 'html')
                        html.send_keys(Keys.PAGE_DOWN)
                    elif scroll_method == 3:
                        # Direct scroll
                        driver.execute_script("window.scrollBy(0, 1200);")
                    elif scroll_method == 4:
                        # Scroll to random element
                        if pins and len(pins) > 3:
                            random_pin = random.choice(pins)
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_pin)
                    else:
                        # Multiple small scrolls
                        for _ in range(3):
                            driver.execute_script("window.scrollBy(0, 400);")
                            time.sleep(0.3)
                    
                    # Wait for new content to load - longer wait times
                    time.sleep(random.uniform(2.0, 4.0))
                    
                    # Check if scroll worked
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        failed_attempts += 1
                        logging.info(f"Scroll didn't produce new content. Failed attempt: {failed_attempts}/{max_failed_attempts}")
                    else:
                        last_height = new_height
                    
                    # Add a longer pause every few scrolls
                    if scroll_attempts % 10 == 0:
                        logging.info("Taking a short break...")
                        time.sleep(random.uniform(5.0, 8.0))
                    
                except Exception as scroll_error:
                    logging.error(f"Error during scrolling: {scroll_error}")
                    failed_attempts += 1
            
            logging.info(f"PHASE 1 COMPLETE: Downloaded {downloaded_count} images with base term '{base_search_term}'")
            
            # Check if we need to move to Phase 2 with modifiers
            if downloaded_count < target_count:
                logging.info(f"Moving to PHASE 2: Using modifiers after {failed_attempts} failed attempts")
                print(f"\nPHASE 1 COMPLETE: Downloaded {downloaded_count} images with base term '{base_search_term}'")
                print(f"Moving to PHASE 2: Using modifiers to find {target_count - downloaded_count} more images")
                
                # Take a longer break before moving to modifiers
                time.sleep(random.uniform(8.0, 12.0))
                
                # PHASE 2: Use modifiers after base term is exhausted
                # -------------------------------------------------
                logging.info("PHASE 2: Using modifiers to find more images")
                
                # Loop through modifiers
                for i, modifier in enumerate(modifiers):
                    if downloaded_count >= target_count:
                        break
                    
                    # Construct search term with modifier
                    search_term = f"{base_search_term} {modifier}"
                    logging.info(f"Searching for: '{search_term}' ({i+1}/{len(modifiers)})")
                    print(f"Searching for: '{search_term}' ({i+1}/{len(modifiers)})")
                    
                    # Navigate to search results
                    encoded_search = urllib.parse.quote(search_term)
                    driver.get(f"https://www.pinterest.com/search/pins/?q={encoded_search}")
                    
                    try:
                        # Wait for pins to appear
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test-id='pin']")))
                        logging.info("Search page loaded successfully")
                    except TimeoutException:
                        logging.error(f"No pins found for '{search_term}', trying next modifier")
                        print(f"No pins found for '{search_term}', trying next modifier")
                        continue
                    
                    # Wait for page to load completely
                    time.sleep(random.uniform(3.0, 5.0))
                    
                    # Initialize variables for this modifier
                    modifier_scroll_attempts = 0
                    max_modifier_scrolls = 50  # Limit scrolls per modifier
                    no_new_pins_streak = 0
                    max_no_new_streak = 60  # Move to next modifier after this many failed attempts
                    last_height = driver.execute_script("return document.body.scrollHeight")
                    last_download_for_modifier = downloaded_count
                    
                    # Scroll and download for this modifier
                    while (modifier_scroll_attempts < max_modifier_scrolls and 
                           no_new_pins_streak < max_no_new_streak and 
                           downloaded_count < target_count):
                        
                        modifier_scroll_attempts += 1
                        logging.info(f"'{search_term}' - Scroll {modifier_scroll_attempts}/{max_modifier_scrolls} - Downloaded {downloaded_count}/{target_count}")
                        
                        # Process pins similar to Phase 1
                        try:
                            pins = driver.find_elements(By.CSS_SELECTOR, "div[data-test-id='pin']")
                            
                            # Get pins we haven't processed yet
                            new_pins = []
                            for pin in pins:
                                try:
                                    pin_id = pin.get_attribute("data-test-pin-id") or str(hash(pin.text))
                                    if pin_id not in processed_pins:
                                        new_pins.append(pin)
                                        processed_pins.add(pin_id)
                                except:
                                    continue
                            
                            # Process new pins
                            for pin in new_pins:
                                try:
                                    if downloaded_count >= target_count:
                                        break
                                    
                                    # Scroll to pin
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", pin)
                                    time.sleep(random.uniform(0.3, 0.7))
                                    
                                    # Extract image URL
                                    img_url = None
                                    try:
                                        img_elements = pin.find_elements(By.TAG_NAME, "img")
                                        for img in img_elements:
                                            img_url = img.get_attribute("src")
                                            if not img_url:
                                                img_url = img.get_attribute("data-src")
                                            
                                            if img_url and len(img_url) > 10 and ("pinimg" in img_url):
                                                break
                                    except:
                                        continue
                                    
                                    if not img_url:
                                        continue
                                    
                                    # Try to get higher resolution
                                    img_url = img_url.replace("/236x/", "/originals/")
                                    img_url = img_url.replace("/474x/", "/originals/")
                                    img_url = img_url.replace("/736x/", "/originals/")
                                    img_url = img_url.split("?")[0]
                                    
                                    # Download image
                                    try:
                                        headers = {
                                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                            'Referer': 'https://www.pinterest.com/'
                                        }
                                        
                                        response = requests.get(img_url, headers=headers, timeout=10)
                                        
                                        if response.status_code == 200:
                                            img_content = response.content
                                            img_hash = hashlib.md5(img_content).hexdigest()
                                            
                                            if img_hash not in unique_hashes:
                                                unique_hashes.add(img_hash)
                                                
                                                # Determine file extension
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
                                                
                                                # Create filename including modifier
                                                file_path = os.path.join(download_dir, f"{base_search_term}_{modifier}_{downloaded_count+1}.{file_extension}")
                                                
                                                with open(file_path, 'wb') as file:
                                                    file.write(img_content)
                                                
                                                downloaded_count += 1
                                                if downloaded_count % 5 == 0:  # Only show every 5 images
                                                    print(f"Downloaded image {downloaded_count}/{target_count}")
                                                logging.info(f"Downloaded image {downloaded_count}/{target_count} - {os.path.basename(file_path)}")
                                            else:
                                                logging.info("Duplicate image found, skipping...")
                                    except Exception as download_error:
                                        logging.error(f"Error downloading image: {download_error}")
                                
                                except Exception as pin_error:
                                    continue
                            
                            # Check if we've downloaded anything new with this modifier
                            if downloaded_count == last_download_for_modifier:
                                no_new_pins_streak += 1
                                logging.info(f"No new images found: {no_new_pins_streak}/{max_no_new_streak}")
                            else:
                                no_new_pins_streak = 0
                                last_download_for_modifier = downloaded_count
                            
                        except Exception as processing_error:
                            logging.error(f"Error: {processing_error}")
                            no_new_pins_streak += 1
                        
                        # Scroll down to load more pins
                        try:
                            scroll_method = random.randint(1, 3)
                            
                            if scroll_method == 1:
                                driver.execute_script("window.scrollBy({top: 1000, left: 0, behavior: 'smooth'});")
                            elif scroll_method == 2:
                                html = driver.find_element(By.TAG_NAME, 'html')
                                html.send_keys(Keys.PAGE_DOWN)
                            else:
                                driver.execute_script("window.scrollBy(0, 1200);")
                            
                            time.sleep(random.uniform(2.0, 4.0))
                            
                            new_height = driver.execute_script("return document.body.scrollHeight")
                            if new_height == last_height:
                                no_new_pins_streak += 1
                            else:
                                last_height = new_height
                            
                            # Longer pause periodically
                            if modifier_scroll_attempts % 8 == 0:
                                time.sleep(random.uniform(4.0, 6.0))
                                
                        except Exception as scroll_error:
                            logging.error(f"Scroll error: {scroll_error}")
                            no_new_pins_streak += 1
                    
                    # Take a break between modifiers
                    logging.info(f"Completed search for '{search_term}'. Taking a break before next modifier...")
                    print(f"Completed search for '{search_term}'. Moving to next modifier...")
                    time.sleep(random.uniform(6.0, 10.0))
                    
                    # Clear some processed pins between modifiers to save memory
                    if len(processed_pins) > 5000:
                        logging.info("Clearing processed pins cache to free memory")
                        processed_pins.clear()
        
        except Exception as e:
            logging.error(f"Error during base term search: {e}")
            traceback.print_exc()
        
        if downloaded_count >= target_count:
            logging.info(f"Success! Downloaded {downloaded_count} images to {download_dir}")
            print(f"\nSuccess! Downloaded {downloaded_count} images to {download_dir}")
        else:
            logging.info(f"Completed with {downloaded_count} of {target_count} images.")
            print(f"\nCompleted with {downloaded_count} of {target_count} images.")
        
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
        logging.info("Browser closed. Script finished.")
        print("\nBrowser closed. Script finished.")

if __name__ == "__main__":
    print("Pinterest Image Scraper")
    print("=" * 60)
    print("Make sure you have installed required packages:")
    print("pip install selenium requests webdriver-manager")
    print("-" * 60)
    print("This script will first exhaust all images from your base search term.")
    print("After 100 failed attempts, it will move on to using modifiers (HD, FanArt, etc).")
    print("-" * 60)
    download_pinterest_images()