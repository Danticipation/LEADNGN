from app import db
from datetime import datetime
from sqlalchemy import JSON
import json

class Lead(db.Model):
    """Model to store scraped leads"""
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False, index=True)
    contact_name = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    industry = db.Column(db.String(100), nullable=True, index=True)
    company_size = db.Column(db.String(50), nullable=True)  # Small, Medium, Large, Enterprise
    location = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    # Lead scoring and quality
    quality_score = db.Column(db.Integer, default=0)  # 0-100 scale
    lead_status = db.Column(db.String(50), default='new')  # new, contacted, qualified, converted, rejected
    source = db.Column(db.String(100), nullable=True)  # where the lead was scraped from
    
    # Additional data
    description = db.Column(db.Text, nullable=True)
    social_media = db.Column(db.Text, nullable=True)  # JSON string for social links
    revenue_estimate = db.Column(db.String(50), nullable=True)
    employee_count = db.Column(db.Integer, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contacted = db.Column(db.DateTime, nullable=True)
    
    # Tags and notes
    tags = db.Column(db.Text, default='[]')  # JSON array of tags
    notes = db.Column(db.Text, nullable=True)
    ai_analysis = db.Column(db.Text, nullable=True)  # Store AI analysis as JSON string
    
    # Data quality and validation
    last_validated = db.Column(db.DateTime, nullable=True)
    validation_score = db.Column(db.Integer, nullable=True)  # 0-100 validation score
    
    def __repr__(self):
        return f'<Lead {self.company_name}>'
    
    def get_tags(self):
        """Return tags as a list"""
        try:
            return json.loads(self.tags) if self.tags else []
        except:
            return []
    
    def set_tags(self, tags_list):
        """Set tags from a list"""
        self.tags = json.dumps(tags_list)
    
    def get_social_media(self):
        """Return social media links as a dictionary"""
        try:
            return json.loads(self.social_media) if self.social_media else {}
        except:
            return {}
    
    def set_social_media(self, social_dict):
        """Set social media from a dictionary"""
        self.social_media = json.dumps(social_dict)

class ScrapingSession(db.Model):
    """Model to track scraping sessions"""
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(255), nullable=False)
    target_industry = db.Column(db.String(100), nullable=True)
    target_location = db.Column(db.String(255), nullable=True)
    source_platform = db.Column(db.String(100), nullable=False)  # LinkedIn, Google, etc.
    
    # Session stats
    leads_found = db.Column(db.Integer, default=0)
    leads_processed = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    
    # Status and timing
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Configuration
    search_criteria = db.Column(db.Text, nullable=True)  # JSON string with search parameters
    
    def __repr__(self):
        return f'<ScrapingSession {self.session_name}>'
    
    def get_search_criteria(self):
        """Return search criteria as a dictionary"""
        try:
            return json.loads(self.search_criteria) if self.search_criteria else {}
        except:
            return {}
    
    def set_search_criteria(self, criteria_dict):
        """Set search criteria from a dictionary"""
        self.search_criteria = json.dumps(criteria_dict)

class LeadInteraction(db.Model):
    """Model to track interactions with leads"""
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    interaction_type = db.Column(db.String(50), nullable=False)  # email, call, meeting, note
    subject = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=True)
    outcome = db.Column(db.String(100), nullable=True)  # positive, negative, neutral, follow_up
    
    # Timing
    interaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_date = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    lead = db.relationship('Lead', backref=db.backref('interactions', lazy=True))
    
    def __repr__(self):
        return f'<LeadInteraction {self.interaction_type} for Lead {self.lead_id}>'

class LeadList(db.Model):
    """Model for organizing leads into lists/campaigns"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    list_type = db.Column(db.String(50), default='general')  # general, campaign, target_industry
    
    # Stats
    total_leads = db.Column(db.Integer, default=0)
    contacted_leads = db.Column(db.Integer, default=0)
    converted_leads = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<LeadList {self.name}>'

class LeadListMembership(db.Model):
    """Many-to-many relationship between leads and lists"""
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    list_id = db.Column(db.Integer, db.ForeignKey('lead_list.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    lead = db.relationship('Lead', backref=db.backref('list_memberships', lazy=True))
    lead_list = db.relationship('LeadList', backref=db.backref('memberships', lazy=True))
    
    def __repr__(self):
        return f'<LeadListMembership Lead {self.lead_id} in List {self.list_id}>'