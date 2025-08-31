# Add these functions to your browser.py file

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import random
import time

# Global variables
driver = None
wait = None

def create_driver():
    """Create a fresh browser driver instance"""
    global driver, wait
    
    # Close existing driver if it exists
    if driver:
        try:
            driver.quit()
        except:
            pass
    
    # Chrome options for stealth
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Randomize window size slightly
    width = random.randint(1200, 1400)
    height = random.randint(800, 1000)
    chrome_options.add_argument(f"--window-size={width},{height}")
    
    # Random user agents (optional)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    # Create driver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute script to hide automation indicators
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Create WebDriverWait instance
    wait = WebDriverWait(driver, 10)
    
    # Small delay to let browser fully initialize
    time.sleep(random.uniform(1, 3))
    
    return driver

def close_driver():
    """Close and cleanup the current driver"""
    global driver, wait
    
    if driver:
        try:
            # Clear all data
            driver.delete_all_cookies()
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
        except:
            pass
        
        try:
            driver.quit()
        except:
            pass
        
        driver = None
        wait = None

def get_current_driver():
    """Get the current driver instance"""
    return driver

def get_current_wait():
    """Get the current wait instance"""  
    return wait