import os
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
        from lead_audit import audit_manager
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
        from lead_audit import audit_manager
        evolution = audit_manager.get_quality_score_evolution(lead_id)
        return jsonify(evolution)
    
    except Exception as e:
        logger.error(f"Score evolution error for {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to get score evolution'}), 500

@app.route('/api/team/activity', methods=['GET'])
def get_team_activity():
    """Get team activity summary for collaboration"""
    try:
        from lead_audit import audit_manager
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
        field_name = request.json.get('field_name')
        target_timestamp = request.json.get('target_timestamp')
        reverted_by = request.json.get('reverted_by', 'unknown')
        
        if not field_name or not target_timestamp:
            return jsonify({'error': 'field_name and target_timestamp required'}), 400
        
        from lead_audit import audit_manager
        success = audit_manager.revert_lead_field(lead_id, field_name, target_timestamp, reverted_by)
        
        if success:
            return jsonify({'success': True, 'message': 'Field reverted successfully'})
        else:
            return jsonify({'error': 'Failed to revert field'}), 400
    
    except Exception as e:
        logger.error(f"Field revert error for {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to revert field'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)