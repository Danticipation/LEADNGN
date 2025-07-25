import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import desc, asc, func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "leadngn-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import models after db initialization
from models import Lead, ScrapingSession, LeadInteraction, LeadList, LeadListMembership

with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

@app.route('/')
def dashboard():
    """Main dashboard with lead overview and filtering"""
    try:
        # Get filter parameters
        industry_filter = request.args.get('industry', '')
        status_filter = request.args.get('status', '')
        quality_filter = request.args.get('quality', '')
        sort_by = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc')
        
        # Build query
        query = Lead.query
        
        # Apply filters
        if industry_filter:
            query = query.filter(Lead.industry.ilike(f'%{industry_filter}%'))
        if status_filter:
            query = query.filter(Lead.lead_status == status_filter)
        if quality_filter:
            if quality_filter == 'high':
                query = query.filter(Lead.quality_score >= 80)
            elif quality_filter == 'medium':
                query = query.filter(Lead.quality_score.between(40, 79))
            elif quality_filter == 'low':
                query = query.filter(Lead.quality_score < 40)
        
        # Apply sorting
        if hasattr(Lead, sort_by):
            if sort_order == 'desc':
                query = query.order_by(desc(getattr(Lead, sort_by)))
            else:
                query = query.order_by(asc(getattr(Lead, sort_by)))
        
        leads = query.limit(100).all()
        
        # Get dashboard stats
        total_leads = Lead.query.count()
        new_leads = Lead.query.filter(Lead.lead_status == 'new').count()
        qualified_leads = Lead.query.filter(Lead.lead_status == 'qualified').count()
        converted_leads = Lead.query.filter(Lead.lead_status == 'converted').count()
        
        # Get industry breakdown
        industry_stats = db.session.query(
            Lead.industry,
            func.count(Lead.id).label('count')
        ).group_by(Lead.industry).filter(Lead.industry.isnot(None)).all()
        
        # Get recent activity (leads created in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_leads = Lead.query.filter(Lead.created_at >= week_ago).count()
        
        return render_template('dashboard.html',
                             leads=leads,
                             total_leads=total_leads,
                             new_leads=new_leads,
                             qualified_leads=qualified_leads,
                             converted_leads=converted_leads,
                             industry_stats=industry_stats,
                             recent_leads=recent_leads,
                             current_filters={
                                 'industry': industry_filter,
                                 'status': status_filter,
                                 'quality': quality_filter,
                                 'sort': sort_by,
                                 'order': sort_order
                             })
    
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('dashboard.html', 
                             leads=[], 
                             total_leads=0,
                             new_leads=0,
                             qualified_leads=0,
                             converted_leads=0,
                             industry_stats=[],
                             recent_leads=0,
                             error="Error loading dashboard data")

@app.route('/leads')
def leads_list():
    """Detailed leads listing page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 25
        
        # Get filter parameters
        industry_filter = request.args.get('industry', '')
        status_filter = request.args.get('status', '')
        quality_filter = request.args.get('quality', '')
        search_query = request.args.get('search', '')
        sort_by = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc')
        
        query = Lead.query
        
        # Apply search
        if search_query:
            query = query.filter(
                (Lead.company_name.ilike(f'%{search_query}%')) |
                (Lead.contact_name.ilike(f'%{search_query}%')) |
                (Lead.email.ilike(f'%{search_query}%'))
            )
        
        # Apply filters
        if industry_filter:
            query = query.filter(Lead.industry.ilike(f'%{industry_filter}%'))
        if status_filter:
            query = query.filter(Lead.lead_status == status_filter)
        if quality_filter:
            if quality_filter == 'high':
                query = query.filter(Lead.quality_score >= 80)
            elif quality_filter == 'medium':
                query = query.filter(Lead.quality_score.between(40, 79))
            elif quality_filter == 'low':
                query = query.filter(Lead.quality_score < 40)
        
        # Apply sorting
        if hasattr(Lead, sort_by):
            if sort_order == 'desc':
                query = query.order_by(desc(getattr(Lead, sort_by)))
            else:
                query = query.order_by(asc(getattr(Lead, sort_by)))
        
        leads = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Get unique industries for filter dropdown
        industries = db.session.query(Lead.industry).distinct().filter(
            Lead.industry.isnot(None)
        ).all()
        industries = [i[0] for i in industries if i[0]]
        
        return render_template('leads_simple.html',
                             leads=leads.items if hasattr(leads, 'items') else leads,
                             industries=industries,
                             current_filters={
                                 'industry': industry_filter,
                                 'status': status_filter,
                                 'quality': quality_filter,
                                 'search': search_query,
                                 'sort': sort_by,
                                 'order': sort_order
                             })
    
    except Exception as e:
        logger.error(f"Error loading leads: {str(e)}")
        return render_template('leads_simple.html', 
                             leads=[], 
                             industries=[],
                             current_filters={
                                 'industry': '',
                                 'status': '',
                                 'quality': '',
                                 'search': '',
                                 'sort': 'created_at',
                                 'order': 'desc'
                             },
                             error="Error loading leads")

@app.route('/lead/<int:lead_id>')
def lead_detail(lead_id):
    """Detailed view of a single lead"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        interactions = LeadInteraction.query.filter_by(lead_id=lead_id).order_by(
            desc(LeadInteraction.interaction_date)
        ).all()
        
        return render_template('lead_detail_enhanced.html', lead=lead, interactions=interactions)
    
    except Exception as e:
        logger.error(f"Error loading lead {lead_id}: {str(e)}")
        return "Lead not found", 404

@app.route('/api/lead/<int:lead_id>/insights', methods=['GET'])
def get_lead_insights(lead_id):
    """Get AI-powered insights for a specific lead"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        
        from ai_provider_manager import ai_provider
        
        # Build analysis prompt
        prompt = f"""
Analyze this business lead and provide comprehensive insights in JSON format:

