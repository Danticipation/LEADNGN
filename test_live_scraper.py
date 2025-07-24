#!/usr/bin/env python3
"""
Test script for live lead scraper
Tests the real web scraping functionality
"""

import sys
import logging
from live_lead_scraper import LiveLeadScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_scraper():
    """Test the live lead scraper"""
    scraper = LiveLeadScraper()
    
    try:
        logger.info("Testing live lead scraper...")
        
        # Test with HVAC in Austin, TX
        industry = "HVAC"
        location = "Austin, TX"
        max_leads = 5
        
        logger.info(f"Searching for {industry} businesses in {location}")
        leads = scraper.generate_live_leads(industry, location, max_leads)
        
        logger.info(f"Found {len(leads)} leads:")
        
        for i, lead in enumerate(leads, 1):
            print(f"\nLead {i}:")
            print(f"  Company: {lead.get('company_name', 'N/A')}")
            print(f"  Email: {lead.get('email', 'N/A')}")
            print(f"  Phone: {lead.get('phone', 'N/A')}")
            print(f"  Website: {lead.get('website', 'N/A')}")
            print(f"  Quality Score: {lead.get('quality_score', 0)}")
            print(f"  Source: {lead.get('source', 'N/A')}")
        
        if not leads:
            logger.warning("No leads found. This could be due to:")
            logger.warning("1. Network connectivity issues")
            logger.warning("2. Website blocking/rate limiting")
            logger.warning("3. Changes in website structure")
            logger.warning("4. Chrome/Selenium setup issues")
        
        return leads
        
    except Exception as e:
        logger.error(f"Scraper test failed: {e}")
        return []
    
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    test_scraper()