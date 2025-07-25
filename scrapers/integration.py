"""
Enhanced Scraping Integration for LeadNGN
Integrates enhanced scraping with existing system
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .enhanced_scraper import enhanced_scraper
from .data_enrichment import data_enricher

logger = logging.getLogger(__name__)

class EnhancedScrapingEngine:
    """Integration layer for enhanced scraping capabilities"""
    
    def __init__(self):
        self.scraper = enhanced_scraper
        self.enricher = data_enricher
    
    def generate_enhanced_leads(self, industry: str, location: str, max_leads: int = 20, 
                               enable_enrichment: bool = True) -> Dict:
        """Generate leads with enhanced scraping and optional data enrichment"""
        
        result = {
            'success': False,
            'leads': [],
            'stats': {},
            'enrichment_enabled': enable_enrichment,
            'generation_timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            logger.info(f"Starting enhanced lead generation: {industry} in {location}")
            
            # Primary scraping with enhanced engine
            scraping_result = self.scraper.enhanced_lead_generation(
                industry=industry,
                location=location,
                max_leads=max_leads,
                sources=['google', 'directories']
            )
            
            if not scraping_result['success']:
                result['error'] = scraping_result.get('error', 'Scraping failed')
                return result
            
            leads = scraping_result['leads']
            result['stats'] = scraping_result['stats']
            
            # Data enrichment phase
            if enable_enrichment and leads:
                logger.info(f"Starting data enrichment for {len(leads)} leads")
                enriched_leads = []
                
                for lead in leads:
                    try:
                        # Validate and enrich each lead
                        validation_result = self.enricher.validate_business_legitimacy(lead)
                        
                        # Add enrichment data to lead
                        lead['validation'] = validation_result
                        lead['enrichment_score'] = validation_result.get('legitimacy_score', 0)
                        
                        # Update quality score based on validation
                        original_score = lead.get('quality_score', 70)
                        enrichment_bonus = min(20, validation_result.get('legitimacy_score', 0) // 5)
                        lead['quality_score'] = min(100, original_score + enrichment_bonus)
                        
                        enriched_leads.append(lead)
                        
                    except Exception as e:
                        logger.warning(f"Enrichment failed for {lead.get('company_name', 'unknown')}: {e}")
                        # Keep original lead without enrichment
                        lead['validation'] = {'error': str(e)}
                        enriched_leads.append(lead)
                
                result['leads'] = enriched_leads
                result['stats']['enrichment_applied'] = True
                result['stats']['enriched_count'] = len([l for l in enriched_leads if 'validation' in l and 'error' not in l['validation']])
            else:
                result['leads'] = leads
                result['stats']['enrichment_applied'] = False
            
            # Final quality filtering
            high_quality_leads = [
                lead for lead in result['leads'] 
                if lead.get('quality_score', 0) >= 75
            ]
            
            # Update statistics
            result['stats'].update({
                'final_lead_count': len(result['leads']),
                'high_quality_count': len(high_quality_leads),
                'average_quality_score': sum(l.get('quality_score', 0) for l in result['leads']) / len(result['leads']) if result['leads'] else 0
            })
            
            result['success'] = True
            result['leads'] = high_quality_leads  # Return only high-quality leads
            
            logger.info(f"Enhanced lead generation complete: {len(high_quality_leads)} high-quality leads")
            
        except Exception as e:
            logger.error(f"Enhanced scraping engine error: {e}")
            result['error'] = str(e)
        
        return result
    
    def validate_existing_leads(self, leads: List[Dict]) -> List[Dict]:
        """Validate and enrich existing leads in database"""
        validated_leads = []
        
        for lead in leads:
            try:
                # Run validation
                validation = self.enricher.validate_business_legitimacy(lead)
                
                # Update lead with validation data
                lead['last_validated'] = datetime.utcnow().isoformat()
                lead['validation_score'] = validation.get('legitimacy_score', 0)
                lead['verification_status'] = validation.get('verification_status', 'pending')
                
                validated_leads.append(lead)
                
            except Exception as e:
                logger.warning(f"Validation failed for {lead.get('company_name', 'unknown')}: {e}")
                lead['validation_error'] = str(e)
                validated_leads.append(lead)
        
        return validated_leads
    
    def get_scraping_capabilities(self) -> Dict:
        """Get information about enhanced scraping capabilities"""
        return {
            'enhanced_features': [
                'Multi-source data collection',
                'Advanced quality scoring',
                'Business legitimacy validation',
                'Email deliverability checking',
                'Website quality analysis',
                'Contact information verification',
                'Industry-specific targeting',
                'Duplicate prevention',
                'Real-time data enrichment'
            ],
            'supported_industries': list(self.scraper.industry_keywords.keys()),
            'data_sources': [
                'Google Business Listings',
                'Business Directories',
                'Yellow Pages',
                'Industry-specific databases'
            ],
            'validation_capabilities': [
                'Email MX record validation',
                'Phone number formatting',
                'Website accessibility',
                'SSL certificate checking',
                'Business legitimacy scoring'
            ],
            'quality_factors': [
                'Company name professionalism',
                'Business age and establishment',
                'Contact information completeness',
                'Website quality and presence',
                'Industry specialization',
                'Geographic relevance'
            ]
        }

# Global instance
enhanced_engine = EnhancedScrapingEngine()