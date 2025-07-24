"""
Business Directory Scraper for LeadNGN
Scrapes legitimate business data from public business directories
"""

import requests
import time
import logging
import re
import json
from typing import Dict, List, Optional
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import trafilatura

logger = logging.getLogger(__name__)

class BusinessDirectoryScraper:
    """Scraper for business directories and public listings"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        self.request_delay = 3  # Be respectful with rate limiting
        self.last_request_time = 0
    
    def rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def scrape_bbb_businesses(self, industry: str, location: str, max_results: int = 10) -> List[Dict]:
        """Scrape Better Business Bureau listings"""
        leads = []
        
        try:
            # BBB search URL
            state = location.split(',')[-1].strip() if ',' in location else location
            search_term = industry.lower().replace(' ', '%20')
            
            # Try BBB search
            bbb_url = f"https://www.bbb.org/search?filter_state={state}&find_entity={search_term}"
            
            self.rate_limit()
            response = self.session.get(bbb_url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for business listings
                business_cards = soup.find_all('div', {'class': ['search-result-card', 'business-card']})
                
                for card in business_cards[:max_results]:
                    try:
                        # Extract business name
                        name_elem = card.find(['h3', 'h4', 'a'])
                        if name_elem:
                            company_name = name_elem.get_text().strip()
                            
                            # Get business URL
                            link_elem = card.find('a')
                            business_url = None
                            if link_elem:
                                href = link_elem.get('href')
                                if href:
                                    business_url = urljoin('https://www.bbb.org', href)
                            
                            if business_url:
                                lead_data = self.scrape_bbb_business_page(business_url, company_name, industry, location)
                                if lead_data:
                                    leads.append(lead_data)
                    
                    except Exception as e:
                        logger.warning(f"Error processing BBB business: {e}")
                        continue
            
            logger.info(f"Found {len(leads)} leads from BBB")
            return leads
            
        except Exception as e:
            logger.error(f"BBB scraping error: {e}")
            return leads
    
    def scrape_chamber_businesses(self, industry: str, location: str, max_results: int = 10) -> List[Dict]:
        """Scrape local Chamber of Commerce listings"""
        leads = []
        
        try:
            # Search for chamber of commerce websites
            city = location.split(',')[0].strip() if ',' in location else location
            chamber_query = f"{city} chamber of commerce business directory"
            
            # This would search for chamber websites, but for now we'll create sample data
            # In production, you'd implement actual chamber directory scraping
            
            return leads
            
        except Exception as e:
            logger.error(f"Chamber scraping error: {e}")
            return leads
    
    def scrape_bbb_business_page(self, url: str, company_name: str, industry: str, location: str) -> Optional[Dict]:
        """Scrape individual BBB business page"""
        try:
            self.rate_limit()
            response = self.session.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract contact information
                phone = ""
                website = ""
                address = ""
                
                # Look for phone number
                phone_elem = soup.find('a', href=re.compile(r'tel:'))
                if phone_elem:
                    phone = phone_elem.get_text().strip()
                
                # Look for website
                website_elem = soup.find('a', {'class': ['website', 'external-link']})
                if website_elem:
                    website = website_elem.get('href', '')
                
                # Look for address
                address_elem = soup.find('div', {'class': ['address', 'location']})
                if address_elem:
                    address = address_elem.get_text().strip()
                
                # Try to get email from website if available
                email = ""
                if website:
                    email = self.extract_email_from_website(website)
                
                # Calculate quality score
                quality_score = self.calculate_quality_score(company_name, email, phone, website, address)
                
                if quality_score >= 60:  # Only return decent quality leads
                    return {
                        'company_name': company_name,
                        'website': website,
                        'email': email,
                        'phone': phone,
                        'industry': industry,
                        'location': location,
                        'quality_score': quality_score,
                        'source': 'bbb_directory',
                        'description': f"BBB-listed {industry} business in {location}",
                        'address': address
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error scraping BBB page {url}: {e}")
            return None
    
    def extract_email_from_website(self, url: str) -> str:
        """Extract email from business website"""
        try:
            self.rate_limit()
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Use trafilatura for text extraction
                text_content = trafilatura.extract(response.text) or ""
                
                # Look for email patterns
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, text_content)
                
                # Return first business email (not personal domains)
                for email in emails:
                    if self.is_business_email(email):
                        return email
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error extracting email from {url}: {e}")
            return ""
    
    def is_business_email(self, email: str) -> bool:
        """Check if email is a business email"""
        personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']
        domain = email.split('@')[1].lower() if '@' in email else ''
        return domain not in personal_domains
    
    def calculate_quality_score(self, company_name: str, email: str, phone: str, website: str, address: str) -> int:
        """Calculate lead quality score"""
        score = 0
        
        if company_name:
            score += 20
        if email:
            score += 30
            if self.is_business_email(email):
                score += 10
        if phone:
            score += 25
        if website and 'http' in website:
            score += 10
        if address:
            score += 5
        
        return min(score, 100)
    
    def generate_directory_leads(self, industry: str, location: str, max_leads: int = 15) -> List[Dict]:
        """Generate leads from business directories"""
        all_leads = []
        
        logger.info(f"Searching business directories for {industry} in {location}")
        
        # Search BBB
        bbb_leads = self.scrape_bbb_businesses(industry, location, max_leads // 2)
        all_leads.extend(bbb_leads)
        
        # Search Chamber of Commerce (would implement actual scraping)
        chamber_leads = self.scrape_chamber_businesses(industry, location, max_leads // 2)
        all_leads.extend(chamber_leads)
        
        # Remove duplicates and sort by quality
        unique_leads = []
        seen_emails = set()
        
        for lead in all_leads:
            email = lead.get('email', '')
            if email and email not in seen_emails:
                seen_emails.add(email)
                unique_leads.append(lead)
        
        unique_leads.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        logger.info(f"Generated {len(unique_leads)} directory leads")
        return unique_leads[:max_leads]

# Global directory scraper instance
directory_scraper = BusinessDirectoryScraper()