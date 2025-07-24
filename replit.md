# LeadNGN - AI-Powered Lead Generation & Management Platform

## Overview

LeadNGN is a comprehensive lead generation and management platform that combines automated web scraping with AI-powered business intelligence. The system targets high-value local service businesses and provides advanced analytics, personalized outreach generation, and multi-channel orchestration capabilities. Built with Flask and PostgreSQL, it features a premium black and gold UI theme and supports both cloud-based (OpenAI GPT-4o) and local AI processing (Ollama).

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM
- **Database**: PostgreSQL with optimized indexing and connection pooling
- **AI Processing**: Dual provider support (OpenAI GPT-4o and Ollama Llama2:13b)
- **Web Scraping**: Multi-source lead scraping with quality scoring
- **Background Processing**: Scheduled revalidation workflows and notifications

### Frontend Architecture
- **UI Theme**: Premium black and gold gradient design
- **Responsive Design**: Enterprise-grade visual design language
- **Real-time Updates**: Interactive dashboard with performance monitoring
- **API Integration**: RESTful endpoints for all major operations

### Database Schema
- **Core Models**: Lead, ScrapingSession, LeadInteraction, LeadList, LeadListMembership
- **Audit System**: LeadAuditLog for complete change history tracking
- **Intelligence Models**: Account grouping, email deliverability, phone validation

## Key Components

### Lead Management System
- **CRUD Operations**: Complete lead lifecycle management with audit trail
- **Quality Scoring**: 0-100 scale intelligent scoring with confidence metrics
- **Industry Categorization**: HVAC, Dental, Legal, Property Management, etc.
- **Status Tracking**: New, contacted, qualified, converted, rejected workflows
- **Advanced Filtering**: Geographic, industry, and quality-based search

### AI-Powered Intelligence Engine
- **Business Analysis**: Industry-specific pain point identification and market positioning
- **Personalized Outreach**: Context-aware email generation with value proposition matching
- **Lead Scoring**: Multi-factor assessment including authority, budget, and buying readiness
- **Provider Flexibility**: Seamless switching between cloud and local AI processing

### Strategic Enterprise Features
- **Account-Based Intelligence**: Corporate domain grouping with buying intent analysis
- **Email Deliverability System**: MX validation, reputation scoring, spam prevention
- **Phone Intelligence**: Twilio integration for call prioritization and SMS campaigns
- **Auto-Revalidation Workflows**: Scheduled data freshness maintenance (daily/weekly/monthly)
- **Real-Time Notifications**: Slack integration for high-value lead alerts
- **Lead Audit Trail**: Complete change history with field-level versioning

### Web Scraping Engine
- **Multi-Source Support**: Google search, business directories, company websites
- **Industry-Specific Targeting**: Optimized search terms for high-value sectors
- **Quality Assessment**: Automated scoring based on data completeness and relevance
- **Rate Limiting**: Respectful scraping with user agent rotation

## Data Flow

1. **Lead Discovery**: Web scraping identifies potential leads from multiple sources
2. **Quality Assessment**: Automated scoring evaluates lead potential (0-100 scale)
3. **AI Analysis**: Business intelligence engine analyzes company context and opportunities
4. **Enrichment**: Email deliverability and phone validation enhance contact data
5. **Personalization**: AI generates tailored outreach content based on analysis
6. **Workflow Management**: Status tracking and interaction history maintain lead lifecycle
7. **Revalidation**: Automated background processes maintain data freshness

## External Dependencies

### AI Providers
- **OpenAI GPT-4o**: Cloud-based AI processing for advanced analysis
- **Ollama**: Local AI processing with Llama2:13b model support
- **Automatic Fallback**: Intelligent switching between providers

### Third-Party Integrations
- **Twilio**: Phone number validation and SMS capabilities
- **Slack**: Real-time notification webhooks for team alerts
- **Email Validation**: DNS resolution and deliverability checking
- **Web Scraping**: Requests, BeautifulSoup, Selenium for data collection

### Python Dependencies
- **Flask**: Web framework with SQLAlchemy ORM
- **PostgreSQL**: Primary database with psycopg2 adapter
- **Celery**: Background task processing (planned)
- **SpaCy**: Natural language processing for text analysis

## Deployment Strategy

### Environment Configuration
- **Database**: PostgreSQL with connection pooling and health monitoring
- **AI Setup**: Environment variables control provider selection (USE_LOCAL_AI)
- **Secrets Management**: API keys and webhooks via environment variables
- **Logging**: Structured logging with appropriate levels

### Development Setup
- **Local Development**: SQLite fallback with automatic table creation
- **AI Configuration**: Support for both OpenAI API keys and local Ollama setup
- **Sample Data**: Seed scripts for demonstration and testing
- **Health Checks**: System status verification and dependency testing

### Production Considerations
- **Scalability**: Connection pooling and optimized database queries
- **Monitoring**: Real-time performance metrics and error tracking
- **Security**: Session management and input validation
- **Backup**: Audit trail system provides data recovery capabilities

### Deployment Options
- **Cloud Deployment**: Supports standard web hosting with PostgreSQL
- **Local Deployment**: Complete functionality with Ollama for cost-free operation
- **Hybrid Setup**: Cloud database with local AI processing for optimal cost/performance