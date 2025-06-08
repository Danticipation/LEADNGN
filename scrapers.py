"""
Lead scraping modules for LeadNGN
Supports multiple platforms and data sources
"""
import requests
import time
import random
import json
import re
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from models import Lead, ScrapingSession, db

logger = logging.getLogger(__name__)

class BaseScraper:
    """Base class for all lead scrapers"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
    def calculate_quality_score(self, lead_data):
        """Calculate lead quality score based on available data"""
        score = 0
        
        # Email presence (30 points)
        if lead_data.get('email'):
            score += 30
            
        # Website presence (20 points)
        if lead_data.get('website'):
            score += 20
            
        # Phone presence (15 points)
        if lead_data.get('phone'):
            score += 15
            
        # Complete contact info (10 points)
        if lead_data.get('contact_name'):
            score += 10
            
        # Industry classification (10 points)
        if lead_data.get('industry'):
            score += 10
            
        # Location info (10 points)
        if lead_data.get('location'):
            score += 10
            
        # Company size info (5 points)
        if lead_data.get('company_size'):
            score += 5
            
        return min(score, 100)
    
    def clean_text(self, text):
        """Clean and normalize text data"""
        if not text:
            return None
        return ' '.join(text.strip().split())
    
    def extract_email(self, text):
        """Extract email from text using regex"""
        if not text:
            return None
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else None
    
    def extract_phone(self, text):
        """Extract phone number from text"""
        if not text:
            return None
        phone_pattern = r'(\+?1?[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
        phones = re.findall(phone_pattern, text)
        return ''.join(phones[0]) if phones else None

class GoogleSearchScraper(BaseScraper):
    """Scraper for finding leads through Google search"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.google.com/search"
    
    def search_companies(self, industry, location=None, company_size=None, limit=20):
        """Search for companies in specific industry and location"""
        leads = []
        
        # Build search query
        query_parts = [industry, "company"]
        if location:
            query_parts.append(location)
        if company_size:
            query_parts.append(company_size)
        
        search_query = " ".join(query_parts)
        
        try:
            params = {
                'q': search_query,
                'num': min(limit, 100)
            }
            
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            search_results = soup.find_all('div', class_='g')
            
            for result in search_results[:limit]:
                try:
                    # Extract basic info from search result
                    title_elem = result.find('h3')
                    link_elem = result.find('a')
                    snippet_elem = result.find('span', class_=['st', 'VwiC3b'])
                    
                    if not title_elem or not link_elem:
                        continue
                    
                    company_name = self.clean_text(title_elem.get_text())
                    website = link_elem.get('href', '').replace('/url?q=', '').split('&')[0]
                    description = self.clean_text(snippet_elem.get_text()) if snippet_elem else ""
                    
                    # Skip non-company results
                    if any(skip in company_name.lower() for skip in ['wikipedia', 'linkedin', 'facebook', 'indeed']):
                        continue
                    
                    lead_data = {
                        'company_name': company_name,
                        'website': website,
                        'industry': industry,
                        'location': location,
                        'company_size': company_size,
                        'description': description,
                        'source': 'Google Search'
                    }
                    
                    # Try to get more details from company website
                    enriched_data = self.enrich_company_data(website)
                    lead_data.update(enriched_data)
                    
                    lead_data['quality_score'] = self.calculate_quality_score(lead_data)
                    leads.append(lead_data)
                    
                    # Add delay to avoid rate limiting
                    time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue
            
            return leads
            
        except Exception as e:
            logger.error(f"Error in Google search: {e}")
            return []
    
    def enrich_company_data(self, website):
        """Extract additional data from company website"""
        enriched_data = {}
        
        if not website or not website.startswith('http'):
            return enriched_data
        
        try:
            response = self.session.get(website, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract contact information
            page_text = soup.get_text()
            
            # Look for email
            email = self.extract_email(page_text)
            if email:
                enriched_data['email'] = email
            
            # Look for phone
            phone = self.extract_phone(page_text)
            if phone:
                enriched_data['phone'] = phone
            
            # Look for contact person in about/team pages
            contact_links = soup.find_all('a', href=re.compile(r'(about|team|contact|management)', re.I))
            if contact_links and len(contact_links) > 0:
                # Try to extract names from these pages
                contact_names = self.extract_contact_names(soup)
                if contact_names:
                    enriched_data['contact_name'] = contact_names[0]
            
        except Exception as e:
            logger.warning(f"Error enriching data for {website}: {e}")
        
        return enriched_data
    
    def extract_contact_names(self, soup):
        """Extract potential contact names from webpage"""
        names = []
        
        # Look for common patterns
        name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\. [A-Z][a-z]+\b',      # F. Last
        ]
        
        text = soup.get_text()
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            names.extend(matches)
        
        # Filter out common false positives
        filtered_names = []
        for name in names:
            if not any(word in name.lower() for word in ['privacy policy', 'terms of service', 'all rights']):
                filtered_names.append(name)
        
        return list(set(filtered_names))[:3]  # Return top 3 unique names

