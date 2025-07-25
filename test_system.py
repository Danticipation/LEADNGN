#!/usr/bin/env python3
"""
Test script for LeadNgN system with real lead scraping and AI analysis
"""

import sys
import os
import requests
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ollama_connection():
    """Test if Ollama is running and accessible"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print("✓ Ollama service is running")
            return True
        else:
            print("✗ Ollama service not responding properly")
            return False
    except Exception as e:
        print(f"✗ Ollama connection failed: {e}")
        return False

def test_ollama_model():
    """Test Llama2:13b model generation"""
    try:
        test_prompt = "Analyze this business: HVAC company in Dallas, Texas. Provide insights in JSON format."
        
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama2:13b',
                'prompt': test_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,
                    'top_p': 0.9
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '')
            print("✓ Llama2:13b model is responding")
            print(f"   Sample response: {generated_text[:100]}...")
            return True
        else:
            print(f"✗ Model generation failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        return False

def test_web_scraping():
    """Test web scraping functionality"""
    try:
        import trafilatura
        import requests
        from bs4 import BeautifulSoup
        
        # Test basic web scraping
        test_url = "https://httpbin.org/html"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            if soup.find('title'):
                print("✓ Web scraping libraries working")
                return True
        
        print("✗ Web scraping test failed")
        return False
    except Exception as e:
        print(f"✗ Web scraping test error: {e}")
        return False

def test_database_connection():
    """Test database connectivity"""
    try:
        # Import Flask app and test database
        from app import app, db
        
        with app.app_context():
            # Test database connection
            with db.engine.connect() as connection:
                connection.execute(db.text('SELECT 1'))
            print("✓ Database connection working")
            return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def create_test_lead():
    """Create a test lead for AI analysis"""
    try:
        from app import app, db
        from models import Lead
        
        with app.app_context():
            # Create test HVAC lead
            test_lead = Lead(
                company_name="Dallas Heating & Air",
                industry="HVAC",
                location="Dallas, TX",
                contact_name="John Smith",
                email="john@dallasheatingair.com",
                phone="(214) 555-0123",
                website="https://dallasheatingair.com",
                quality_score=85,
                source="test_system"
            )
            
            db.session.add(test_lead)
            db.session.commit()
            
            print(f"✓ Created test lead: {test_lead.company_name} (ID: {test_lead.id})")
            return test_lead.id
    except Exception as e:
        print(f"✗ Test lead creation failed: {e}")
        return None

def test_ai_analysis(lead_id):
    """Test AI analysis on a lead"""
    try:
        from app import app
        from rag_system_ollama import rag_system
        from models import Lead
        
        with app.app_context():
            lead = Lead.query.get(lead_id)
            if not lead:
                print("✗ Test lead not found")
                return False
            
            print(f"Testing AI analysis on {lead.company_name}...")
            
            # Test lead insights generation
            insights = rag_system.generate_lead_insights(lead)
            
            if 'error' in insights:
                print(f"✗ AI analysis failed: {insights['error']}")
                return False
            
            print("✓ AI lead insights generated successfully")
            print(f"   Priority: {insights.get('lead_priority', 'unknown')}")
            print(f"   Key insights: {len(insights.get('key_insights', []))} items")
            print(f"   Pain points: {len(insights.get('pain_points', []))} items")
            
            # Test outreach generation
            outreach = rag_system.generate_personalized_outreach(lead)
            
            if 'error' in outreach:
                print(f"✗ Outreach generation failed: {outreach['error']}")
                return False
            
            print("✓ Personalized outreach generated successfully")
            print(f"   Subject: {outreach.get('subject', 'N/A')}")
            
            return True
    except Exception as e:
        print(f"✗ AI analysis test failed: {e}")
        return False

def main():
    """Run complete system test"""
    print("LeadNGN System Test - Local AI with Ollama")
    print("=" * 50)
    
    # Test all components
    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("Llama2:13b Model", test_ollama_model),
        ("Web Scraping", test_web_scraping),
        ("Database Connection", test_database_connection),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if not test_func():
            all_passed = False
    
    if all_passed:
        print(f"\n✓ All basic tests passed! Creating test lead...")
        lead_id = create_test_lead()
        
        if lead_id:
            print(f"\n✓ Testing AI analysis...")
            if test_ai_analysis(lead_id):
                print(f"\n🎉 Complete LeadNGN system test PASSED!")
                print(f"   - Local Ollama AI is working")
                print(f"   - Lead analysis and outreach generation functional")
                print(f"   - Ready for real lead scraping and AI intelligence")
            else:
                print(f"\n✗ AI analysis test failed")
        else:
            print(f"\n✗ Test lead creation failed")
    else:
        print(f"\n✗ Some basic tests failed - check configuration")

if __name__ == "__main__":
    main()