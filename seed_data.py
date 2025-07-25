"""
Seed script to populate LeadNgN with sample lead data
"""
import random
from datetime import datetime, timedelta
from app import app, db
from models import Lead, ScrapingSession

def create_sample_leads():
    """Create sample leads for demonstration"""
    
    # Sample companies data
    companies = [
        {"name": "TechFlow Solutions", "industry": "Software Development", "size": "Medium", "location": "San Francisco, CA"},
        {"name": "DataMine Analytics", "industry": "Data Analytics", "size": "Small", "location": "Austin, TX"},
        {"name": "CloudFirst Systems", "industry": "Cloud Services", "size": "Large", "location": "Seattle, WA"},
        {"name": "FinTech Innovations", "industry": "Financial Technology", "size": "Medium", "location": "New York, NY"},
        {"name": "HealthCore Digital", "industry": "Healthcare Technology", "size": "Enterprise", "location": "Boston, MA"},
        {"name": "EcoGreen Energy", "industry": "Renewable Energy", "size": "Large", "location": "Denver, CO"},
        {"name": "RetailNext Platform", "industry": "E-commerce", "size": "Medium", "location": "Los Angeles, CA"},
        {"name": "EduTech Pioneers", "industry": "Education Technology", "size": "Small", "location": "Chicago, IL"},
        {"name": "ManufactureMax", "industry": "Manufacturing", "size": "Enterprise", "location": "Detroit, MI"},
        {"name": "LogisticsPro", "industry": "Logistics", "size": "Large", "location": "Atlanta, GA"},
        {"name": "SecureNet Solutions", "industry": "Cybersecurity", "size": "Medium", "location": "Washington, DC"},
        {"name": "AgriTech Dynamics", "industry": "Agriculture Technology", "size": "Small", "location": "Des Moines, IA"},
        {"name": "PropTech Ventures", "industry": "Real Estate Technology", "size": "Medium", "location": "Miami, FL"},
        {"name": "FoodTech Labs", "industry": "Food Technology", "size": "Small", "location": "Portland, OR"},
        {"name": "TransportNext", "industry": "Transportation", "size": "Large", "location": "Phoenix, AZ"}
    ]
    
    # Sample contact names
    contacts = [
        "Sarah Johnson", "Michael Chen", "Emily Rodriguez", "David Kim", "Lisa Wang",
        "James Wilson", "Maria Garcia", "Robert Taylor", "Jessica Brown", "Alex Thompson",
        "Amanda Davis", "Christopher Lee", "Nicole Martinez", "Kevin Anderson", "Rachel Smith"
    ]
    
    # Lead statuses with weights
    statuses = [
        ("new", 0.4),
        ("contacted", 0.25),
        ("qualified", 0.2),
        ("converted", 0.1),
        ("rejected", 0.05)
    ]
    
    leads_created = 0
    
    for i, company in enumerate(companies):
        # Create 1-3 leads per company
        num_leads = random.randint(1, 3)
        
        for j in range(num_leads):
            contact = random.choice(contacts)
            
            # Generate email from contact name and company
            email_name = contact.lower().replace(" ", ".")
            domain = company["name"].lower().replace(" ", "").replace(",", "")[:10] + ".com"
            email = f"{email_name}@{domain}"
            
            # Weighted random status selection
            status_choices, weights = zip(*statuses)
            status = random.choices(status_choices, weights=weights)[0]
            
            # Quality score based on company size and industry
            base_score = 50
            if company["size"] == "Enterprise":
                base_score += 30
            elif company["size"] == "Large":
                base_score += 20
            elif company["size"] == "Medium":
                base_score += 10
            
            # Industry modifiers
            high_value_industries = ["Financial Technology", "Healthcare Technology", "Cybersecurity"]
            if company["industry"] in high_value_industries:
                base_score += 15
            
            quality_score = min(100, max(0, base_score + random.randint(-20, 20)))
            
            # Create lead
            lead = Lead()
            lead.company_name = company["name"]
            lead.contact_name = contact
            lead.email = email
            lead.phone = f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"
            lead.website = f"https://www.{domain}"
            lead.industry = company["industry"]
            lead.company_size = company["size"]
            lead.location = company["location"]
            lead.quality_score = quality_score
            lead.lead_status = status
            lead.source = "LinkedIn Scraping"
            
            # Random description
            descriptions = [
                f"Growing {company['industry'].lower()} company looking to expand operations",
                f"Established {company['size'].lower()} business in the {company['industry'].lower()} sector",
                f"Innovative company specializing in {company['industry'].lower()} solutions",
                f"Market leader in {company['industry'].lower()} with strong growth potential"
            ]
            lead.description = random.choice(descriptions)
            
            # Employee count based on size
            size_ranges = {
                "Small": (10, 50),
                "Medium": (51, 200),
                "Large": (201, 1000),
                "Enterprise": (1001, 5000)
            }
            min_emp, max_emp = size_ranges.get(company["size"], (10, 50))
            lead.employee_count = random.randint(min_emp, max_emp)
            
            # Random creation date within last 30 days
            days_ago = random.randint(0, 30)
            lead.created_at = datetime.utcnow() - timedelta(days=days_ago)
            
            # Set tags
            tags = []
            if quality_score >= 80:
                tags.append("high-priority")
            if company["size"] in ["Large", "Enterprise"]:
                tags.append("enterprise")
            if status == "qualified":
                tags.append("hot-lead")
            
            lead.set_tags(tags)
            
            db.session.add(lead)
            leads_created += 1
    
    # Create sample scraping sessions
    sessions_data = [
        {
            "name": "LinkedIn Tech Companies Q4",
            "industry": "Technology",
            "location": "San Francisco Bay Area",
            "platform": "LinkedIn",
            "leads_found": 45,
            "status": "completed"
        },
        {
            "name": "Healthcare Startups Boston",
            "industry": "Healthcare Technology",
            "location": "Boston, MA",
            "platform": "AngelList",
            "leads_found": 23,
            "status": "completed"
        },
        {
            "name": "FinTech Companies NYC",
            "industry": "Financial Technology",
            "location": "New York, NY",
            "platform": "Crunchbase",
            "leads_found": 31,
            "status": "running"
        }
    ]
    
    for session_data in sessions_data:
        session = ScrapingSession()
        session.session_name = session_data["name"]
        session.target_industry = session_data["industry"]
        session.target_location = session_data["location"]
        session.source_platform = session_data["platform"]
        session.leads_found = session_data["leads_found"]
        session.leads_processed = session_data["leads_found"]
        session.status = session_data["status"]
        session.success_rate = random.uniform(0.7, 0.95)
        
        if session_data["status"] == "completed":
            session.completed_at = datetime.utcnow() - timedelta(days=random.randint(1, 7))
        
        db.session.add(session)
    
    db.session.commit()
    print(f"Created {leads_created} sample leads and {len(sessions_data)} scraping sessions")

if __name__ == "__main__":
    with app.app_context():
        # Clear existing data
        Lead.query.delete()
        ScrapingSession.query.delete()
        
        # Create sample data
        create_sample_leads()
        
        print("Sample data created successfully!")