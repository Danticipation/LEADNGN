"""
Live Lead Scraper for LeadNGN
Real web scraping implementation for generating legitimate business leads
"""

import requests
import time
import logging
import re
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import trafilatura
from fake_useragent import UserAgent
from email_validator import validate_email, EmailNotValidError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveLeadScraper:
    """Production-ready lead scraper for real business data"""
    
    def __init__(self):
        """Initialize the scraper with proper headers and rate limiting"""
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Rate limiting
        self.request_delay = 2  # seconds between requests
        self.last_request_time = 0
        
        # Chrome driver setup for JavaScript-heavy sites
        self.driver = None
        self.setup_selenium()
        
    def setup_selenium(self):
        """Setup Chrome driver for JavaScript rendering"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={self.ua.random}')
            chrome_options.binary_location = '/usr/bin/chromium'
            
            # Try to use system chromedriver
            from selenium.webdriver.chrome.service import Service
            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium Chrome driver initialized successfully")
            
        except Exception as e:
            logger.warning(f"Selenium setup failed: {e}. Will use requests only.")
            self.driver = None
    
    def rate_limit(self):
        """Implement rate limiting to be respectful"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_google_businesses(self, industry: str, location: str, max_results: int = 20) -> List[Dict]:
        """Search for businesses using alternative methods"""
        leads = []
        
        try:
            # Use DuckDuckGo instead of Google (more scraping-friendly)
            query = f"{industry} {location} business contact email phone"
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            
            self.rate_limit()
            headers = self.session.headers.copy()
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            
            response = self.session.get(search_url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for search results
                result_links = soup.find_all('a', {'class': ['result__url', 'result__a']})
                
                for link in result_links[:max_results]:
                    try:
                        url = link.get('href')
                        if url and url.startswith('http'):
                            # Get the title/company name
                            title_elem = link.find_parent().find(['h2', 'h3'])
                            if title_elem:
                                company_name = title_elem.get_text().strip()
                                
                                # Skip irrelevant results
                                if self.is_relevant_business(company_name, industry):
                                    lead_data = self.scrape_business_details(url, company_name, industry, location)
                                    if lead_data and lead_data.get('email'):
                                        leads.append(lead_data)
                                        
                                        if len(leads) >= max_results:
                                            break
                    
                    except Exception as e:
                        logger.warning(f"Error processing search result: {e}")
                        continue
            
            logger.info(f"Found {len(leads)} leads from search")
            return leads
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return leads
    
    def scrape_yelp_businesses(self, industry: str, location: str, max_results: int = 15) -> List[Dict]:
        """Scrape business data from Yelp"""
        leads = []
        
        try:
            # Construct Yelp search URL
            search_term = industry.lower().replace(' ', '+')
            location_term = location.lower().replace(' ', '+').replace(',', '%2C')
            yelp_url = f"https://www.yelp.com/search?find_desc={search_term}&find_loc={location_term}"
            
            self.rate_limit()
            
            if self.driver:
                self.driver.get(yelp_url)
                time.sleep(3)  # Let JavaScript load
                
                # Find business listings
                business_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/biz/"]')
                
                for link in business_links[:max_results]:
                    try:
                        business_url = link.get_attribute('href')
                        if business_url and '/biz/' in business_url:
                            lead_data = self.scrape_yelp_business_page(business_url, industry, location)
                            if lead_data and lead_data.get('email'):
                                leads.append(lead_data)
                    
                    except Exception as e:
                        logger.warning(f"Error scraping Yelp business: {e}")
                        continue
            
            logger.info(f"Found {len(leads)} leads from Yelp")
            return leads
            
        except Exception as e:
            logger.error(f"Yelp scraping error: {e}")
            return leads
    
    def scrape_yellowpages_businesses(self, industry: str, location: str, max_results: int = 15) -> List[Dict]:
        """Scrape business data from Yellow Pages"""
        leads = []
        
        try:
            # Construct Yellow Pages search URL
            search_term = industry.lower().replace(' ', '%20')
            location_term = location.lower().replace(' ', '%20').replace(',', '%2C')
            yp_url = f"https://www.yellowpages.com/search?search_terms={search_term}&geo_location_terms={location_term}"
            
            self.rate_limit()
            response = self.session.get(yp_url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find business listings
                business_divs = soup.find_all('div', {'class': ['result', 'organic']})
                
                for div in business_divs[:max_results]:
                    try:
                        # Extract business details
                        name_elem = div.find(['h3', 'h2'], {'class': ['business-name', 'n']})
                        if name_elem:
                            company_name = name_elem.get_text().strip()
                            
                            # Get business URL
                            link_elem = name_elem.find('a') if name_elem.name != 'a' else name_elem
                            business_url = None
                            if link_elem:
                                href = link_elem.get('href')
                                if href:
                                    business_url = urljoin('https://www.yellowpages.com', href)
                            
                            if business_url:
                                lead_data = self.scrape_yellowpages_business_page(business_url, company_name, industry, location)
                                if lead_data and lead_data.get('email'):
                                    leads.append(lead_data)
                    
                    except Exception as e:
                        logger.warning(f"Error processing Yellow Pages business: {e}")
                        continue
            
            logger.info(f"Found {len(leads)} leads from Yellow Pages")
            return leads
            
        except Exception as e:
            logger.error(f"Yellow Pages scraping error: {e}")
            return leads
    
    def scrape_business_details(self, url: str, company_name: str, industry: str, location: str) -> Optional[Dict]:
        """Scrape detailed information from a business website"""
        try:
            self.rate_limit()
            
            # Try to get website content
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            # Use trafilatura for clean text extraction
            text_content = trafilatura.extract(response.text) or ""
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract contact information
            email = self.extract_email_from_content(text_content, soup)
            phone = self.extract_phone_from_content(text_content, soup)
            
            # Calculate quality score based on available data
            quality_score = self.calculate_quality_score(company_name, email, phone, url, text_content)
            
            if email and quality_score >= 60:  # Only return if we have email and decent quality
                return {
                    'company_name': company_name,
                    'website': url,
                    'email': email,
                    'phone': phone,
                    'industry': industry,
                    'location': location,
                    'quality_score': quality_score,
                    'source': 'live_scraping',
                    'description': self.extract_business_description(text_content),
                    'contact_name': self.extract_contact_name(text_content, soup)
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error scraping business details from {url}: {e}")
            return None
    
    def scrape_yelp_business_page(self, url: str, industry: str, location: str) -> Optional[Dict]:
        """Scrape details from individual Yelp business page"""
        try:
            if not self.driver:
                return None
                
            self.rate_limit()
            self.driver.get(url)
            time.sleep(2)
            
            # Extract business name
            company_name = ""
            try:
                name_elem = self.driver.find_element(By.CSS_SELECTOR, 'h1')
                company_name = name_elem.text.strip()
            except NoSuchElementException:
                return None
            
            # Look for website link
            website = ""
            try:
                website_elem = self.driver.find_element(By.CSS_SELECTOR, 'a[href*="biz_redir"]')
                website = website_elem.get_attribute('href')
            except NoSuchElementException:
                pass
            
            # If we found a website, scrape it for contact details
            if website and company_name:
                return self.scrape_business_details(website, company_name, industry, location)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error scraping Yelp page {url}: {e}")
            return None
    
    def scrape_yellowpages_business_page(self, url: str, company_name: str, industry: str, location: str) -> Optional[Dict]:
        """Scrape details from Yellow Pages business page"""
        try:
            self.rate_limit()
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract website
                website = ""
                website_elem = soup.find('a', {'class': ['website', 'track-visit-website']})
                if website_elem:
                    website = website_elem.get('href', '')
                
                # Extract phone
                phone = ""
                phone_elem = soup.find(['span', 'div'], {'class': ['phone', 'phones']})
                if phone_elem:
                    phone = phone_elem.get_text().strip()
                
                # If we have a website, scrape it for email
                email = ""
                if website:
                    try:
                        lead_data = self.scrape_business_details(website, company_name, industry, location)
                        if lead_data:
                            return lead_data
                    except:
                        pass
                
                # Fall back to Yellow Pages data if no website
                if phone:
                    quality_score = self.calculate_quality_score(company_name, email, phone, url, "")
                    if quality_score >= 50:
                        return {
                            'company_name': company_name,
                            'website': website or url,
                            'email': email,
                            'phone': phone,
                            'industry': industry,
                            'location': location,
                            'quality_score': quality_score,
                            'source': 'yellowpages',
                            'description': f"{industry} business in {location}",
                            'contact_name': ""
                        }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error scraping Yellow Pages page {url}: {e}")
            return None
    
    def extract_email_from_content(self, text: str, soup: BeautifulSoup) -> str:
        """Extract email addresses from website content"""
        # Look for emails in text content
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Also check mailto links
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
        for link in mailto_links:
            href = link.get('href', '')
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0]
                emails.append(email)
        
        # Validate and return best email
        for email in emails:
            try:
                if self.is_business_email(email):
                    validate_email(email)
                    return email
            except EmailNotValidError:
                continue
        
        return ""
    
    def extract_phone_from_content(self, text: str, soup: BeautifulSoup) -> str:
        """Extract phone numbers from website content"""
        # Phone number patterns
        phone_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',  # (123) 456-7890
            r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
            r'\b\d{10}\b',  # 1234567890
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        # Check tel: links
        tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
        for link in tel_links:
            href = link.get('href', '')
            if href.startswith('tel:'):
                phone = href.replace('tel:', '').replace('+1', '').strip()
                if len(phone) >= 10:
                    return phone
        
        return ""
    
    def extract_contact_name(self, text: str, soup: BeautifulSoup) -> str:
        """Extract contact person name from website content"""
        # Look for common contact patterns
        contact_patterns = [
            r'Contact:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Owner:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Manager:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'President:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        for pattern in contact_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return ""
    
    def extract_business_description(self, text: str) -> str:
        """Extract business description from website content"""
        if len(text) > 200:
            # Find the first meaningful paragraph
            paragraphs = text.split('\n')
            for para in paragraphs:
                if len(para) > 50 and len(para) < 300:
                    return para.strip()
            
            # Fallback to first 200 characters
            return text[:200] + "..." if len(text) > 200 else text
        
        return text
    
    def is_relevant_business(self, company_name: str, industry: str) -> bool:
        """Check if business name is relevant to the target industry"""
        industry_keywords = {
            'HVAC': ['hvac', 'heating', 'cooling', 'air conditioning', 'climate', 'furnace'],
            'Dental': ['dental', 'dentist', 'orthodontics', 'oral', 'teeth', 'smile'],
            'Legal': ['law', 'legal', 'attorney', 'lawyer', 'firm', 'counsel'],
            'Plumbing': ['plumbing', 'plumber', 'pipe', 'drain', 'water', 'sewer'],
        }
        
        keywords = industry_keywords.get(industry, [])
        company_lower = company_name.lower()
        
        return any(keyword in company_lower for keyword in keywords)
    
    def is_business_email(self, email: str) -> bool:
        """Check if email looks like a business email (not personal)"""
        personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']
        domain = email.split('@')[1].lower() if '@' in email else ''
        return domain not in personal_domains
    
    def calculate_quality_score(self, company_name: str, email: str, phone: str, website: str, content: str) -> int:
        """Calculate lead quality score based on available data"""
        score = 0
        
        # Base score for having a company name
        if company_name:
            score += 20
        
        # Email presence and quality
        if email:
            score += 30
            if self.is_business_email(email):
                score += 10
        
        # Phone number presence
        if phone:
            score += 20
        
        # Professional website
        if website and not any(domain in website for domain in ['yelp.com', 'yellowpages.com', 'facebook.com']):
            score += 15
        
        # Content quality
        if len(content) > 500:
            score += 5
        
        return min(score, 100)
    
    def generate_live_leads(self, industry: str, location: str, max_leads: int = 20) -> List[Dict]:
        """Generate real leads from multiple sources"""
        all_leads = []
        
        logger.info(f"Starting live lead generation for {industry} in {location}")
        
        # Search Google (primary source)
        google_leads = self.search_google_businesses(industry, location, max_leads // 2)
        all_leads.extend(google_leads)
        
        # Search Yellow Pages
        if len(all_leads) < max_leads:
            yp_leads = self.scrape_yellowpages_businesses(industry, location, max_leads // 3)
            all_leads.extend(yp_leads)
        
        # Search Yelp if we still need more
        if len(all_leads) < max_leads and self.driver:
            yelp_leads = self.scrape_yelp_businesses(industry, location, max_leads // 4)
            all_leads.extend(yelp_leads)
        
        # Remove duplicates based on email
        seen_emails = set()
        unique_leads = []
        for lead in all_leads:
            if lead.get('email') and lead['email'] not in seen_emails:
                seen_emails.add(lead['email'])
                unique_leads.append(lead)
        
        # Sort by quality score
        unique_leads.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        logger.info(f"Generated {len(unique_leads)} unique high-quality leads")
        return unique_leads[:max_leads]
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
        self.session.close()

# Global scraper instance
live_scraper = LiveLeadScraper()