"""
Auto-Revalidation Workflow System for LeadNGN
Keeps lead data fresh with scheduled re-scoring and re-insight passes
"""

import os
import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import and_, or_
from models import Lead, ScrapingSession, db
from ai_provider_manager import ai_provider
from email_deliverability import EmailDeliverabilityChecker
from phone_integration import phone_manager

logger = logging.getLogger(__name__)

class LeadRevalidationEngine:
    """Automated lead data revalidation and refresh system"""
    
    def __init__(self):
        self.email_checker = EmailDeliverabilityChecker()
        self.revalidation_intervals = {
            'high_quality': 30,  # Days between revalidation for quality 80+
            'medium_quality': 21,  # Days for quality 60-79
            'low_quality': 14,   # Days for quality <60
            'contacted': 7,      # Days for contacted leads
            'new': 3            # Days for new leads
        }
        self.max_concurrent_jobs = 5
        self.running_jobs = 0
    
    def schedule_revalidation_jobs(self):
        """Set up scheduled revalidation jobs"""
        # Daily revalidation check
        schedule.every().day.at("02:00").do(self.run_daily_revalidation)
        
        # Weekly deep revalidation
        schedule.every().sunday.at("01:00").do(self.run_weekly_deep_revalidation)
        
        # Monthly comprehensive review
        schedule.every().month.do(self.run_monthly_comprehensive_review)
        
        logger.info("Revalidation jobs scheduled")
    
    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def start_background_scheduler(self):
        """Start the revalidation scheduler in background"""
        scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Background revalidation scheduler started")
    
    def run_daily_revalidation(self):
        """Daily revalidation of leads based on staleness"""
        logger.info("Starting daily lead revalidation")
        
        try:
            stale_leads = self.identify_stale_leads()
            
            for priority_group, leads in stale_leads.items():
                if leads and self.running_jobs < self.max_concurrent_jobs:
                    self.process_lead_batch(leads, f"daily_{priority_group}")
            
            logger.info(f"Daily revalidation completed. Processed {sum(len(leads) for leads in stale_leads.values())} leads")
            
        except Exception as e:
            logger.error(f"Daily revalidation failed: {e}")
    
    def identify_stale_leads(self) -> Dict[str, List[Any]]:
        """Identify leads that need revalidation based on age and status"""
        cutoff_dates = {}
        now = datetime.utcnow()
        
        for category, days in self.revalidation_intervals.items():
            cutoff_dates[category] = now - timedelta(days=days)
        
        stale_leads = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': []
        }
        
        # High priority: Contacted leads or high-quality leads
        high_priority = Lead.query.filter(
            and_(
                or_(
                    Lead.lead_status == 'contacted',
                    Lead.quality_score >= 80
                ),
                Lead.updated_at < cutoff_dates['contacted']
            )
        ).limit(20).all()
        
        # Medium priority: Medium quality leads
        medium_priority = Lead.query.filter(
            and_(
                Lead.quality_score.between(60, 79),
                Lead.updated_at < cutoff_dates['medium_quality']
            )
        ).limit(15).all()
        
        # Low priority: Low quality or old leads
        low_priority = Lead.query.filter(
            and_(
                Lead.quality_score < 60,
                Lead.updated_at < cutoff_dates['low_quality']
            )
        ).limit(10).all()
        
        stale_leads['high_priority'] = high_priority
        stale_leads['medium_priority'] = medium_priority
        stale_leads['low_priority'] = low_priority
        
        return stale_leads
    
    def process_lead_batch(self, leads: List[Any], batch_name: str):
        """Process a batch of leads for revalidation"""
        if self.running_jobs >= self.max_concurrent_jobs:
            logger.warning(f"Max concurrent jobs reached, skipping batch {batch_name}")
            return
        
        self.running_jobs += 1
        logger.info(f"Starting revalidation batch: {batch_name} ({len(leads)} leads)")
        
        try:
            for lead in leads:
                self.revalidate_single_lead(lead)
                time.sleep(1)  # Rate limiting
            
            logger.info(f"Completed revalidation batch: {batch_name}")
            
        except Exception as e:
            logger.error(f"Batch {batch_name} failed: {e}")
        finally:
            self.running_jobs -= 1
    
    def revalidate_single_lead(self, lead: Any) -> Dict[str, Any]:
        """Revalidate a single lead's data and scoring"""
        revalidation_result = {
            "lead_id": lead.id,
            "company_name": lead.company_name,
            "previous_quality_score": lead.quality_score,
            "updates_made": [],
            "validation_errors": []
        }
        
        try:
            # Email validation update
            if lead.email:
                email_validation = self.email_checker.validate_email_comprehensive(lead.email)
                if email_validation["deliverability_score"] != getattr(lead, 'email_deliverability_score', 0):
                    lead.email_deliverability_score = email_validation["deliverability_score"]
                    revalidation_result["updates_made"].append("email_deliverability_updated")
            
            # Phone validation update
            if lead.phone:
                phone_validation = phone_manager.validate_phone_number(lead.phone)
                if phone_validation["is_valid"] and phone_validation["formatted"] != lead.phone:
                    lead.phone = phone_validation["formatted"]
                    revalidation_result["updates_made"].append("phone_formatted")
            
            # Website accessibility check
            if lead.website:
                website_status = self.check_website_status(lead.website)
                if hasattr(lead, 'website_status') and website_status != lead.website_status:
                    lead.website_status = website_status
                    revalidation_result["updates_made"].append("website_status_updated")
            
            # Recalculate quality score
            new_quality_score = self.recalculate_quality_score(lead)
            if abs(new_quality_score - lead.quality_score) >= 5:  # Significant change
                lead.quality_score = new_quality_score
                revalidation_result["updates_made"].append("quality_score_updated")
            
            # Update timestamps
            lead.updated_at = datetime.utcnow()
            
            # Save changes
            if revalidation_result["updates_made"]:
                db.session.commit()
                logger.info(f"Revalidated lead {lead.id}: {', '.join(revalidation_result['updates_made'])}")
            
            revalidation_result["new_quality_score"] = lead.quality_score
            revalidation_result["status"] = "success"
            
        except Exception as e:
            logger.error(f"Revalidation failed for lead {lead.id}: {e}")
            revalidation_result["validation_errors"].append(str(e))
            revalidation_result["status"] = "error"
            db.session.rollback()
        
        return revalidation_result
    
    def check_website_status(self, website_url: str) -> str:
        """Check if website is still accessible"""
        try:
            import requests
            
            if not website_url.startswith(('http://', 'https://')):
                website_url = 'https://' + website_url
            
            response = requests.head(website_url, timeout=10, allow_redirects=True)
            
            if response.status_code < 400:
                return "active"
            elif response.status_code == 404:
                return "not_found"
            else:
                return f"error_{response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return "unreachable"
        except requests.exceptions.Timeout:
            return "timeout"
        except Exception:
            return "unknown"
    
    def recalculate_quality_score(self, lead: Any) -> int:
        """Recalculate lead quality score with current data"""
        score = 0
        
        # Contact information completeness (40 points max)
        if lead.email:
            score += 15
            if hasattr(lead, 'email_deliverability_score'):
                score += min(15, lead.email_deliverability_score // 4)
        
        if lead.phone:
            score += 10
        
        if lead.contact_name:
            score += 10
        
        # Company information (30 points max)
        if lead.website:
            score += 10
            if hasattr(lead, 'website_status') and lead.website_status == "active":
                score += 10
        
        if lead.industry:
            score += 5
        
        if lead.location:
            score += 5
        
        # Business characteristics (20 points max)
        if lead.company_size:
            score += 5
        
        if lead.revenue_estimate:
            score += 5
        
        if lead.employee_count and lead.employee_count > 0:
            score += 5
        
        if lead.description:
            score += 5
        
        # Data freshness (10 points max)
        if lead.updated_at:
            days_old = (datetime.utcnow() - lead.updated_at).days
            freshness_score = max(0, 10 - (days_old // 7))  # Lose 1 point per week
            score += freshness_score
        
        return min(100, max(0, score))
    
    def run_weekly_deep_revalidation(self):
        """Weekly deep revalidation including AI re-analysis"""
        logger.info("Starting weekly deep revalidation")
        
        try:
            # Get high-priority leads for AI re-analysis
            high_value_leads = Lead.query.filter(
                and_(
                    Lead.quality_score >= 70,
                    Lead.lead_status.in_(['new', 'contacted']),
                    Lead.updated_at < datetime.utcnow() - timedelta(days=7)
                )
            ).limit(10).all()
            
            for lead in high_value_leads:
                self.deep_revalidate_lead(lead)
                time.sleep(5)  # Longer delay for AI calls
            
            logger.info(f"Weekly deep revalidation completed for {len(high_value_leads)} leads")
            
        except Exception as e:
            logger.error(f"Weekly deep revalidation failed: {e}")
    
    def deep_revalidate_lead(self, lead: Any):
        """Perform deep revalidation including AI re-analysis"""
        try:
            # Re-generate AI insights if lead is important enough
            if lead.quality_score >= 80:
                insights = ai_provider.generate_analysis(
                    self.build_revalidation_prompt(lead), 
                    "analysis"
                )
                
                # Store updated insights
                if hasattr(lead, 'ai_insights'):
                    lead.ai_insights = str(insights)
                
                logger.info(f"AI insights updated for lead {lead.id}")
            
            # Perform standard revalidation
            self.revalidate_single_lead(lead)
            
        except Exception as e:
            logger.error(f"Deep revalidation failed for lead {lead.id}: {e}")
    
    def build_revalidation_prompt(self, lead: Any) -> str:
        """Build prompt for AI re-analysis during revalidation"""
        return f"""
Re-analyze this business lead for current market conditions and opportunities:

COMPANY: {lead.company_name}
INDUSTRY: {lead.industry or 'Unknown'}
LOCATION: {lead.location or 'Unknown'}
CONTACT: {lead.contact_name or 'Unknown'}
WEBSITE: {lead.website or 'None'}
LAST ANALYSIS: {lead.updated_at.strftime('%Y-%m-%d') if lead.updated_at else 'Never'}

Focus on:
1. Current industry trends affecting this business
2. Updated pain points and opportunities
3. Revised engagement strategy
4. Current market timing for outreach

Provide updated analysis in JSON format with business_intelligence, engagement_strategy, and lead_scoring sections.
"""
    
    def run_monthly_comprehensive_review(self):
        """Monthly comprehensive lead database review"""
        logger.info("Starting monthly comprehensive review")
        
        try:
            # Archive very old, low-quality leads
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            old_leads = Lead.query.filter(
                and_(
                    Lead.quality_score < 40,
                    Lead.lead_status == 'new',
                    Lead.updated_at < cutoff_date
                )
            ).all()
            
            archived_count = 0
            for lead in old_leads:
                lead.lead_status = 'archived'
                archived_count += 1
            
            if archived_count > 0:
                db.session.commit()
                logger.info(f"Archived {archived_count} old, low-quality leads")
            
            # Generate quality distribution report
            quality_stats = self.generate_quality_statistics()
            logger.info(f"Quality distribution: {quality_stats}")
            
        except Exception as e:
            logger.error(f"Monthly comprehensive review failed: {e}")
    
    def generate_quality_statistics(self) -> Dict[str, Any]:
        """Generate lead quality distribution statistics"""
        total_leads = Lead.query.count()
        
        if total_leads == 0:
            return {"total_leads": 0}
        
        high_quality = Lead.query.filter(Lead.quality_score >= 80).count()
        medium_quality = Lead.query.filter(Lead.quality_score.between(60, 79)).count()
        low_quality = Lead.query.filter(Lead.quality_score < 60).count()
        
        return {
            "total_leads": total_leads,
            "high_quality": high_quality,
            "medium_quality": medium_quality,
            "low_quality": low_quality,
            "high_quality_percent": round((high_quality / total_leads) * 100, 1),
            "medium_quality_percent": round((medium_quality / total_leads) * 100, 1),
            "low_quality_percent": round((low_quality / total_leads) * 100, 1)
        }
    
    def force_revalidate_lead(self, lead_id: int) -> Dict[str, Any]:
        """Force immediate revalidation of a specific lead"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {"error": "Lead not found"}
            
            result = self.revalidate_single_lead(lead)
            return result
            
        except Exception as e:
            logger.error(f"Force revalidation failed for lead {lead_id}: {e}")
            return {"error": str(e)}
    
    def get_revalidation_status(self) -> Dict[str, Any]:
        """Get current revalidation system status"""
        stale_leads = self.identify_stale_leads()
        
        return {
            "running_jobs": self.running_jobs,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "stale_leads_count": {
                "high_priority": len(stale_leads['high_priority']),
                "medium_priority": len(stale_leads['medium_priority']),
                "low_priority": len(stale_leads['low_priority'])
            },
            "next_daily_run": "02:00 UTC",
            "next_weekly_run": "Sunday 01:00 UTC",
            "revalidation_intervals": self.revalidation_intervals
        }


# Global instance
revalidation_engine = LeadRevalidationEngine()