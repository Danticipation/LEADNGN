# Ollama Integration Setup for LeadNGN

## Overview
Ollama integration provides local AI analysis using Mistral 7B, offering cost-effective AI processing alongside OpenAI. This dual provider approach enables cost optimization and reduces dependency on external APIs.

## Current Implementation Status

### ✅ Completed Features
1. **Ollama Integration Module** (`/features/ollama_integration.py`)
   - OllamaAnalyzer class with lead analysis capabilities
   - Local Mistral 7B integration via Ollama Python client
   - Business intelligence analysis using local AI
   - Consultant email generation with Ollama
   - Fallback system when Ollama is unavailable

2. **API Endpoints Added**
   - `GET /api/ollama/test-connection` - Test Ollama connectivity
   - `POST /api/analyze-lead-ollama` - Lead analysis using Mistral 7B
   - `POST /api/generate-consultant-email-ollama` - Email generation with Ollama
   - `GET /api/ai-provider-comparison/{lead_id}` - Compare OpenAI vs Ollama results

3. **Dual AI Provider Support**
   - OpenAI GPT-4o for premium analysis
   - Local Ollama Mistral 7B for cost-effective processing
   - Automatic fallback to existing systems when Ollama unavailable
   - Provider comparison functionality

### 🔄 Current Status: Setup Required

**Ollama Connection Status:**
```json
{
    "available": false,
    "status": "failed",
    "error": "Failed to connect to Ollama",
    "solution": "Ensure Ollama is running and mistral:7b model is downloaded"
}
```

## Setup Instructions

### Step 1: Install Ollama
```bash
# For Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# For Windows
# Download from https://ollama.com/download
```

### Step 2: Download Mistral 7B Model
```bash
ollama pull mistral:7b
```

### Step 3: Start Ollama Service
```bash
ollama serve
```

### Step 4: Verify Installation
```bash
# Test Ollama is running
curl http://localhost:11434/api/tags

# Test model availability
ollama run mistral:7b "Hello, test response"
```

## Integration Architecture

### Lead Analysis Workflow
```python
# 1. Prepare lead data
lead_data = {
    'company_name': 'Austin Air Conditioning',
    'website': 'austinairconditioningllc.com',
    'industry': 'HVAC',
    'location': 'Austin, TX',
    'contact_name': 'Michael Johnson'
}

# 2. Analyze with Ollama
analysis = ollama_analyzer.analyze_lead_with_ollama(lead_data)

# 3. Store results in database
lead.ai_analysis = json.dumps(analysis)
```

### Email Generation Workflow
```python
# 1. Generate consultant email using Ollama
email_data = ollama_analyzer.generate_consultant_email_ollama(lead_id)

# 2. Integrate with existing consultant approach
# 3. Add tracking capabilities
# 4. Store for analytics
```

## Analysis Output Structure

### Ollama Lead Analysis
```json
{
    "business_overview": "2-3 sentence business summary",
    "pain_points": ["challenge 1", "challenge 2", "challenge 3"],
    "industry_positioning": "market position assessment",
    "technology_adoption": "basic|medium|advanced",
    "employee_count_estimate": "small|medium|large",
    "revenue_assessment": "small|medium|high",
    "business_maturity": "startup|established|enterprise",
    "decision_maker_profile": "decision maker description",
    "engagement_strategy": "recommended approach",
    "automation_opportunities": ["opportunity 1", "opportunity 2"],
    "competitive_advantages": ["advantage 1", "advantage 2"],
    "growth_potential": "low|medium|high",
    "seasonal_factors": "seasonal considerations",
    "confidence_score": 85,
    "analysis_provider": "ollama_mistral7b"
}
```

### Email Generation Output
```json
{
    "success": true,
    "email_data": {
        "subject_lines": [
            "Enterprise HVAC automation for Austin Air Conditioning",
            "Michael Johnson - business automation consultation",
            "Scale operations with enterprise automation"
        ],
        "email_body": "Personalized consultant email content...",
        "consultant_positioning": true,
        "template_type": "consultant_introduction"
    },
    "ai_provider": "ollama_mistral7b"
}
```

## API Usage Examples

### Test Ollama Connection
```bash
curl -s http://localhost:5000/api/ollama/test-connection
```

### Analyze Lead with Ollama
```bash
curl -X POST http://localhost:5000/api/analyze-lead-ollama \
  -H "Content-Type: application/json" \
  -d '{"lead_id": 42}'
```

### Generate Email with Ollama
```bash
curl -X POST http://localhost:5000/api/generate-consultant-email-ollama \
  -H "Content-Type: application/json" \
  -d '{"lead_id": 42}'
```

### Compare AI Providers
```bash
curl -s http://localhost:5000/api/ai-provider-comparison/42
```

## Benefits of Dual AI Provider System

### Cost Optimization
- **OpenAI GPT-4o**: Premium analysis for high-value leads
- **Local Ollama**: Cost-free processing for bulk analysis
- **Smart Routing**: Choose provider based on requirements

### Performance Benefits
- **Local Processing**: No API latency for Ollama
- **Redundancy**: Fallback when one provider unavailable
- **Comparison**: Validate results across providers

### Privacy & Security
- **Local Processing**: Sensitive data stays on-premises with Ollama
- **Compliance**: Enhanced data privacy for regulated industries
- **Control**: Full control over local AI processing

## Fallback System

When Ollama is unavailable, the system automatically:
1. Falls back to existing OpenAI-based analysis
2. Falls back to consultant approach templates
3. Provides degraded service rather than failure
4. Logs warnings for monitoring

## Next Steps

### Immediate (Setup Required)
1. **Install Ollama service** on the server
2. **Download Mistral 7B model** 
3. **Configure Ollama to start automatically**
4. **Test connection and model availability**

### Future Enhancements
1. **Model Selection** - Support multiple Ollama models
2. **Load Balancing** - Distribute requests between providers  
3. **Performance Monitoring** - Track provider response times
4. **Smart Routing** - Choose provider based on lead complexity

## Troubleshooting

### Common Issues
1. **"Failed to connect to Ollama"**
   - Ensure Ollama service is running: `ollama serve`
   - Check port accessibility: `curl http://localhost:11434`

2. **"Model not found"**
   - Download model: `ollama pull mistral:7b`
   - Verify: `ollama list`

3. **JSON parsing errors**
   - Ollama responses may need cleaning
   - Fallback system handles malformed responses

### Monitoring
- Check Ollama logs: `ollama serve --verbose`
- Monitor API response times
- Track fallback usage frequency

The Ollama integration provides LeadNGN with powerful local AI capabilities, reducing costs while maintaining high-quality analysis. Once Ollama is installed and configured, the system will provide seamless dual AI provider support with automatic failover and cost optimization.