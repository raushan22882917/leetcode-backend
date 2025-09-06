from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

app = FastAPI(title="LeetCode Profile Scraper", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class ProfileData(BaseModel):
    name: str
    username: str
    rank: str
    avatar_url: str
    location: Optional[str] = None
    university: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    skills: List[str] = []
    contest_rating: Optional[str] = None
    global_ranking: Optional[str] = None
    contests_attended: Optional[str] = None
    problems_solved: Optional[str] = None
    acceptance_rate: Optional[str] = None
    easy_problems: Optional[str] = None
    medium_problems: Optional[str] = None
    hard_problems: Optional[str] = None
    problems_attempting: Optional[str] = None
    submissions_past_year: Optional[str] = None
    total_active_days: Optional[str] = None
    max_streak: Optional[str] = None

class ScrapeRequest(BaseModel):
    username: str

def get_chrome_driver():
    """Create and configure Chrome WebDriver with fallback handling"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Try to install Chrome driver
        driver_path = ChromeDriverManager().install()
        print(f"Chrome driver path: {driver_path}")
        
        # Fix the path if it points to the wrong file
        if "THIRD_PARTY_NOTICES" in driver_path:
            # Find the actual chromedriver.exe in the same directory
            import os
            driver_dir = os.path.dirname(driver_path)
            for file in os.listdir(driver_dir):
                if file.startswith("chromedriver") and file.endswith(".exe"):
                    driver_path = os.path.join(driver_dir, file)
                    break
        
        print(f"Corrected driver path: {driver_path}")
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        print(f"Chrome driver not available: {e}")
        print("Falling back to requests-only scraping...")
        return None

def scrape_leetcode_profile(username: str) -> ProfileData:
    """
    Scrape LeetCode profile data using Selenium for dynamic content with fallback to requests
    """
    profile_data = ProfileData(
        name="",
        username=username,
        rank="",
        avatar_url="",
        skills=[],
        contest_rating=None,
        global_ranking=None,
        contests_attended=None,
        problems_solved=None,
        acceptance_rate=None,
        easy_problems=None,
        medium_problems=None,
        hard_problems=None,
        problems_attempting=None,
        submissions_past_year=None,
        total_active_days=None,
        max_streak=None
    )
    
    driver = None
    try:
        # Try to initialize Chrome driver
        driver = get_chrome_driver()
        
        if driver:
            # Use Selenium for dynamic content
            url = f"https://leetcode.com/u/{username}/"
            driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            
            # Wait for profile content to load
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)  # Additional wait for dynamic content
            except:
                pass
            
            # Get page source and parse with BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract profile data using Selenium selectors
            profile_data = extract_profile_with_selenium(driver, soup, username)
            
            # If we didn't get data with Selenium, try BeautifulSoup parsing
            if not profile_data.name and not profile_data.rank:
                profile_data = extract_from_html(soup, username)
        else:
            # Fallback to requests-only approach
            print("Using requests-only scraping approach...")
            profile_data = scrape_with_requests_only(username)
        
        # If still no data, try GraphQL API
        if not profile_data.name and not profile_data.rank:
            profile_data = try_graphql_api(username, {})
        
        if profile_data.name or profile_data.rank:
            return profile_data
        else:
            raise HTTPException(status_code=404, detail="Profile not found or data not accessible")
            
    except Exception as e:
        print(f"Detailed error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error scraping profile: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def scrape_with_requests_only(username: str) -> ProfileData:
    """Scrape LeetCode profile using only requests and BeautifulSoup (fallback method)"""
    profile_data = ProfileData(
        name="",
        username=username,
        rank="",
        avatar_url="",
        skills=[],
        contest_rating=None,
        global_ranking=None,
        contests_attended=None,
        problems_solved=None,
        acceptance_rate=None,
        easy_problems=None,
        medium_problems=None,
        hard_problems=None,
        problems_attempting=None,
        submissions_past_year=None,
        total_active_days=None,
        max_streak=None
    )
    
    try:
        # Headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Try to get the profile page
        url = f"https://leetcode.com/u/{username}/"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract profile data from HTML
        profile_data = extract_from_html(soup, username)
        
        # If we still don't have data, try to find JSON data in script tags
        if not profile_data.name and not profile_data.rank:
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'profile' in script.string.lower():
                    try:
                        # Try to extract JSON data from script tags
                        script_content = script.string
                        if 'window.__INITIAL_STATE__' in script_content:
                            # Extract JSON data
                            start = script_content.find('{')
                            end = script_content.rfind('}') + 1
                            if start != -1 and end != -1:
                                json_str = script_content[start:end]
                                data = json.loads(json_str)
                                profile_data = extract_from_json_data(data, username)
                                if profile_data.name or profile_data.rank:
                                    break
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
        
    except Exception as e:
        print(f"Error in requests-only scraping: {e}")
    
    return profile_data

def extract_profile_with_selenium(driver, soup, username):
    """Extract profile data using Selenium WebDriver"""
    profile_data = ProfileData(
        name="",
        username=username,
        rank="",
        avatar_url="",
        skills=[],
        contest_rating=None,
        global_ranking=None,
        contests_attended=None,
        problems_solved=None,
        acceptance_rate=None,
        easy_problems=None,
        medium_problems=None,
        hard_problems=None,
        problems_attempting=None,
        submissions_past_year=None,
        total_active_days=None,
        max_streak=None
    )
    
    try:
        # Try to find profile elements using Selenium
        selectors = {
            'name': [
                'div[class*="text-label-1"]',
                'h1',
                '.text-label-1',
                '[data-testid="profile-name"]'
            ],
            'avatar': [
                'img[alt*="Avatar"]',
                'img[alt*="avatar"]',
                '.avatar img',
                'img[src*="avatar"]'
            ],
            'rank': [
                'span[class*="rank"]',
                '.ranking',
                '[data-testid="ranking"]'
            ],
            'location': [
                'div[class*="location"]',
                '.location',
                '[data-testid="location"]'
            ],
            'github': [
                'a[href*="github.com"]',
                '.github-link'
            ],
            'linkedin': [
                'a[href*="linkedin.com"]',
                '.linkedin-link'
            ]
        }
        
        # Extract name - be more specific
        name_selectors = [
            'div[class*="text-label-1"]:not([class*="text-label-2"]):not([class*="text-label-3"])',
            'h1:not([class*="text-label-2"])',
            '.text-label-1:not(.text-label-2):not(.text-label-3)',
            '[data-testid="profile-name"]'
        ]
        
        for selector in name_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    # Filter out very long text (likely page content)
                    if text and len(text) < 100 and not profile_data.name:
                        # Additional check to ensure it's a name-like text
                        if not any(word in text.lower() for word in ['problems', 'contest', 'discuss', 'interview', 'store', 'register', 'log', 'premium']):
                            profile_data.name = text
                            break
                if profile_data.name:
                    break
            except:
                continue
        
        # Extract avatar
        for selector in selectors['avatar']:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    src = element.get_attribute('src')
                    if src and not profile_data.avatar_url:
                        profile_data.avatar_url = src
                        break
                if profile_data.avatar_url:
                    break
            except:
                continue
        
        # Extract rank - look for numbers after "Rank"
        try:
            # Look for elements containing "Rank" followed by a number
            rank_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Rank')]/following-sibling::*[1]")
            for element in rank_elements:
                text = element.text.strip()
                if text and text.replace(',', '').replace('.', '').isdigit() and not profile_data.rank:
                    profile_data.rank = text
                    break
            
            # Fallback: look for any element with a large number
            if not profile_data.rank:
                all_elements = driver.find_elements(By.XPATH, "//*[text()[matches(., '^[0-9,]+$')]]")
                for element in all_elements:
                    text = element.text.strip()
                    if text and len(text) > 3 and text.replace(',', '').isdigit() and not profile_data.rank:
                        profile_data.rank = text
                        break
        except:
            pass
        
        # Extract location
        for selector in selectors['location']:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and not profile_data.location:
                        profile_data.location = text
                        break
                if profile_data.location:
                    break
            except:
                continue
        
        # Extract GitHub link
        for selector in selectors['github']:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    if href and 'github.com' in href and not profile_data.github:
                        profile_data.github = href.split('/')[-1]
                        break
                if profile_data.github:
                    break
            except:
                continue
        
        # Extract LinkedIn link
        for selector in selectors['linkedin']:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    if href and 'linkedin.com' in href and not profile_data.linkedin:
                        profile_data.linkedin = href.split('/')[-1]
                        break
                if profile_data.linkedin:
                    break
            except:
                continue
        
        # Extract contest rating information
        try:
            # Look for contest rating section
            contest_rating_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'Contest Rating')]/following-sibling::div")
            for element in contest_rating_elements:
                text = element.text.strip()
                if text and text.replace(',', '').isdigit() and not profile_data.contest_rating:
                    profile_data.contest_rating = text
                    break
            
            # Look for global ranking
            global_ranking_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'Global Ranking')]/following-sibling::div")
            for element in global_ranking_elements:
                text = element.text.strip()
                if text and '/' in text and not profile_data.global_ranking:
                    profile_data.global_ranking = text
                    break
            
            # Look for contests attended
            attended_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'Attended')]/following-sibling::div")
            for element in attended_elements:
                text = element.text.strip()
                if text and text.isdigit() and not profile_data.contests_attended:
                    profile_data.contests_attended = text
                    break
        except:
            pass
        
        # Extract problem-solving statistics
        try:
            # Look for problems solved (format: "166/3671")
            solved_elements = driver.find_elements(By.XPATH, "//span[contains(text(), '/') and contains(text(), '3671')]")
            for element in solved_elements:
                text = element.text.strip()
                if text and '/' in text and not profile_data.problems_solved:
                    profile_data.problems_solved = text
                    break
            
            # Look for acceptance rate (format: "65.67%")
            acceptance_elements = driver.find_elements(By.XPATH, "//span[contains(text(), '%')]")
            for element in acceptance_elements:
                text = element.text.strip()
                if text and '%' in text and '.' in text and not profile_data.acceptance_rate:
                    profile_data.acceptance_rate = text
                    break
            
            # Look for Easy problems (format: "81/895")
            easy_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'Easy')]/following-sibling::div")
            for element in easy_elements:
                text = element.text.strip()
                if text and '/' in text and not profile_data.easy_problems:
                    profile_data.easy_problems = text
                    break
            
            # Look for Medium problems (format: "68/1911")
            medium_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'Med.')]/following-sibling::div")
            for element in medium_elements:
                text = element.text.strip()
                if text and '/' in text and not profile_data.medium_problems:
                    profile_data.medium_problems = text
                    break
            
            # Look for Hard problems (format: "17/865")
            hard_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'Hard')]/following-sibling::div")
            for element in hard_elements:
                text = element.text.strip()
                if text and '/' in text and not profile_data.hard_problems:
                    profile_data.hard_problems = text
                    break
            
            # Look for problems attempting (format: "6 Attempting")
            attempting_elements = driver.find_elements(By.XPATH, "//span[contains(text(), 'Attempting')]")
            for element in attempting_elements:
                text = element.text.strip()
                if text and 'Attempting' in text and not profile_data.problems_attempting:
                    profile_data.problems_attempting = text
                    break
        except:
            pass
        
        # Extract activity statistics
        try:
            # Look for submissions in past year (format: "89 submissions in the past one year")
            submissions_elements = driver.find_elements(By.XPATH, "//span[contains(text(), 'submissions in the past one year')]")
            for element in submissions_elements:
                text = element.text.strip()
                if text and 'submissions in the past one year' in text and not profile_data.submissions_past_year:
                    # Extract the number before "submissions"
                    parts = text.split(' ')
                    if len(parts) > 0 and parts[0].isdigit():
                        profile_data.submissions_past_year = parts[0]
                        break
            
            # Look for total active days (format: "Total active days: 22")
            active_days_elements = driver.find_elements(By.XPATH, "//span[contains(text(), 'Total active days:')]")
            for element in active_days_elements:
                text = element.text.strip()
                if text and 'Total active days:' in text and not profile_data.total_active_days:
                    # Extract the number after the colon
                    parts = text.split(':')
                    if len(parts) > 1:
                        number = parts[1].strip()
                        if number.isdigit():
                            profile_data.total_active_days = number
                            break
            
            # Look for max streak (format: "Max streak: 5")
            streak_elements = driver.find_elements(By.XPATH, "//span[contains(text(), 'Max streak:')]")
            for element in streak_elements:
                text = element.text.strip()
                if text and 'Max streak:' in text and not profile_data.max_streak:
                    # Extract the number after the colon
                    parts = text.split(':')
                    if len(parts) > 1:
                        number = parts[1].strip()
                        if number.isdigit():
                            profile_data.max_streak = number
                            break
        except:
            pass
        
        # Extract skills from page text
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            skill_keywords = ['python', 'java', 'javascript', 'c++', 'sql', 'dsa', 'dbms', 'aida', 'react', 'node.js']
            for keyword in skill_keywords:
                if keyword in page_text and keyword not in profile_data.skills:
                    profile_data.skills.append(keyword)
        except:
            pass
            
    except Exception as e:
        print(f"Error in Selenium extraction: {e}")
    
    return profile_data

def extract_from_json_data(data: dict, username: str) -> ProfileData:
    """Extract profile data from JSON embedded in the page"""
    profile_data = ProfileData(
        name="",
        username=username,
        rank="",
        avatar_url="",
        skills=[],
        contest_rating=None,
        global_ranking=None,
        contests_attended=None,
        problems_solved=None,
        acceptance_rate=None,
        easy_problems=None,
        medium_problems=None,
        hard_problems=None,
        problems_attempting=None,
        submissions_past_year=None,
        total_active_days=None,
        max_streak=None
    )
    
    try:
        # Navigate through the JSON structure to find profile data
        if 'profile' in data:
            profile_info = data['profile']
            profile_data.name = profile_info.get('realName', '')
            profile_data.rank = str(profile_info.get('ranking', ''))
            profile_data.avatar_url = profile_info.get('userAvatar', '')
            profile_data.location = profile_info.get('location', '')
            profile_data.github = profile_info.get('githubUrl', '')
            profile_data.linkedin = profile_info.get('linkedinUrl', '')
            
            # Extract skills from tags or other fields
            if 'skillTags' in profile_info:
                profile_data.skills = profile_info['skillTags']
    except (KeyError, TypeError):
        pass
    
    return profile_data

def extract_from_html(soup: BeautifulSoup, username: str) -> ProfileData:
    """Extract profile data from HTML elements"""
    profile_data = ProfileData(
        name="",
        username=username,
        rank="",
        avatar_url="",
        skills=[],
        contest_rating=None,
        global_ranking=None,
        contests_attended=None,
        problems_solved=None,
        acceptance_rate=None,
        easy_problems=None,
        medium_problems=None,
        hard_problems=None,
        problems_attempting=None,
        submissions_past_year=None,
        total_active_days=None,
        max_streak=None
    )
    
    try:
        # Look for various possible selectors
        selectors_to_try = [
            {'name': 'div[class*="text-label-1"]', 'type': 'name'},
            {'name': 'h1', 'type': 'name'},
            {'name': 'img[alt*="Avatar"]', 'type': 'avatar'},
            {'name': 'span[class*="rank"]', 'type': 'rank'},
            {'name': 'div[class*="location"]', 'type': 'location'},
            {'name': 'a[href*="github"]', 'type': 'github'},
            {'name': 'a[href*="linkedin"]', 'type': 'linkedin'},
        ]
        
        for selector in selectors_to_try:
            elements = soup.select(selector['name'])
            for element in elements:
                if selector['type'] == 'name' and not profile_data.name:
                    profile_data.name = element.get_text(strip=True)
                elif selector['type'] == 'avatar' and not profile_data.avatar_url:
                    profile_data.avatar_url = element.get('src', '')
                elif selector['type'] == 'rank' and not profile_data.rank:
                    text = element.get_text(strip=True)
                    if text.replace(',', '').replace('.', '').isdigit():
                        profile_data.rank = text
                elif selector['type'] == 'location' and not profile_data.location:
                    profile_data.location = element.get_text(strip=True)
                elif selector['type'] == 'github' and not profile_data.github:
                    href = element.get('href', '')
                    if 'github.com' in href:
                        profile_data.github = href.split('/')[-1]
                elif selector['type'] == 'linkedin' and not profile_data.linkedin:
                    href = element.get('href', '')
                    if 'linkedin.com' in href:
                        profile_data.linkedin = href.split('/')[-1]
        
        # Extract contest rating information from HTML
        try:
            # Look for contest rating in HTML
            contest_rating_divs = soup.find_all('div', string=lambda text: text and 'Contest Rating' in text)
            for div in contest_rating_divs:
                parent = div.parent
                if parent:
                    rating_div = parent.find('div', class_='text-label-1')
                    if rating_div and rating_div.get_text(strip=True).replace(',', '').isdigit():
                        profile_data.contest_rating = rating_div.get_text(strip=True)
                        break
            
            # Look for global ranking
            global_ranking_divs = soup.find_all('div', string=lambda text: text and 'Global Ranking' in text)
            for div in global_ranking_divs:
                parent = div.parent
                if parent:
                    ranking_div = parent.find('div', class_='text-label-1')
                    if ranking_div and '/' in ranking_div.get_text(strip=True):
                        profile_data.global_ranking = ranking_div.get_text(strip=True)
                        break
            
            # Look for contests attended
            attended_divs = soup.find_all('div', string=lambda text: text and 'Attended' in text)
            for div in attended_divs:
                parent = div.parent
                if parent:
                    attended_div = parent.find('div', class_='text-label-1')
                    if attended_div and attended_div.get_text(strip=True).isdigit():
                        profile_data.contests_attended = attended_div.get_text(strip=True)
                        break
        except:
            pass
        
        # Extract problem-solving statistics from HTML
        try:
            # Look for problems solved (format: "166/3671")
            solved_spans = soup.find_all('span', string=lambda text: text and '/' in text and '3671' in text)
            for span in solved_spans:
                text = span.get_text(strip=True)
                if text and '/' in text and not profile_data.problems_solved:
                    profile_data.problems_solved = text
                    break
            
            # Look for acceptance rate (format: "65.67%")
            acceptance_spans = soup.find_all('span', string=lambda text: text and '%' in text and '.' in text)
            for span in acceptance_spans:
                text = span.get_text(strip=True)
                if text and '%' in text and '.' in text and not profile_data.acceptance_rate:
                    profile_data.acceptance_rate = text
                    break
            
            # Look for Easy problems (format: "81/895")
            easy_divs = soup.find_all('div', string=lambda text: text and 'Easy' in text)
            for div in easy_divs:
                parent = div.parent
                if parent:
                    easy_div = parent.find('div', class_='text-xs')
                    if easy_div and '/' in easy_div.get_text(strip=True):
                        profile_data.easy_problems = easy_div.get_text(strip=True)
                        break
            
            # Look for Medium problems (format: "68/1911")
            medium_divs = soup.find_all('div', string=lambda text: text and 'Med.' in text)
            for div in medium_divs:
                parent = div.parent
                if parent:
                    medium_div = parent.find('div', class_='text-xs')
                    if medium_div and '/' in medium_div.get_text(strip=True):
                        profile_data.medium_problems = medium_div.get_text(strip=True)
                        break
            
            # Look for Hard problems (format: "17/865")
            hard_divs = soup.find_all('div', string=lambda text: text and 'Hard' in text)
            for div in hard_divs:
                parent = div.parent
                if parent:
                    hard_div = parent.find('div', class_='text-xs')
                    if hard_div and '/' in hard_div.get_text(strip=True):
                        profile_data.hard_problems = hard_div.get_text(strip=True)
                        break
            
            # Look for problems attempting (format: "6 Attempting")
            attempting_spans = soup.find_all('span', string=lambda text: text and 'Attempting' in text)
            for span in attempting_spans:
                text = span.get_text(strip=True)
                if text and 'Attempting' in text and not profile_data.problems_attempting:
                    profile_data.problems_attempting = text
                    break
        except:
            pass
        
        # Extract activity statistics from HTML
        try:
            # Look for submissions in past year (format: "89 submissions in the past one year")
            submissions_spans = soup.find_all('span', string=lambda text: text and 'submissions in the past one year' in text)
            for span in submissions_spans:
                text = span.get_text(strip=True)
                if text and 'submissions in the past one year' in text and not profile_data.submissions_past_year:
                    # Extract the number before "submissions"
                    parts = text.split(' ')
                    if len(parts) > 0 and parts[0].isdigit():
                        profile_data.submissions_past_year = parts[0]
                        break
            
            # Look for total active days (format: "Total active days: 22")
            active_days_spans = soup.find_all('span', string=lambda text: text and 'Total active days:' in text)
            for span in active_days_spans:
                text = span.get_text(strip=True)
                if text and 'Total active days:' in text and not profile_data.total_active_days:
                    # Extract the number after the colon
                    parts = text.split(':')
                    if len(parts) > 1:
                        number = parts[1].strip()
                        if number.isdigit():
                            profile_data.total_active_days = number
                            break
            
            # Look for max streak (format: "Max streak: 5")
            streak_spans = soup.find_all('span', string=lambda text: text and 'Max streak:' in text)
            for span in streak_spans:
                text = span.get_text(strip=True)
                if text and 'Max streak:' in text and not profile_data.max_streak:
                    # Extract the number after the colon
                    parts = text.split(':')
                    if len(parts) > 1:
                        number = parts[1].strip()
                        if number.isdigit():
                            profile_data.max_streak = number
                            break
        except:
            pass
        
        # Extract skills from various possible locations
        skill_keywords = ['python', 'java', 'javascript', 'c++', 'sql', 'dsa', 'dbms', 'aida']
        all_text = soup.get_text().lower()
        for keyword in skill_keywords:
            if keyword in all_text and keyword not in profile_data.skills:
                profile_data.skills.append(keyword)
                
    except Exception:
        pass
    
    return profile_data

def try_graphql_api(username: str, headers: dict) -> ProfileData:
    """Try to get data using LeetCode's GraphQL API"""
    profile_data = ProfileData(
        name="",
        username=username,
        rank="",
        avatar_url="",
        skills=[],
        contest_rating=None,
        global_ranking=None,
        contests_attended=None,
        problems_solved=None,
        acceptance_rate=None,
        easy_problems=None,
        medium_problems=None,
        hard_problems=None,
        problems_attempting=None,
        submissions_past_year=None,
        total_active_days=None,
        max_streak=None
    )
    
    try:
        # LeetCode GraphQL endpoint
        graphql_url = "https://leetcode.com/graphql/"
        
        query = """
        query userPublicProfile($username: String!) {
            matchedUser(username: $username) {
                username
                profile {
                    realName
                    userAvatar
                    ranking
                    location
                    githubUrl
                    linkedinUrl
                    skillTags
                }
            }
        }
        """
        
        variables = {"username": username}
        
        payload = {
            "query": query,
            "variables": variables
        }
        
        response = requests.post(graphql_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' in data and 'matchedUser' in data['data']:
            user_data = data['data']['matchedUser']
            if user_data and 'profile' in user_data:
                profile = user_data['profile']
                profile_data.name = profile.get('realName', '')
                profile_data.rank = str(profile.get('ranking', ''))
                profile_data.avatar_url = profile.get('userAvatar', '')
                profile_data.location = profile.get('location', '')
                profile_data.github = profile.get('githubUrl', '')
                profile_data.linkedin = profile.get('linkedinUrl', '')
                profile_data.skills = profile.get('skillTags', [])
                
    except Exception:
        pass
    
    return profile_data

@app.get("/")
async def root():
    return {"message": "LeetCode Profile Scraper API", "version": "1.0.0"}

@app.post("/scrape-profile", response_model=ProfileData)
async def scrape_profile(request: ScrapeRequest):
    """
    Scrape LeetCode profile data for a given username
    """
    try:
        profile_data = scrape_leetcode_profile(request.username)
        return profile_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/scrape-profile/{username}", response_model=ProfileData)
async def scrape_profile_get(username: str):
    """
    Scrape LeetCode profile data for a given username (GET endpoint)
    """
    try:
        profile_data = scrape_leetcode_profile(username)
        return profile_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/test-scrape/{username}")
async def test_scrape(username: str):
    """
    Test endpoint to debug scraping issues with Selenium
    """
    driver = None
    try:
        driver = get_chrome_driver()
        
        if driver:
            url = f"https://leetcode.com/u/{username}/"
            driver.get(url)
            
            # Wait for page to load
            time.sleep(5)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            return {
                "method": "selenium",
                "url": url,
                "page_title": driver.title,
                "content_length": len(page_source),
                "has_script_tags": len(soup.find_all('script')),
                "page_loaded": "body" in page_source.lower(),
                "profile_elements_found": {
                    "name_elements": len(driver.find_elements(By.CSS_SELECTOR, 'div[class*="text-label-1"]')),
                    "avatar_elements": len(driver.find_elements(By.CSS_SELECTOR, 'img[alt*="Avatar"]')),
                    "rank_elements": len(driver.find_elements(By.CSS_SELECTOR, 'span[class*="rank"]')),
                    "github_links": len(driver.find_elements(By.CSS_SELECTOR, 'a[href*="github.com"]')),
                    "linkedin_links": len(driver.find_elements(By.CSS_SELECTOR, 'a[href*="linkedin.com"]'))
                }
            }
        else:
            # Test requests-only approach
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            url = f"https://leetcode.com/u/{username}/"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return {
                "method": "requests_only",
                "url": url,
                "status_code": response.status_code,
                "content_length": len(response.content),
                "has_script_tags": len(soup.find_all('script')),
                "page_loaded": "body" in response.text.lower(),
                "profile_elements_found": {
                    "name_elements": len(soup.select('div[class*="text-label-1"]')),
                    "avatar_elements": len(soup.select('img[alt*="Avatar"]')),
                    "rank_elements": len(soup.select('span[class*="rank"]')),
                    "github_links": len(soup.select('a[href*="github.com"]')),
                    "linkedin_links": len(soup.select('a[href*="linkedin.com"]'))
                }
            }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
