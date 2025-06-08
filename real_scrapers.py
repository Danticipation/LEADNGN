"""
Real lead scraping implementation for LeadNGN
Targets high-value local service businesses
"""
import requests
import time
import random
import json
import re
from urllib.parse import urljoin, urlparse, quote_plus
from datetime import datetime
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import logging
from models import Lead, ScrapingSession, db

logger = logging.getLogger(__name__)

class RealLeadScraper:
    """Production-ready lead scraper for local service businesses"""
    
    def __init__(self):
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
        
        # Industry-specific search terms for better targeting
        self.industry_keywords = {
            'hvac': ['HVAC contractor', 'heating cooling', 'air conditioning repair', 'furnace installation'],
            'plumbing': ['plumber', 'plumbing services', 'drain cleaning', 'pipe repair'],
            'legal': ['attorney', 'lawyer', 'law firm', 'legal services'],
            'dental': ['dentist', 'dental office', 'orthodontist', 'dental practice'],
            'medical': ['doctor office', 'medical practice', 'physician', 'clinic'],
            'real_estate': ['real estate agent', 'realtor', 'property broker', 'real estate office'],
            'auto': ['auto repair', 'car dealership', 'automotive service', 'mechanic'],
            'property_management': ['property management', 'rental management', 'property manager'],
            'ecommerce': ['online store', 'ecommerce', 'retail business'],
            'education': ['private school', 'trade school', 'tutoring center', 'education services'],
            'fitness': ['gym', 'fitness center', 'yoga studio', 'personal trainer'],
            'events': ['event planner', 'wedding planner', 'DJ services', 'event venue']
        }
    
    def calculate_quality_score(self, lead_data):
        """Calculate lead quality score based on available information"""
        score = 0
        
        # Phone number (35 points) - crucial for local services
        if lead_data.get('phone'):
            score += 35
            
        # Email address (25 points)
        if lead_data.get('email'):
            score += 25
            
        # Website (20 points)
        if lead_data.get('website'):
            score += 20
            
        # Physical address (15 points) - important for local businesses
        if lead_data.get('location'):
            score += 15
            
        # Business hours/description (5 points)
        if lead_data.get('description'):
            score += 5
            
        return min(score, 100)
    
    def extract_contact_info(self, text):
        """Extract contact information from text"""
        contact_info = {}
        
        # Extract phone numbers (multiple patterns)
        phone_patterns = [
            r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            r'\b([0-9]{3})[-.\s]([0-9]{3})[-.\s]([0-9]{4})\b',
            r'\(([0-9]{3})\)\s*([0-9]{3})[-.\s]([0-9]{4})\b'
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Format as (XXX) XXX-XXXX
                phone_parts = matches[0]
                if len(phone_parts) == 3:
                    contact_info['phone'] = f"({phone_parts[0]}) {phone_parts[1]}-{phone_parts[2]}"
                    break
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            # Filter out common non-business emails
            business_emails = [email for email in emails if not any(domain in email.lower() for domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'])]
            if business_emails:
                contact_info['email'] = business_emails[0]
            elif emails:
                contact_info['email'] = emails[0]
        
        # Extract addresses (basic pattern)
        address_pattern = r'\b\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl)\b[^.]*(?:\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b)?'
        addresses = re.findall(address_pattern, text)
        if addresses:
            contact_info['address'] = addresses[0]
        
        return contact_info
    
    def scrape_google_business_results(self, industry, location, limit=20):
        """Scrape Google search results for local businesses"""
        leads = []
        
        try:
            # Build search query for local businesses
            keywords = self.industry_keywords.get(industry, [industry])
            
            for keyword in keywords[:2]:  # Use top 2 keywords to avoid over-searching
                query = f"{keyword} {location}" if location else keyword
                search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={min(limit, 20)}"
                
                # Add delay to avoid rate limiting
                time.sleep(random.uniform(2, 4))
                
                response = self.session.get(search_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for business listings in search results
                business_divs = soup.find_all('div', class_='g')
                
                for div in business_divs:
                    try:
                        # Extract business name from title
                        title_elem = div.find('h3')
                        if not title_elem:
                            continue
                        
                        business_name = title_elem.get_text().strip()
                        
                        # Skip non-business results
                        if any(skip in business_name.lower() for skip in ['wikipedia', 'yelp', 'yellowpages', 'google', 'facebook']):
                            continue
                        
                        # Get business website
                        link_elem = div.find('a')
                        website = link_elem.get('href', '') if link_elem else ''
                        if website.startswith('/url?q='):
                            website = website.split('q=')[1].split('&')[0]
                        
                        # Extract snippet text for contact info
                        snippet_elem = div.find('span', class_=['st', 'VwiC3b'])
                        snippet_text = snippet_elem.get_text() if snippet_elem else ''
                        
                        # Extract contact information from snippet
                        contact_info = self.extract_contact_info(snippet_text)
                        
                        # Try to get more details from the business website
                        if website and website.startswith('http'):
                            enriched_data = self.scrape_business_website(website)
                            contact_info.update(enriched_data)
                        
                        # Create lead data
                        lead_data = {
                            'company_name': business_name,
                            'website': website,
                            'industry': industry.replace('_', ' ').title(),
                            'location': location,
                            'description': snippet_text[:500],
                            'source': 'Google Search',
                            **contact_info
                        }
                        
                        lead_data['quality_score'] = self.calculate_quality_score(lead_data)
                        
                        # Only add if we have some contact information
                        if lead_data.get('phone') or lead_data.get('email'):
                            leads.append(lead_data)
                        
                        if len(leads) >= limit:
                            break
                    
                    except Exception as e:
                        logger.warning(f"Error processing search result: {e}")
                        continue
                
                if len(leads) >= limit:
                    break
            
            return leads[:limit]
            
        except Exception as e:
            logger.error(f"Error scraping Google results: {e}")
            return []
    
    def scrape_business_website(self, website_url):
        """Extract additional contact information from business website"""
        contact_data = {}
        
        try:
            response = self.session.get(website_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            
            # Extract contact information
            contact_info = self.extract_contact_info(page_text)
            contact_data.update(contact_info)
            
            # Look for business hours
            hours_patterns = [
                r'(?i)(?:hours?|open|closed)[\s:]*(?:mon|tue|wed|thu|fri|sat|sun)[\s\w:.-]*(?:\d{1,2}[:]\d{2})',
                r'(?i)(?:\d{1,2}[:]\d{2}\s*(?:am|pm)?\s*[-to]+\s*\d{1,2}[:]\d{2}\s*(?:am|pm)?)'
            ]
            
            for pattern in hours_patterns:
                hours_match = re.search(pattern, page_text)
                if hours_match:
                    contact_data['business_hours'] = hours_match.group(0)[:100]
                    break
            
            # Look for services/specialties
            services_keywords = ['services', 'specialties', 'we offer', 'our services']
            for keyword in services_keywords:
                if keyword in page_text.lower():
                    # Extract text around the keyword
                    start_idx = page_text.lower().find(keyword)
                    services_text = page_text[start_idx:start_idx+200]
                    if len(services_text) > 50:
                        contact_data['services'] = services_text.strip()
                        break
        
        except Exception as e:
            logger.warning(f"Error scraping website {website_url}: {e}")
        
        return contact_data
    
    def scrape_yellowpages(self, industry, location, limit=10):
        """Scrape Yellow Pages for business listings"""
        leads = []
        
        try:
            # Map industries to Yellow Pages categories
            yp_categories = {
                'hvac': 'heating-air-conditioning',
                'plumbing': 'plumbers',
                'legal': 'attorneys',
                'dental': 'dentists',
                'medical': 'physicians-surgeons',
                'real_estate': 'real-estate-agents',
                'auto': 'automobile-dealers'
            }
            
            category = yp_categories.get(industry, industry.replace('_', '-'))
            location_param = location.replace(' ', '+') if location else 'nationwide'
            
            url = f"https://www.yellowpages.com/search?search_terms={category}&geo_location_terms={location_param}"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find business listings
            listings = soup.find_all('div', class_='result')
            
            for listing in listings[:limit]:
                try:
                    # Extract business name
                    name_elem = listing.find('a', class_='business-name')
                    if not name_elem:
                        continue
                    
                    business_name = name_elem.get_text().strip()
                    
                    # Extract phone number
                    phone_elem = listing.find('div', class_='phones')
                    phone = phone_elem.get_text().strip() if phone_elem else None
                    
                    # Extract address
                    address_elem = listing.find('div', class_='street-address')
                    address = address_elem.get_text().strip() if address_elem else None
                    
                    # Extract website
                    website_elem = listing.find('a', class_='track-visit-website')
                    website = website_elem.get('href') if website_elem else None
                    
                    lead_data = {
                        'company_name': business_name,
                        'phone': phone,
                        'location': address or location,
                        'website': website,
                        'industry': industry.replace('_', ' ').title(),
                        'source': 'Yellow Pages'
                    }
                    
                    lead_data['quality_score'] = self.calculate_quality_score(lead_data)
                    
                    if lead_data.get('phone'):  # Only add if we have a phone number
                        leads.append(lead_data)
                
                except Exception as e:
                    logger.warning(f"Error processing Yellow Pages listing: {e}")
                    continue
            
            return leads
            
        except Exception as e:
            logger.error(f"Error scraping Yellow Pages: {e}")
            return []

class LeadScrapingEngine:
    """Main engine for coordinating real lead scraping"""
    
    def __init__(self):
        self.scraper = RealLeadScraper()
    
    def scrape_leads(self, industry, location=None, company_size=None, sources=['google'], limit=50):
        """Scrape real leads from multiple sources"""
        
        # Create scraping session
        session = ScrapingSession(
            session_name=f"{industry.title()} leads - {location or 'All Locations'} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
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
        
        try:
            # Scrape from each source
            for source in sources:
                logger.info(f"Scraping {source} for {industry} leads in {location or 'all locations'}")
                
                source_leads = []
                leads_per_source = limit // len(sources)
                
                if source == 'google':
                    source_leads = self.scraper.scrape_google_business_results(
                        industry, location, leads_per_source
                    )
                elif source == 'yellowpages':
                    source_leads = self.scraper.scrape_yellowpages(
                        industry, location, leads_per_source
                    )
                
                # Add leads to database, avoiding duplicates
                for lead_data in source_leads:
                    # Check for existing lead by company name and location
                    existing_lead = Lead.query.filter_by(
                        company_name=lead_data['company_name']
                    ).first()
                    
                    if not existing_lead:
                        lead = Lead(**lead_data)
                        db.session.add(lead)
                        all_leads.append(lead_data)
                        logger.info(f"Added new lead: {lead_data['company_name']}")
                
                db.session.commit()
                
                # Add delay between sources
                time.sleep(random.uniform(3, 6))
            
            # Update session with results
            session.leads_found = len(all_leads)
            session.leads_processed = len(all_leads)
            session.success_rate = 100.0 if len(all_leads) > 0 else 0.0
            session.status = 'completed'
            session.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Scraping session completed. Found {len(all_leads)} new leads.")
            
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