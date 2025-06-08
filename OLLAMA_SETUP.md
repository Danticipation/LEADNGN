# LeadNGN Local AI Setup with Ollama

LeadNGN now uses local Ollama Llama2:13b for AI-powered lead intelligence instead of OpenAI. This provides complete privacy and no API costs.

## Installing Ollama

### 1. Download and Install Ollama
```bash
# On macOS
brew install ollama

# On Linux
curl -fsSL https://ollama.ai/install.sh | sh

# On Windows
# Download from https://ollama.ai/download
```

### 2. Start Ollama Service
```bash
# Start the Ollama service
ollama serve
```

### 3. Download Llama2:13b Model
```bash
# This will download the 13B parameter model (about 7GB)
ollama pull llama2:13b
```

### 4. Run the Model
```bash
# Start the model in interactive mode
ollama run llama2:13b
```

## Verifying Setup

### Test Ollama API
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test model generation
curl http://localhost:11434/api/generate -d '{
  "model": "llama2:13b",
  "prompt": "Analyze this business: HVAC company in Dallas, Texas",
  "stream": false
}'
```

## Using AI Features in LeadNGN

Once Ollama is running with llama2:13b, these features become available:

### 1. AI Lead Insights
- Analyzes prospect data and business context
- Identifies pain points and opportunities
- Provides priority scoring and recommendations
- Suggests optimal contact methods and timing

### 2. Personalized Outreach Generation
- Creates customized email content
- References industry-specific challenges
- Tailors messaging to company location and size
- Generates compelling subject lines and calls-to-action

### 3. Company Research Intelligence
- Analyzes website content and technology stack
- Identifies digital maturity indicators
- Assesses contact accessibility and professionalism
- Provides industry-specific context

## AI-Powered Workflow

1. **Scrape Leads**: Use the scraping system to find prospects
2. **Generate Insights**: Click "Generate AI Insights" for analysis
3. **Research Company**: Get comprehensive business intelligence
4. **Create Outreach**: Generate personalized email content
5. **Follow Up**: Use recommendations for optimal timing

## Troubleshooting

### Ollama Not Connected
If you see "Local Ollama LLM not available" errors:

1. Ensure Ollama service is running: `ollama serve`
2. Verify model is downloaded: `ollama list`
3. Check the model is running: `ollama run llama2:13b`
4. Test API endpoint: `curl http://localhost:11434/api/tags`

### Model Performance
- Llama2:13b requires about 8GB RAM
- First responses may be slower as the model loads
- Subsequent requests are faster with model cached

### Alternative Models
You can use other models by updating `rag_system_ollama.py`:
```python
self.model_name = "llama2:7b"  # Smaller, faster model
self.model_name = "codellama:13b"  # For technical analysis
```

## Benefits of Local AI

✅ **Complete Privacy**: Your lead data never leaves your system
✅ **No API Costs**: No per-request charges or monthly fees
✅ **Offline Capability**: Works without internet connection
✅ **Customizable**: Fine-tune models for your specific needs
✅ **No Rate Limits**: Process as many leads as needed