class DirectoryScraper(BaseScraper):
    """Scraper for business directories and listing sites"""
    
    def __init__(self):
        super().__init__()
        self.directories = [
            'yellowpages.com',
            'yelp.com',
            'bbb.org',
            'manta.com'
        ]
    
    def scrape_directory(self, directory_url, industry, location, limit=20):
        """Scrape a specific business directory"""
        leads = []
        
        try:
            # This is a simplified version - real implementation would need
            # specific parsers for each directory
            response = self.session.get(directory_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Generic extraction logic - would need customization per site
            business_listings = soup.find_all(['div', 'article'], class_=re.compile(r'(business|listing|company)'))
            
            for listing in business_listings[:limit]:
                try:
                    # Extract basic information
                    name_elem = listing.find(['h1', 'h2', 'h3', 'h4'])
                    if not name_elem:
                        continue
                    
                    company_name = self.clean_text(name_elem.get_text())
                    
                    # Look for contact info
                    email = self.extract_email(listing.get_text())
                    phone = self.extract_phone(listing.get_text())
                    
                    # Look for website
                    website_elem = listing.find('a', href=re.compile(r'http'))
                    website = website_elem.get('href') if website_elem else None
                    
                    lead_data = {
                        'company_name': company_name,
                        'email': email,
                        'phone': phone,
                        'website': website,
                        'industry': industry,
                        'location': location,
                        'source': f'Directory: {urlparse(directory_url).netloc}',
                        'quality_score': 0
                    }
                    
                    lead_data['quality_score'] = self.calculate_quality_score(lead_data)
                    leads.append(lead_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing directory listing: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping directory {directory_url}: {e}")
        
        return leads

class LinkedInScraper(BaseScraper):
    """LinkedIn scraper for finding company leads"""
    
    def __init__(self):
        super().__init__()
        self.setup_selenium()
    
    def setup_selenium(self):
        """Setup Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            self.driver = None
    
    def search_companies(self, industry, location=None, company_size=None, limit=20):
        """Search LinkedIn for companies"""
        leads = []
        
        if not self.driver:
            logger.error("Chrome driver not available")
            return leads
        
        try:
            # LinkedIn company search URL
            search_url = "https://www.linkedin.com/search/results/companies/"
            
            params = {
                'keywords': industry,
            }
            if location:
                params['geoUrn'] = location
            
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{search_url}?{query_string}"
            
            self.driver.get(full_url)
            time.sleep(3)
            
            # Look for company cards
            company_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-test-id="search-result"]')
            
            for element in company_elements[:limit]:
                try:
                    # Extract company name
                    name_elem = element.find_element(By.CSS_SELECTOR, 'h3 a')
                    company_name = name_elem.text.strip()
                    
                    # Get company URL
                    company_url = name_elem.get_attribute('href')
                    
                    # Extract industry and size info
                    info_text = element.text
                    
                    lead_data = {
                        'company_name': company_name,
                        'website': company_url,
                        'industry': industry,
                        'location': location,
                        'company_size': company_size,
                        'source': 'LinkedIn',
                        'description': info_text
                    }
                    
                    lead_data['quality_score'] = self.calculate_quality_score(lead_data)
                    leads.append(lead_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing LinkedIn company: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
        finally:
            if self.driver:
                self.driver.quit()
        
        return leads

class LeadScrapingEngine:
    """Main engine that orchestrates different scrapers"""
    
    def __init__(self):
        self.scrapers = {
            'google': GoogleSearchScraper(),
            'directory': DirectoryScraper(),
            'linkedin': LinkedInScraper()
        }
    
    def scrape_leads(self, industry, location=None, company_size=None, sources=['google'], limit=50):
        """Scrape leads from multiple sources"""
        
        # Create scraping session
        session = ScrapingSession(
            session_name=f"{industry} leads - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            target_industry=industry,
            target_location=location,
            source_platform=', '.join(sources),
            status='running',
            search_criteria=json.dumps({
                'industry': industry,
                'location': location,
                'company_size': company_size,
                'sources': sources,
                'limit': limit
            })
        )
        
        db.session.add(session)
        db.session.commit()
        
        all_leads = []
        leads_per_source = limit // len(sources)
        
        try:
            for source in sources:
                if source in self.scrapers:
                    logger.info(f"Scraping {source} for {industry} leads")
                    
                    scraper = self.scrapers[source]
                    leads = scraper.search_companies(
                        industry=industry,
                        location=location,
                        company_size=company_size,
                        limit=leads_per_source
                    )
                    
                    # Save leads to database
                    for lead_data in leads:
                        # Check if lead already exists
                        existing_lead = Lead.query.filter_by(
                            company_name=lead_data['company_name']
                        ).first()
                        
                        if not existing_lead:
                            lead = Lead(**lead_data)
                            db.session.add(lead)
                            all_leads.append(lead_data)
                    
                    db.session.commit()
                    logger.info(f"Found {len(leads)} leads from {source}")
            
            # Update session with results
            session.leads_found = len(all_leads)
            session.leads_processed = len(all_leads)
            session.success_rate = 100.0 if len(all_leads) > 0 else 0.0
            session.status = 'completed'
            session.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'session_id': session.id,
                'leads_found': len(all_leads),
                'leads': all_leads
            }
            
        except Exception as e:
            logger.error(f"Error in scraping session: {e}")
            session.status = 'failed'
            db.session.commit()
            raise e