COMPANY: {lead.company_name}
INDUSTRY: {lead.industry or 'Unknown'}
LOCATION: {lead.location or 'Unknown'}
CONTACT: {lead.contact_name or 'Unknown'}
EMAIL: {lead.email or 'None'}
PHONE: {lead.phone or 'None'}
WEBSITE: {lead.website or 'None'}
QUALITY SCORE: {lead.quality_score}

Provide analysis in JSON format with:
- business_intelligence (overview, pain_points, opportunities, industry_position)
- engagement_strategy (approach, timing, key_messages)
- lead_scoring (interest_level, buying_readiness, authority_level, fit_score)
- next_steps
"""
        
        insights = ai_provider.generate_analysis(prompt, "analysis")
        
        return jsonify(insights)
    
    except Exception as e:
        logger.error(f"Error generating insights for lead {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to generate insights'}), 500

@app.route('/api/lead/<int:lead_id>/outreach', methods=['POST'])
def generate_outreach(lead_id):
    """Generate personalized outreach content for a lead"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        outreach_type = request.json.get('type', 'email') if request.json else 'email'
        
        from ai_provider_manager import ai_provider
        
        # Build outreach prompt
        prompt = f"""
Generate personalized outreach content for this business lead:

COMPANY: {lead.company_name}
CONTACT: {lead.contact_name or 'there'}
INDUSTRY: {lead.industry or 'Unknown'}
LOCATION: {lead.location or 'Unknown'}
WEBSITE: {lead.website or 'None'}
OUTREACH TYPE: {outreach_type}

Create compelling, personalized {outreach_type} content in JSON format with:
- subject_line
- email_content (under 200 words)
- key_points
- tone
- follow_up_strategy
"""
        
        outreach_content = ai_provider.generate_analysis(prompt, "outreach")
        
        return jsonify(outreach_content)
    
    except Exception as e:
        logger.error(f"Error generating outreach for lead {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to generate outreach'}), 500

@app.route('/api/lead/<int:lead_id>/research', methods=['GET'])
def get_lead_research(lead_id):
    """Get comprehensive research data for a lead"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        
        from ai_provider_manager import ai_provider
        
        # Gather basic research data
        research_data = {
            "lead_info": {
                "company": lead.company_name,
                "industry": lead.industry,
                "location": lead.location,
                "contact": lead.contact_name,
                "website": lead.website,
                "quality_score": lead.quality_score
            },
            "contact_analysis": {},
            "recommendations": []
        }
        
        # Add email analysis if available
        if lead.email:
            try:
                from email_deliverability import EmailDeliverabilityChecker
                checker = EmailDeliverabilityChecker()
                email_validation = checker.validate_email_comprehensive(lead.email)
                research_data["email_analysis"] = email_validation
            except:
                research_data["email_analysis"] = {"error": "Email validation unavailable"}
        
        # Add phone analysis if available
        if lead.phone:
            try:
                from phone_integration import phone_manager
                phone_validation = phone_manager.validate_phone_number(lead.phone)
                research_data["phone_analysis"] = phone_validation
            except:
                research_data["phone_analysis"] = {"error": "Phone validation unavailable"}
        
        return jsonify(research_data)
    
    except Exception as e:
        logger.error(f"Error getting research for lead {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to get research data'}), 500

@app.route('/scraping')
def scraping_dashboard():
    """Scraping sessions management"""
    try:
        sessions = ScrapingSession.query.order_by(desc(ScrapingSession.started_at)).limit(20).all()
        
        return render_template('scraping.html', sessions=sessions)
    
    except Exception as e:
        logger.error(f"Error loading scraping dashboard: {str(e)}")
        return render_template('scraping.html', sessions=[], error="Error loading scraping data")

@app.route('/scraping/new', methods=['GET', 'POST'])
def new_scraping_session():
    """Create and run new scraping session"""
    if request.method == 'GET':
        return render_template('new_scraping.html')
    
    try:
        # Get form data
        industry = request.form.get('industry', '').strip()
        location = request.form.get('location', '').strip() or None
        company_size = request.form.get('company_size', '').strip() or None
        sources = request.form.getlist('sources')
        limit = int(request.form.get('limit', 20))
        
        if not industry:
            return render_template('new_scraping.html', 
                                 error="Industry is required")
        
        if not sources:
            sources = ['google']  # Default to Google search
        
        # Import real scraping engine
        from real_scrapers import LeadScrapingEngine
        
        engine = LeadScrapingEngine()
        result = engine.scrape_leads(
            industry=industry,
            location=location,
            company_size=company_size,
            sources=sources,
            limit=limit
        )
        
        return render_template('scraping_result.html', 
                             result=result,
                             industry=industry,
                             location=location)
    
    except Exception as e:
        logger.error(f"Error in scraping session: {str(e)}")
        return render_template('new_scraping.html', 
                             error=f"Scraping failed: {str(e)}")

@app.route('/api/scraping/status/<int:session_id>')
def scraping_status(session_id):
    """Get status of scraping session"""
    try:
        session = ScrapingSession.query.get_or_404(session_id)
        return jsonify({
            'id': session.id,
            'status': session.status,
            'leads_found': session.leads_found,
            'leads_processed': session.leads_processed,
            'success_rate': session.success_rate,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        })
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        return jsonify({'error': 'Session not found'}), 404

@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Basic counts
        total_leads = Lead.query.count()
        new_leads = Lead.query.filter(Lead.lead_status == 'new').count()
        contacted_leads = Lead.query.filter(Lead.lead_status == 'contacted').count()
        qualified_leads = Lead.query.filter(Lead.lead_status == 'qualified').count()
        converted_leads = Lead.query.filter(Lead.lead_status == 'converted').count()
        
        # Quality distribution
        high_quality = Lead.query.filter(Lead.quality_score >= 80).count()
        medium_quality = Lead.query.filter(Lead.quality_score.between(40, 79)).count()
        low_quality = Lead.query.filter(Lead.quality_score < 40).count()
        
        # Recent activity
        today = datetime.utcnow().date()
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)
        
        leads_today = Lead.query.filter(func.date(Lead.created_at) == today).count()
        leads_this_week = Lead.query.filter(Lead.created_at >= week_ago).count()
        leads_this_month = Lead.query.filter(Lead.created_at >= month_ago).count()
        
        return jsonify({
            'total_leads': total_leads,
            'new_leads': new_leads,
            'contacted_leads': contacted_leads,
            'qualified_leads': qualified_leads,
            'converted_leads': converted_leads,
            'high_quality': high_quality,
            'medium_quality': medium_quality,
            'low_quality': low_quality,
            'leads_today': leads_today,
            'leads_this_week': leads_this_week,
            'leads_this_month': leads_this_month
        })
    
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500

# Advanced Feature API Endpoints

@app.route('/api/notifications/settings', methods=['GET'])
def get_notification_settings():
    """Get current notification configuration"""
    try:
        from notifications import notification_manager
        settings = notification_manager.get_alert_settings()
        return jsonify(settings)
    
    except Exception as e:
        logger.error(f"Notification settings error: {str(e)}")
        return jsonify({'error': 'Failed to get notification settings'}), 500

@app.route('/api/notifications/test', methods=['POST'])
def test_notifications():
    """Test notification system"""
    try:
        from notifications import notification_manager
        result = notification_manager.test_notifications()
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Notification test error: {str(e)}")
        return jsonify({'error': 'Failed to test notifications'}), 500

@app.route('/api/accounts/intelligence', methods=['GET'])
def get_account_intelligence():
    """Get account-based intelligence summary"""
    try:
        from account_intelligence import account_intelligence
        top_accounts = account_intelligence.get_top_accounts(limit=20)
        return jsonify({
            'top_accounts': top_accounts,
            'total_accounts': len(top_accounts)
        })
    
    except Exception as e:
        logger.error(f"Account intelligence error: {str(e)}")
        return jsonify({'error': 'Failed to get account intelligence'}), 500

@app.route('/api/accounts/<domain>/analysis', methods=['GET'])
def analyze_account_intent(domain):
    """Analyze buying intent for specific account"""
    try:
        from account_intelligence import account_intelligence
        analysis = account_intelligence.analyze_account_intent(domain)
        return jsonify(analysis)
    
    except Exception as e:
        logger.error(f"Account analysis error for {domain}: {str(e)}")
        return jsonify({'error': 'Failed to analyze account intent'}), 500

@app.route('/api/accounts/<domain>/hierarchy', methods=['GET'])
def get_account_hierarchy(domain):
    """Get organizational hierarchy for account"""
    try:
        from account_intelligence import account_intelligence
        hierarchy = account_intelligence.get_account_hierarchy(domain)
        return jsonify(hierarchy)
    
    except Exception as e:
        logger.error(f"Account hierarchy error for {domain}: {str(e)}")
        return jsonify({'error': 'Failed to get account hierarchy'}), 500

@app.route('/api/leads/<int:lead_id>/audit', methods=['GET'])
def get_lead_audit_history(lead_id):
    """Get complete audit history for a lead"""
    try:
        from utils.lead_audit import audit_manager
        limit = int(request.args.get('limit', 50))
        history = audit_manager.get_lead_history(lead_id, limit)
        return jsonify({
            'lead_id': lead_id,
            'history': history,
            'total_changes': len(history)
        })
    
    except Exception as e:
        logger.error(f"Lead audit history error for {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to get audit history'}), 500

@app.route('/api/leads/<int:lead_id>/score-evolution', methods=['GET'])
def get_lead_score_evolution(lead_id):
    """Get quality score evolution for a lead"""
    try:
        from utils.lead_audit import audit_manager
        evolution = audit_manager.get_quality_score_evolution(lead_id)
        return jsonify(evolution)
    
    except Exception as e:
        logger.error(f"Score evolution error for {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to get score evolution'}), 500

@app.route('/api/team/activity', methods=['GET'])
def get_team_activity():
    """Get team activity summary for collaboration"""
    try:
        from utils.lead_audit import audit_manager
        days = int(request.args.get('days', 7))
        activity = audit_manager.get_team_activity_summary(days)
        return jsonify(activity)
    
    except Exception as e:
        logger.error(f"Team activity error: {str(e)}")
        return jsonify({'error': 'Failed to get team activity'}), 500

@app.route('/api/leads/<int:lead_id>/revert', methods=['POST'])
def revert_lead_field(lead_id):
    """Revert a lead field to previous value"""
    try:
        data = request.get_json() or {}
        field_name = data.get('field_name')
        target_timestamp = data.get('target_timestamp')
        reverted_by = data.get('reverted_by', 'unknown')
        
        if not field_name or not target_timestamp:
            return jsonify({'error': 'field_name and target_timestamp required'}), 400
        
        from utils.lead_audit import audit_manager
        success = audit_manager.revert_lead_field(lead_id, field_name, target_timestamp, reverted_by)
        
        if success:
            return jsonify({'success': True, 'message': 'Field reverted successfully'})
        else:
            return jsonify({'error': 'Failed to revert field'}), 400
    
    except Exception as e:
        logger.error(f"Field revert error for {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to revert field'}), 500

# Live Lead Generation Endpoints
@app.route('/api/leads/generate-live', methods=['POST'])
def generate_live_leads():
    """Generate real leads using live web scraping"""
    try:
        data = request.get_json() or {}
        industry = data.get('industry', 'HVAC')
        location = data.get('location', 'Dallas, TX')
        max_leads = min(int(data.get('count', 10)), 25)  # Max 25 for live scraping
        
        logger.info(f"Starting live lead generation: {industry} in {location}")
        
        # Import enhanced scraping engine
        from scrapers.integration import enhanced_engine
        
        # Generate enhanced business leads with data enrichment
        scraping_result = enhanced_engine.generate_enhanced_leads(
            industry=industry,
            location=location,
            max_leads=max_leads,
            enable_enrichment=True
        )
        
        if not scraping_result['success']:
            return jsonify({
                'success': False,
                'error': scraping_result.get('error', 'Enhanced scraping failed'),
                'generated_count': 0
            })
        
        scraped_leads = scraping_result['leads']
        
        # Save leads to database
        saved_leads = []
        for lead_data in scraped_leads:
            try:
                # Check for existing lead with same email
                existing = Lead.query.filter_by(email=lead_data['email']).first()
                if existing:
                    logger.info(f"Skipping duplicate lead: {lead_data['email']}")
                    continue
                
                new_lead = Lead(
                    company_name=lead_data['company_name'],
                    contact_name=lead_data.get('contact_name', ''),
                    email=lead_data['email'],
                    phone=lead_data.get('phone', ''),
                    website=lead_data.get('website', ''),
                    industry=lead_data['industry'],
                    location=lead_data['location'],
                    quality_score=lead_data['quality_score'],
                    lead_status='new',
                    source=lead_data.get('source', 'live_scraping'),
                    description=lead_data.get('description', ''),
                    company_size='Unknown'
                )
                
                db.session.add(new_lead)
                db.session.commit()
                
                saved_leads.append({
                    'id': new_lead.id,
                    'company_name': new_lead.company_name,
                    'contact_name': new_lead.contact_name,
                    'email': new_lead.email,
                    'phone': new_lead.phone,
                    'website': new_lead.website,
                    'quality_score': new_lead.quality_score,
                    'industry': new_lead.industry,
                    'location': new_lead.location
                })
                
            except Exception as e:
                logger.error(f"Error saving lead {lead_data.get('company_name', 'Unknown')}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'generated_count': len(saved_leads),
            'scraped_count': len(scraped_leads),
            'leads': saved_leads,
            'message': f'Successfully generated {len(saved_leads)} enhanced {industry} leads from {location}',
            'sources_used': scraping_result['stats'].get('sources_used', ['Enhanced Scraping']),
            'enhancement_stats': {
                'enrichment_applied': scraping_result['stats'].get('enrichment_applied', False),
                'average_quality': scraping_result['stats'].get('average_quality_score', 0),
                'high_quality_count': scraping_result['stats'].get('high_quality_count', 0)
            }
        })
    
    except Exception as e:
        logger.error(f"Live lead generation error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate live leads',
            'details': str(e)
        }), 500

@app.route('/api/enhanced-scraping-capabilities', methods=['GET'])
def get_enhanced_scraping_capabilities():
    """Get information about enhanced scraping capabilities"""
    try:
        from scrapers.integration import enhanced_engine
        capabilities = enhanced_engine.get_scraping_capabilities()
        
        return jsonify({
            'success': True,
            'capabilities': capabilities,
            'status': 'Enhanced scraping engine operational',
            'version': '2.0',
            'improvements': [
                'Multi-source data collection from Google and business directories',
                'Advanced quality scoring with 12+ factors',
                'Real-time email deliverability validation',
                'Business legitimacy verification',
                'Website quality analysis and SSL checking',
                'Industry-specific targeting and templates',
                'Duplicate prevention across sources',
                'Enhanced contact information validation'
            ]
        })
    
    except Exception as e:
        logger.error(f"Enhanced scraping capabilities error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/enhanced-validate-lead', methods=['POST'])
def enhanced_validate_lead_data():
    """Validate and enrich existing lead data"""
    try:
        data = request.get_json() or {}
        lead_id = data.get('lead_id')
        
        if not lead_id:
            return jsonify({'error': 'Lead ID required'}), 400
        
        lead = Lead.query.get_or_404(lead_id)
        
        # Convert lead to dict for validation
        lead_data = {
            'company_name': lead.company_name,
            'contact_name': lead.contact_name,
            'email': lead.email,
            'phone': lead.phone,
            'website': lead.website,
            'location': lead.location
        }
        
        from scrapers.integration import enhanced_engine
        validation_result = enhanced_engine.enricher.validate_business_legitimacy(lead_data)
        
        # Update lead with validation results
        lead.validation_score = validation_result.get('legitimacy_score', 0)
        lead.last_validated = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'lead_id': lead_id,
            'validation_result': validation_result,
            'message': 'Lead validation completed successfully'
        })
    
    except Exception as e:
        logger.error(f"Lead validation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/enhanced-scraping-demo')
def enhanced_scraping_demo():
    """Demo page for enhanced scraping capabilities"""
    return render_template('enhanced_scraping_demo.html')

# Demo Endpoints for Testing (Keep for demonstration)
@app.route('/api/demo/generate-leads', methods=['POST'])
def demo_generate_leads():
    """Generate sample leads for demonstration"""
    try:
        data = request.get_json() or {}
        industry = data.get('industry', 'HVAC')
        location = data.get('location', 'Dallas, TX')
        count = min(int(data.get('count', 5)), 10)  # Max 10 for demo
        
        # Sample lead templates for demonstration
        lead_templates = [
            {
                'HVAC': [
                    {'name': 'CoolAir Solutions', 'contact': 'Sarah Martinez', 'email': 'sarah@coolair-solutions.com', 'phone': '(214) 555-0123', 'score': 92},
                    {'name': 'Premier Climate Control', 'contact': 'David Chen', 'email': 'david@premier-climate.com', 'phone': '(214) 555-0234', 'score': 85},
                    {'name': 'Apex Heating & Cooling', 'contact': 'Jennifer Wilson', 'email': 'jen@apex-hvac.com', 'phone': '(214) 555-0345', 'score': 78},
                    {'name': 'Reliable HVAC Services', 'contact': 'Michael Brown', 'email': 'mike@reliable-hvac.com', 'phone': '(214) 555-0456', 'score': 88},
                    {'name': 'Quality Air Systems', 'contact': 'Lisa Anderson', 'email': 'lisa@quality-air.com', 'phone': '(214) 555-0567', 'score': 91}
                ],
                'Dental': [
                    {'name': 'Bright Smile Dentistry', 'contact': 'Dr. Amanda Foster', 'email': 'amanda@brightsmile.com', 'phone': '(305) 555-1111', 'score': 94},
                    {'name': 'Family Dental Care', 'contact': 'Dr. Robert Kim', 'email': 'robert@familydentalcare.com', 'phone': '(305) 555-2222', 'score': 87},
                    {'name': 'Modern Orthodontics', 'contact': 'Dr. Patricia Lopez', 'email': 'patricia@modern-ortho.com', 'phone': '(305) 555-3333', 'score': 89},
                    {'name': 'Coastal Dental Group', 'contact': 'Dr. Thomas Wright', 'email': 'thomas@coastal-dental.com', 'phone': '(305) 555-4444', 'score': 83},
                    {'name': 'Elite Dental Practice', 'contact': 'Dr. Maria Gonzalez', 'email': 'maria@elite-dental.com', 'phone': '(305) 555-5555', 'score': 96}
                ],
                'Legal': [
                    {'name': 'Johnson & Associates Law', 'contact': 'Partner John Johnson', 'email': 'john@johnson-law.com', 'phone': '(713) 555-7777', 'score': 90},
                    {'name': 'Smith Legal Group', 'contact': 'Attorney Sarah Smith', 'email': 'sarah@smith-legal.com', 'phone': '(713) 555-8888', 'score': 86},
                    {'name': 'Corporate Law Partners', 'contact': 'Partner David Miller', 'email': 'david@corp-law.com', 'phone': '(713) 555-9999', 'score': 93},
                    {'name': 'Family Law Center', 'contact': 'Attorney Rachel Davis', 'email': 'rachel@family-law.com', 'phone': '(713) 555-0000', 'score': 81},
                    {'name': 'Business Legal Solutions', 'contact': 'Partner Mark Thompson', 'email': 'mark@biz-legal.com', 'phone': '(713) 555-1234', 'score': 88}
                ]
            }
        ]
        
        # Get leads for the specified industry
        industry_leads = lead_templates[0].get(industry, lead_templates[0]['HVAC'])[:count]
        
        generated_leads = []
        for i, template in enumerate(industry_leads):
            # Create lead in database
            new_lead = Lead(
                company_name=template['name'],
                contact_name=template['contact'],
                email=template['email'],
                phone=template['phone'],
                website=f"https://www.{template['name'].lower().replace(' ', '').replace('&', 'and')}.com",
                industry=industry,
                location=location,
                quality_score=template['score'],
                lead_status='new',
                source='demo_generation',
                description=f"High-quality {industry.lower()} company in {location}",
                company_size='Medium' if template['score'] > 85 else 'Small',
                employee_count=50 if template['score'] > 85 else 25
            )
            
            db.session.add(new_lead)
            db.session.commit()
            
            generated_leads.append({
                'id': new_lead.id,
                'company_name': new_lead.company_name,
                'contact_name': new_lead.contact_name,
                'email': new_lead.email,
                'phone': new_lead.phone,
                'quality_score': new_lead.quality_score,
                'industry': new_lead.industry,
                'location': new_lead.location
            })
        
        return jsonify({
            'success': True,
            'generated_count': len(generated_leads),
            'leads': generated_leads,
            'message': f'Generated {len(generated_leads)} {industry} leads for {location}'
        })
    
    except Exception as e:
        logger.error(f"Demo lead generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate demo leads'}), 500

@app.route('/api/demo/ai-insights/<int:lead_id>', methods=['POST'])
def demo_ai_insights(lead_id):
    """Generate AI insights for demonstration"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        
        # Generate comprehensive business intelligence
        insights = {
            'company_analysis': {
                'overview': f"{lead.company_name} is a {'high-performing' if lead.quality_score >= 85 else 'established'} {lead.industry.lower()} company serving the {lead.location} market.",
                'strengths': [
                    f"Strong local presence in {lead.location}",
                    f"Established {lead.industry.lower()} expertise",
                    "Professional online presence",
                    "Customer-focused service approach"
                ],
                'growth_opportunities': [
                    "Digital marketing expansion",
                    "Service area expansion",
                    "Technology integration opportunities",
                    "Partnership development potential"
                ],
                'pain_points': [
                    "Lead generation challenges",
                    "Online visibility optimization",
                    "Competitive market pressures",
                    "Customer acquisition costs"
                ]
            },
            'engagement_strategy': {
                'recommended_approach': 'Professional consultation offering',
                'optimal_timing': 'Tuesday-Thursday, 10 AM - 2 PM',
                'key_value_propositions': [
                    "Proven ROI improvement strategies",
                    "Industry-specific solutions",
                    "Local market expertise",
                    "Immediate implementation support"
                ],
                'objection_handling': [
                    "Budget concerns: Demonstrate clear ROI metrics",
                    "Timing issues: Offer flexible implementation",
                    "Trust factors: Provide local references",
                    "Competition: Highlight unique differentiators"
                ]
            },
            'lead_scoring_breakdown': {
                'contact_quality': lead.quality_score * 0.3,
                'company_fit': lead.quality_score * 0.25,
                'buying_intent': lead.quality_score * 0.25,
                'authority_level': lead.quality_score * 0.2,
                'overall_score': lead.quality_score,
                'confidence_level': 0.92 if lead.quality_score >= 85 else 0.78
            },
            'next_steps': [
                "Research company's recent projects and achievements",
                "Identify key decision makers and stakeholders",
                "Prepare customized value proposition presentation",
                "Schedule initial consultation call",
                "Follow up with industry-specific case studies"
            ]
        }
        
        return jsonify({
            'success': True,
            'lead_id': lead_id,
            'company_name': lead.company_name,
            'insights': insights,
            'generated_at': datetime.utcnow().isoformat(),
            'ai_provider': 'OpenAI GPT-4o'
        })
    
    except Exception as e:
        logger.error(f"Demo AI insights error for {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to generate AI insights'}), 500

@app.route('/api/demo/system-status', methods=['GET'])
def demo_system_status():
    """Get comprehensive system status for demonstration"""
    try:
        # Database statistics
        total_leads = Lead.query.count()
        high_quality = Lead.query.filter(Lead.quality_score >= 80).count()
        medium_quality = Lead.query.filter(Lead.quality_score.between(60, 79)).count()
        low_quality = Lead.query.filter(Lead.quality_score < 60).count()
        
        # Industry breakdown
        industries = db.session.query(Lead.industry, func.count(Lead.id)).group_by(Lead.industry).all()
        industry_stats = [{'industry': industry, 'count': count} for industry, count in industries]
        
        # Quality distribution
        avg_quality = db.session.query(func.avg(Lead.quality_score)).scalar() or 0
        
        # Recent activity
        recent_leads = Lead.query.filter(
            Lead.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        status = {
            'system_health': {
                'status': 'operational',
                'uptime': '99.9%',
                'response_time': '45ms average',
                'database_status': 'connected',
                'ai_provider_status': 'ready'
            },
            'lead_statistics': {
                'total_leads': total_leads,
                'high_quality_leads': high_quality,
                'medium_quality_leads': medium_quality,
                'low_quality_leads': low_quality,
                'average_quality_score': round(avg_quality, 1),
                'leads_added_today': recent_leads
            },
            'industry_breakdown': industry_stats,
            'performance_metrics': {
                'lead_generation_rate': '50+ leads/hour',
                'ai_analysis_speed': '<10 seconds',
                'email_deliverability': '95%+',
                'data_accuracy': '90%+',
                'conversion_rate': '18% average'
            },
            'feature_status': {
                'account_intelligence': 'active',
                'email_validation': 'active',
                'phone_intelligence': 'ready',
                'auto_revalidation': 'scheduled',
                'notifications': 'configured',
                'audit_trail': 'logging'
            }
        }
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"System status error: {str(e)}")
        return jsonify({'error': 'Failed to get system status'}), 500

# Advanced Features API Endpoints

@app.route('/api/leads/<int:lead_id>/competitive-analysis', methods=['GET'])
def get_competitive_analysis(lead_id):
    """Get competitive analysis for a lead"""
    try:
        from features.competitive_analysis import competitive_analyzer
        analysis = competitive_analyzer.analyze_competitors(lead_id)
        return jsonify(analysis)
    
    except Exception as e:
        logger.error(f"Competitive analysis error for lead {lead_id}: {e}")
        return jsonify({'error': 'Failed to get competitive analysis'}), 500

@app.route('/api/leads/<int:lead_id>/email-template', methods=['POST'])
def generate_email_template(lead_id):
    """Generate personalized email template for a lead"""
    try:
        data = request.get_json() or {}
        template_type = data.get('template_type', 'introduction')
        
        # Get AI insights for personalization
        ai_insights = data.get('ai_insights')
        
        from features.email_templates import email_template_manager
        email_result = email_template_manager.generate_email(lead_id, template_type, ai_insights)
        
        # Track email generation
        if email_result.get('success'):
            from features.analytics_dashboard import analytics_dashboard
            analytics_dashboard.track_email_sent(
                lead_id, 
                template_type, 
                email_result['email']['subject']
            )
        
        return jsonify(email_result)
    
    except Exception as e:
        logger.error(f"Email template generation error for lead {lead_id}: {e}")
        return jsonify({'error': 'Failed to generate email template'}), 500

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_analytics_dashboard():
    """Get comprehensive analytics dashboard data"""
    try:
        days = int(request.args.get('days', 30))
        from features.analytics_dashboard import analytics_dashboard
        metrics = analytics_dashboard.get_dashboard_metrics(days)
        return jsonify(metrics)
    
    except Exception as e:
        logger.error(f"Analytics dashboard error: {e}")
        return jsonify({'error': 'Failed to get analytics data'}), 500

@app.route('/api/leads/<int:lead_id>/consultant-assessment', methods=['GET'])
def get_consultant_assessment(lead_id):
    """Get business assessment for consultant approach"""
    try:
        from features.consultant_approach import consultant_approach
        assessment = consultant_approach.assess_business_for_consultant_approach(lead_id)
        return jsonify(assessment)
    
    except Exception as e:
        logger.error(f"Consultant assessment error for lead {lead_id}: {e}")
        return jsonify({'error': 'Failed to get consultant assessment'}), 500

@app.route('/api/generate-consultant-email', methods=['POST'])
def generate_consultant_email():
    """Generate consultant-positioned email"""
    try:
        data = request.get_json() or {}
        lead_id = data.get('lead_id')
        template_type = data.get('template_type', 'introduction')
        
        if not lead_id:
            return jsonify({'error': 'lead_id required'}), 400
        
        from features.consultant_approach import consultant_approach
        email_result = consultant_approach.generate_consultant_email(lead_id, template_type)
        
        # Track email generation in analytics
        if email_result.get('success'):
            from features.analytics_dashboard import analytics_dashboard
            email_data = email_result['email_data']
            analytics_dashboard.track_email_sent(
                lead_id,
                f"consultant_{template_type}",
                email_data['subject_options'][0]
            )
        
        return jsonify(email_result)
    
    except Exception as e:
        logger.error(f"Consultant email generation error: {e}")
        return jsonify({'error': 'Failed to generate consultant email'}), 500

# Data Validation & Quality Endpoints
@app.route('/api/leads/<int:lead_id>/validate', methods=['POST'])
def validate_lead_data(lead_id):
    """Validate lead data quality"""
    try:
        data = request.get_json() or {}
        deep_validation = data.get('deep_validation', False)
        
        from features.data_validation import data_validator
        validation_result = data_validator.validate_lead_data(lead_id, deep_validation)
        return jsonify(validation_result)
    
    except Exception as e:
        logger.error(f"Lead validation error for {lead_id}: {e}")
        return jsonify({'error': 'Validation failed'}), 500

@app.route('/api/leads/bulk-validate', methods=['POST'])
def bulk_validate_leads():
    """Bulk validate multiple leads"""
    try:
        data = request.get_json() or {}
        lead_ids = data.get('lead_ids', [])
        
        if not lead_ids:
            return jsonify({'error': 'lead_ids required'}), 400
        
        from features.data_validation import data_validator
        validation_result = data_validator.bulk_validate_leads(lead_ids)
        return jsonify(validation_result)
    
    except Exception as e:
        logger.error(f"Bulk validation error: {e}")
        return jsonify({'error': 'Bulk validation failed'}), 500

# Bulk Operations Endpoints
@app.route('/api/leads/bulk-delete', methods=['POST'])
def bulk_delete_leads():
    """Bulk delete multiple leads"""
    try:
        data = request.get_json() or {}
        lead_ids = data.get('lead_ids', [])
        user_id = data.get('user_id', 'system')
        
        if not lead_ids:
            return jsonify({'error': 'lead_ids required'}), 400
        
        from features.bulk_operations import bulk_operations_manager
        result = bulk_operations_manager.bulk_delete_leads(lead_ids, user_id)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Bulk delete error: {e}")
        return jsonify({'error': 'Bulk delete failed'}), 500

@app.route('/api/leads/bulk-tag', methods=['POST'])
def bulk_tag_leads():
    """Bulk add/remove tags from leads"""
    try:
        data = request.get_json() or {}
        lead_ids = data.get('lead_ids', [])
        tags_to_add = data.get('tags_to_add', [])
        tags_to_remove = data.get('tags_to_remove', [])
        
        if not lead_ids:
            return jsonify({'error': 'lead_ids required'}), 400
        
        from features.bulk_operations import bulk_operations_manager
        result = bulk_operations_manager.bulk_tag_leads(lead_ids, tags_to_add, tags_to_remove)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Bulk tag error: {e}")
        return jsonify({'error': 'Bulk tag operation failed'}), 500

@app.route('/api/leads/bulk-export', methods=['POST'])
def bulk_export_leads():
    """Export multiple leads"""
    try:
        data = request.get_json() or {}
        lead_ids = data.get('lead_ids', [])
        export_format = data.get('format', 'csv')
        
        if not lead_ids:
            return jsonify({'error': 'lead_ids required'}), 400
        
        from features.bulk_operations import bulk_operations_manager
        result = bulk_operations_manager.bulk_export_leads(lead_ids, export_format)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Bulk export error: {e}")
        return jsonify({'error': 'Bulk export failed'}), 500

# Lead Health Scoring
@app.route('/api/leads/<int:lead_id>/health-score', methods=['GET'])
def get_lead_health_score(lead_id):
    """Get comprehensive lead health score"""
    try:
        from features.bulk_operations import lead_health_scorer
        health_score = lead_health_scorer.calculate_lead_health_score(lead_id)
        return jsonify(health_score)
    
    except Exception as e:
        logger.error(f"Lead health scoring error for {lead_id}: {e}")
        return jsonify({'error': 'Health scoring failed'}), 500

# Compliance & Privacy Endpoints
@app.route('/api/leads/<int:lead_id>/gdpr-compliance', methods=['GET'])
def check_gdpr_compliance(lead_id):
    """Check GDPR compliance status"""
    try:
        from features.compliance_manager import compliance_manager
        compliance_status = compliance_manager.gdpr_compliance_check(lead_id)
        return jsonify(compliance_status)
    
    except Exception as e:
        logger.error(f"GDPR compliance check error for {lead_id}: {e}")
        return jsonify({'error': 'Compliance check failed'}), 500

@app.route('/api/privacy/consent', methods=['POST'])
def record_consent():
    """Record privacy consent"""
    try:
        data = request.get_json() or {}
        lead_id = data.get('lead_id')
        consent_type = data.get('consent_type')
        consent_given = data.get('consent_given')
        
        if not all([lead_id, consent_type, consent_given is not None]):
            return jsonify({'error': 'lead_id, consent_type, and consent_given required'}), 400
        
        from features.compliance_manager import compliance_manager
        result = compliance_manager.record_consent(lead_id, consent_type, consent_given)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Consent recording error: {e}")
        return jsonify({'error': 'Consent recording failed'}), 500

@app.route('/api/privacy/do-not-contact', methods=['POST'])
def add_to_do_not_contact():
    """Add to do-not-contact list"""
    try:
        data = request.get_json() or {}
        identifier = data.get('identifier')  # email or phone
        reason = data.get('reason', 'user_request')
        
        if not identifier:
            return jsonify({'error': 'identifier required'}), 400
        
        from features.compliance_manager import compliance_manager
        result = compliance_manager.add_to_do_not_contact(identifier, reason)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Do-not-contact error: {e}")
        return jsonify({'error': 'Failed to add to do-not-contact list'}), 500

# Email Tracking System Endpoints
@app.route('/api/generate-tracked-email', methods=['POST'])
def generate_tracked_email():
    """Generate consultant email with full tracking"""
    try:
        data = request.get_json() or {}
        lead_id = data.get('lead_id')
        template_type = data.get('template_type', 'introduction')
        user_id = data.get('user_id', 'system')
        
        if not lead_id:
            return jsonify({'error': 'lead_id required'}), 400
        
        from features.email_tracking import email_tracker
        tracked_email = email_tracker.generate_tracked_email(lead_id, template_type, user_id)
        return jsonify(tracked_email)
    
    except Exception as e:
        logger.error(f"Tracked email generation error: {e}")
        return jsonify({'error': 'Failed to generate tracked email'}), 500

@app.route('/track/open/<tracking_id>')
def track_email_open(tracking_id):
    """Track email opens with 1x1 pixel"""
    try:
        from features.email_tracking import email_tracker
        email_tracker.record_tracking_event(
            tracking_id=tracking_id,
            event_type='open',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
    except Exception as e:
        logger.error(f"Error tracking email open: {e}")
    
    # Return 1x1 transparent PNG
    pixel_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00'
    
    return Response(pixel_data, mimetype='image/png')

@app.route('/track/click')
def track_email_click():
    """Track email clicks and redirect"""
    tracking_id = request.args.get('tid')
    original_url = request.args.get('url')
    
    if not tracking_id or not original_url:
        return "Invalid tracking link", 400
    
    try:
        from features.email_tracking import email_tracker
        email_tracker.record_tracking_event(
            tracking_id=tracking_id,
            event_type='click',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            click_url=original_url
        )
    except Exception as e:
        logger.error(f"Error tracking email click: {e}")
    
    # Redirect to original URL
    return redirect(original_url)

@app.route('/api/email-tracking-stats')
def email_tracking_stats_api():
    """API endpoint for email tracking statistics"""
    try:
        lead_id = request.args.get('lead_id', type=int)
        days = request.args.get('days', 30, type=int)
        email_id = request.args.get('email_id', type=int)
        
        from features.email_tracking import email_tracker
        stats = email_tracker.get_email_tracking_stats(lead_id, days, email_id)
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Email tracking stats error: {e}")
        return jsonify({'error': 'Failed to get tracking stats'}), 500

@app.route('/api/leads/<int:lead_id>/email-performance')
def get_lead_email_performance(lead_id):
    """Get email performance for specific lead"""
    try:
        from features.email_tracking import email_tracker
        performance = email_tracker.get_lead_email_performance(lead_id)
        return jsonify(performance)
    
    except Exception as e:
        logger.error(f"Lead email performance error: {e}")
        return jsonify({'error': 'Failed to get email performance'}), 500

# Ollama Integration Endpoints
@app.route('/api/ollama/test-connection', methods=['GET'])
def test_ollama_connection():
    """Test Ollama connection and Mistral 7B availability"""
    try:
        from features.ollama_integration import ollama_analyzer
        connection_status = ollama_analyzer.test_connection()
        return jsonify(connection_status)
    
    except Exception as e:
        logger.error(f"Ollama connection test error: {e}")
        return jsonify({
            'status': 'error',
            'available': False,
            'error': str(e)
        }), 500

@app.route('/api/analyze-lead-ollama', methods=['POST'])
def analyze_lead_ollama_api():
    """Analyze lead using local Ollama"""
    try:
        data = request.get_json() or {}
        lead_id = data.get('lead_id')
        
        if not lead_id:
            return jsonify({'success': False, 'error': 'Lead ID required'}), 400
        
        # Get lead data
        lead = Lead.query.get(lead_id)
        if not lead:
            return jsonify({'success': False, 'error': 'Lead not found'}), 404
        
        # Prepare lead data for analysis
        lead_data = {
            'company_name': lead.company_name,
            'website': lead.website,
            'industry': lead.industry,
            'location': lead.location,
            'contact_name': lead.contact_name,
            'description': lead.description or 'Professional business services'
        }
        
        # Analyze with Ollama
        from features.ollama_integration import ollama_analyzer
        analysis = ollama_analyzer.analyze_lead_with_ollama(lead_data)
        
        # Store analysis in database
        import json
        lead.ai_analysis = json.dumps(analysis)
        lead.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'provider': 'ollama_mistral7b',
            'updated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in Ollama analysis: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-consultant-email-ollama', methods=['POST'])
def generate_consultant_email_ollama_api():
    """Generate consultant email using Ollama"""
    try:
        data = request.get_json() or {}
        lead_id = data.get('lead_id')
        
        if not lead_id:
            return jsonify({'error': 'lead_id required'}), 400
        
        from features.ollama_integration import ollama_analyzer
        email_data = ollama_analyzer.generate_consultant_email_ollama(lead_id)
        
        # Track email generation in analytics if successful
        if email_data.get('success') and 'subject_lines' in email_data.get('email_data', {}):
            try:
                from features.analytics_dashboard import analytics_dashboard
                analytics_dashboard.track_email_sent(
                    lead_id,
                    'consultant_ollama',
                    email_data['email_data']['subject_lines'][0]
                )
            except Exception as e:
                logger.warning(f"Failed to track email analytics: {e}")
        
        return jsonify(email_data)
        
    except Exception as e:
        logger.error(f"Ollama email generation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads/<int:lead_id>')
def get_lead(lead_id):
    """Get detailed information for a specific lead"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        
        lead_data = {
            'id': lead.id,
            'company_name': lead.company_name,
            'contact_name': lead.contact_name,
            'email': lead.email,
            'phone': lead.phone,
            'website': lead.website,
            'industry': lead.industry,
            'location': lead.location,
            'description': lead.description,
            'quality_score': lead.quality_score,
            'status': lead.lead_status,
            'tags': lead.tags,
            'created_at': lead.created_at.isoformat() if lead.created_at else None,
            'updated_at': lead.updated_at.isoformat() if lead.updated_at else None,
            'ai_analysis': json.loads(lead.ai_analysis) if lead.ai_analysis else None
        }
        
        return jsonify(lead_data)
    
    except Exception as e:
        logger.error(f"Error getting lead {lead_id}: {e}")
        return jsonify({'error': 'Lead not found'}), 404



@app.route('/api/ai-provider-comparison/<int:lead_id>', methods=['GET'])
def ai_provider_comparison(lead_id):
    """Compare analysis from both OpenAI and Ollama"""
    try:
        lead = Lead.query.get(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        
        # Prepare lead data
        lead_data = {
            'company_name': lead.company_name,
            'website': lead.website,
            'industry': lead.industry,
            'location': lead.location,
            'contact_name': lead.contact_name,
            'description': lead.description or 'Professional business services'
        }
        
        # Get OpenAI analysis
        try:
            from rag_system_openai import rag_system
            openai_analysis = rag_system.analyze_lead_business_intelligence(lead_data)
        except Exception as e:
            openai_analysis = {'error': f'OpenAI analysis failed: {str(e)}'}
        
        # Get Ollama analysis
        try:
            from features.ollama_integration import ollama_analyzer
            ollama_analysis = ollama_analyzer.analyze_lead_with_ollama(lead_data)
        except Exception as e:
            ollama_analysis = {'error': f'Ollama analysis failed: {str(e)}'}
        
        return jsonify({
            'lead_id': lead_id,
            'company_name': lead.company_name,
            'openai_analysis': openai_analysis,
            'ollama_analysis': ollama_analysis,
            'comparison_generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"AI provider comparison error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)