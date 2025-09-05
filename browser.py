import sys
import os
from config import WAIT_SECS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_driver():
    """Create and return Chrome driver - call this function instead of using global driver"""
    chromedriver_path = resource_path('chromedriver.exe')
    
    # Debug: print the path (remove this line after testing)
    print(f"Looking for ChromeDriver at: {chromedriver_path}")
    
    if not os.path.exists(chromedriver_path):
        raise FileNotFoundError(f"ChromeDriver not found at: {chromedriver_path}")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service)
    return driver

def create_wait(driver):
    """Create WebDriverWait for the given driver"""
    return WebDriverWait(driver, WAIT_SECS)