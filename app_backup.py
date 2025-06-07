import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
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

with app.app_context():
    try:
        # Import models to create tables
        from models import Lead, ScrapingSession, LeadInteraction, LeadList, LeadListMembership
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        # Continue anyway, tables might already exist

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
        from models import Lead
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
        
        from models import Lead
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
        
        return render_template('leads.html',
                             leads=leads,
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
        return render_template('leads.html', leads=[], error="Error loading leads")

@app.route('/lead/<int:lead_id>')
def lead_detail(lead_id):
    """Detailed view of a single lead"""
    try:
        from models import Lead, LeadInteraction
        lead = Lead.query.get_or_404(lead_id)
        interactions = LeadInteraction.query.filter_by(lead_id=lead_id).order_by(
            desc(LeadInteraction.interaction_date)
        ).all()
        
        return render_template('lead_detail.html', lead=lead, interactions=interactions)
    
    except Exception as e:
        logger.error(f"Error loading lead {lead_id}: {str(e)}")
        return "Lead not found", 404

@app.route('/scraping')
def scraping_dashboard():
    """Scraping sessions management"""
    try:
        from models import ScrapingSession
        sessions = ScrapingSession.query.order_by(desc(ScrapingSession.started_at)).limit(20).all()
        
        return render_template('scraping.html', sessions=sessions)
    
    except Exception as e:
        logger.error(f"Error loading scraping dashboard: {str(e)}")
        return render_template('scraping.html', sessions=[], error="Error loading scraping data")

@app.route('/api/leads', methods=['GET'])
def api_leads():
    """API endpoint for leads data"""
    try:
        from models import Lead
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 25, type=int), 100)
        
        # Get filter parameters
        industry = request.args.get('industry')
        status = request.args.get('status')
        quality = request.args.get('quality')
        
        query = Lead.query
        
        # Apply filters
        if industry:
            query = query.filter(Lead.industry.ilike(f'%{industry}%'))
        if status:
            query = query.filter(Lead.lead_status == status)
        if quality:
            if quality == 'high':
                query = query.filter(Lead.quality_score >= 80)
            elif quality == 'medium':
                query = query.filter(Lead.quality_score.between(40, 79))
            elif quality == 'low':
                query = query.filter(Lead.quality_score < 40)
        
        leads = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'leads': [{
                'id': lead.id,
                'company_name': lead.company_name,
                'contact_name': lead.contact_name,
                'email': lead.email,
                'phone': lead.phone,
                'industry': lead.industry,
                'quality_score': lead.quality_score,
                'lead_status': lead.lead_status,
                'created_at': lead.created_at.isoformat() if lead.created_at else None
            } for lead in leads.items],
            'pagination': {
                'page': leads.page,
                'pages': leads.pages,
                'per_page': leads.per_page,
                'total': leads.total,
                'has_next': leads.has_next,
                'has_prev': leads.has_prev
            }
        })
    
    except Exception as e:
        logger.error(f"Error in leads API: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/lead/<int:lead_id>/update', methods=['POST'])
def update_lead(lead_id):
    """Update lead information"""
    try:
        from models import Lead
        lead = Lead.query.get_or_404(lead_id)
        
        data = request.get_json()
        
        # Update allowed fields
        if 'lead_status' in data:
            lead.lead_status = data['lead_status']
        if 'quality_score' in data:
            lead.quality_score = max(0, min(100, int(data['quality_score'])))
        if 'notes' in data:
            lead.notes = data['notes']
        if 'tags' in data:
            lead.set_tags(data['tags'])
        
        lead.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Lead updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating lead {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to update lead'}), 500

@app.route('/api/lead/<int:lead_id>/interaction', methods=['POST'])
def add_interaction(lead_id):
    """Add interaction to a lead"""
    try:
        from models import Lead, LeadInteraction
        lead = Lead.query.get_or_404(lead_id)
        
        data = request.get_json()
        
        interaction = LeadInteraction()
        interaction.lead_id = lead_id
        interaction.interaction_type = data.get('type', 'note')
        interaction.subject = data.get('subject')
        interaction.content = data.get('content')
        interaction.outcome = data.get('outcome')
        
        if data.get('follow_up_date'):
            interaction.follow_up_date = datetime.fromisoformat(data['follow_up_date'])
        
        # Update lead's last contacted date
        lead.last_contacted = datetime.utcnow()
        
        db.session.add(interaction)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Interaction added successfully'})
    
    except Exception as e:
        logger.error(f"Error adding interaction to lead {lead_id}: {str(e)}")
        return jsonify({'error': 'Failed to add interaction'}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        from models import Lead
        
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)