# LeadNGN Email Tracking System

## Overview
The Email Tracking System provides comprehensive email engagement analytics for the consultant approach system, enabling detailed tracking of opens, clicks, replies, and overall engagement patterns.

## Database Schema

### Tables Created
```sql
-- Main email tracking table
CREATE TABLE sent_emails (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES lead(id),
    template_type VARCHAR(100),
    subject_line TEXT NOT NULL,
    email_body TEXT NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    tracking_id UUID DEFAULT gen_random_uuid(),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_by VARCHAR(255),
    campaign_type VARCHAR(100) DEFAULT 'consultant_outreach'
);

-- Tracking events table
CREATE TABLE email_tracking_events (
    id SERIAL PRIMARY KEY,
    sent_email_id INTEGER REFERENCES sent_emails(id),
    event_type VARCHAR(50) NOT NULL, -- 'open', 'click', 'reply', 'bounce'
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    click_url TEXT,
    metadata JSONB
);

-- Performance indexes
CREATE INDEX idx_tracking_events_email_id ON email_tracking_events(sent_email_id);
CREATE INDEX idx_tracking_events_type ON email_tracking_events(event_type);
CREATE INDEX idx_sent_emails_tracking_id ON sent_emails(tracking_id);
```

## Key Features

### 1. Tracked Email Generation
**Location:** `/features/email_tracking.py`

**Capabilities:**
- Integrates with consultant approach system
- Generates unique tracking IDs for each email
- Adds invisible 1x1 pixel tracking images
- Converts all links to tracked click URLs
- Stores email content and metadata for analytics

**API Endpoint:** `POST /api/generate-tracked-email`

**Request:**
```json
{
    "lead_id": 42,
    "template_type": "introduction",
    "user_id": "admin"
}
```

**Response:**
```json
{
    "success": true,
    "email_data": {
        "email_body": "<html>...with tracking pixel and tracked links</html>",
        "subject_options": ["Enterprise HVAC automation strategy..."],
        "tracking_id": "uuid-string"
    },
    "tracking": {
        "tracking_id": "uuid",
        "sent_email_id": 123,
        "tracking_enabled": true,
        "tracking_pixel_url": "https://yourdomain.com/track/open/uuid",
        "analytics_url": "https://yourdomain.com/api/email-tracking-stats?email_id=123"
    }
}
```

### 2. Real-Time Tracking Endpoints

**Email Open Tracking:**
- URL: `/track/open/{tracking_id}`
- Returns: 1x1 transparent PNG pixel
- Records: IP address, user agent, timestamp

**Click Tracking:**
- URL: `/track/click?tid={tracking_id}&url={original_url}`
- Records: Click event data
- Redirects: User to original destination

### 3. Comprehensive Analytics

**Email Performance Dashboard**
- API: `GET /api/email-tracking-stats?days=30&lead_id=42`
- Metrics: Opens, clicks, replies, engagement rates
- Timeline: Daily engagement breakdown
- Performance: Best subject lines and timing

**Lead-Specific Performance**
- API: `GET /api/leads/{id}/email-performance`
- Analysis: Engagement level classification
- Recommendations: Action items based on performance
- History: Full email interaction timeline

## Analytics Capabilities

### Summary Statistics
- **Total Sent:** Number of emails sent
- **Open Rate:** Percentage of emails opened
- **Click Rate:** Percentage with link clicks
- **Reply Rate:** Direct response percentage
- **Engagement Score:** Weighted combination metric

### Engagement Level Classification
- **Highly Engaged (70%+):** Regular opens and clicks
- **Moderately Engaged (40-69%):** Some interaction
- **Low Engagement (20-39%):** Minimal interaction
- **Unresponsive (<20%):** No significant engagement

### Performance Insights
- **Best Performing Subject Lines:** Data-driven optimization
- **Engagement Timeline:** Daily/weekly patterns
- **Click-through Analysis:** Link performance tracking
- **Recipient Behavior:** Individual engagement patterns

## Integration with Consultant System

### Seamless Integration
The email tracking system integrates directly with the consultant approach:

1. **Generate Tracked Email:** Creates consultant email with tracking
2. **Send via SMTP:** Use tracked HTML content
3. **Monitor Engagement:** Real-time analytics dashboard
4. **Optimize Approach:** Data-driven recommendations

### Enhanced Consultant Templates
All consultant email templates now include:
- Tracking pixel for open detection
- Tracked CTA links for engagement measurement
- Performance analytics for optimization
- Personalized follow-up recommendations

## Sample Analytics Results

### Overall Performance (30 days)
```json
{
    "summary": {
        "total_sent": 25,
        "total_opens": 18,
        "total_clicks": 8,
        "total_replies": 3,
        "open_rate": 72.0,
        "click_rate": 32.0,
        "reply_rate": 12.0,
        "engagement_score": 58.0
    }
}
```

### Lead-Specific Performance
```json
{
    "lead_id": 42,
    "engagement_rate": 85.0,
    "engagement_level": "highly_engaged",
    "best_performing_subject": "Enterprise HVAC automation strategy for Austin Air Conditioning",
    "recommendations": [
        "Schedule follow-up consultation call",
        "Send detailed case study or ROI analysis",
        "Propose specific implementation timeline"
    ]
}
```

### Engagement Timeline
```json
{
    "timeline": [
        {
            "date": "2025-07-24",
            "event_type": "open",
            "count": 5
        },
        {
            "date": "2025-07-24", 
            "event_type": "click",
            "count": 2
        }
    ]
}
```

## Technical Implementation

### Tracking ID Generation
- UUID4 for unique identification
- Stored in database with email metadata
- Used for all tracking URLs and pixels

### HTML Email Conversion
- Plain text emails converted to HTML
- Tracking pixel embedded invisibly
- All URLs replaced with tracking redirects
- Responsive design for mobile compatibility

### Privacy Compliance
- IP address anonymization options
- GDPR-compliant data handling
- Opt-out tracking respect
- Secure tracking URL generation

## Performance Optimizations

### Database Indexing
- Fast lookups by tracking ID
- Efficient event type filtering
- Optimized lead-specific queries

### Caching Strategy
- Analytics results cached for performance
- Real-time updates for new events
- Efficient bulk analytics processing

### Security Measures
- Secure tracking URL generation
- Input validation for all endpoints
- Rate limiting on tracking endpoints
- Malicious click detection

## Next Steps

### Enhanced Analytics
1. **A/B Testing Framework** - Template optimization
2. **Predictive Analytics** - Response probability scoring
3. **Heat Map Analysis** - Email content engagement
4. **Sentiment Analysis** - Reply content analysis

### Integration Expansion
1. **CRM Synchronization** - HubSpot/Salesforce tracking
2. **Email Platform APIs** - SendGrid/Mailgun integration
3. **Marketing Automation** - Drip campaign tracking
4. **Social Media Tracking** - Multi-channel engagement

### Advanced Features
1. **Real-time Notifications** - Instant engagement alerts
2. **Behavioral Triggers** - Action-based follow-ups
3. **Performance Dashboards** - Visual analytics interface
4. **Team Collaboration** - Shared tracking insights

The Email Tracking System transforms LeadNGN from simple email generation to comprehensive engagement analytics, enabling data-driven optimization of the consultant approach and significantly improving conversion rates through detailed performance insights.
