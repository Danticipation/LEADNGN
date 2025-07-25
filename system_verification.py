#!/usr/bin/env python3
"""
LeadNgN System Verification
Comprehensive testing of all system components and connections
"""

import requests
import json
import time
from datetime import datetime

class SystemVerification:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.errors = []
        
    def log_result(self, test_name, status, details=None, error=None):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details,
            'error': str(error) if error else None
        }
        self.results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        
        if error:
            self.errors.append(result)
            print(f"   Error: {error}")
        elif details:
            print(f"   Details: {details}")
    
    def test_endpoint(self, endpoint, method="GET", data=None, expected_keys=None):
        """Test API endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    
                    # Check expected keys if provided
                    if expected_keys:
                        missing_keys = [key for key in expected_keys if key not in json_data]
                        if missing_keys:
                            return "WARN", f"Missing keys: {missing_keys}", json_data
                    
                    return "PASS", f"Status: {response.status_code}", json_data
                except json.JSONDecodeError:
                    return "WARN", f"Status: {response.status_code} (Non-JSON response)", response.text[:100]
            else:
                return "FAIL", f"Status: {response.status_code}", response.text[:200]
                
        except requests.exceptions.RequestException as e:
            return "FAIL", None, e
        except Exception as e:
            return "FAIL", None, e
    
    def run_core_api_tests(self):
        """Test core API endpoints"""
        print("\n🔍 TESTING CORE API ENDPOINTS")
        print("=" * 50)
        
        # Dashboard stats
        status, details, data = self.test_endpoint("/api/dashboard/stats", expected_keys=['total_leads', 'new_leads'])
        self.log_result("Dashboard Stats API", status, details)
        
        # Leads list
        status, details, data = self.test_endpoint("/api/leads")
        self.log_result("Leads List API", status, details)
        
        # Specific lead (ID 42)
        status, details, data = self.test_endpoint("/api/leads/42", expected_keys=['id', 'company_name'])
        self.log_result("Lead Details API", status, details)
        
        # Lead health score
        status, details, data = self.test_endpoint("/api/leads/42/health-score", expected_keys=['health_score', 'health_status'])
        self.log_result("Lead Health Score API", status, details)
        
        return len([r for r in self.results[-4:] if r['status'] == 'PASS'])
    
    def run_ai_integration_tests(self):
        """Test AI integration endpoints"""
        print("\n🤖 TESTING AI INTEGRATION")
        print("=" * 50)
        
        # OpenAI analysis
        status, details, data = self.test_endpoint("/api/analyze-lead", method="POST", 
                                                  data={"lead_id": 42}, 
                                                  expected_keys=['analysis', 'provider'])
        self.log_result("OpenAI Lead Analysis", status, details)
        
        # Ollama connection test
        status, details, data = self.test_endpoint("/api/ollama/test-connection", expected_keys=['status', 'available'])
        self.log_result("Ollama Connection Test", status, details)
        
        # Ollama analysis (with fallback)
        status, details, data = self.test_endpoint("/api/analyze-lead-ollama", method="POST",
                                                  data={"lead_id": 42},
                                                  expected_keys=['analysis', 'provider'])
        self.log_result("Ollama Lead Analysis", status, details)
        
        # AI provider comparison
        status, details, data = self.test_endpoint("/api/ai-provider-comparison/42", 
                                                  expected_keys=['openai_analysis', 'ollama_analysis'])
        self.log_result("AI Provider Comparison", status, details)
        
        return len([r for r in self.results[-4:] if r['status'] == 'PASS'])
    
    def run_advanced_features_tests(self):
        """Test advanced features"""
        print("\n🚀 TESTING ADVANCED FEATURES")
        print("=" * 50)
        
        # Competitive analysis
        status, details, data = self.test_endpoint("/api/competitive-analysis/42", expected_keys=['analysis', 'competitors'])
        self.log_result("Competitive Analysis", status, details)
        
        # Email template generation
        status, details, data = self.test_endpoint("/api/generate-email-template", method="POST",
                                                  data={"lead_id": 42, "template_type": "introduction"})
        self.log_result("Email Template Generation", status, details)
        
        # Consultant email generation
        status, details, data = self.test_endpoint("/api/generate-consultant-email", method="POST",
                                                  data={"lead_id": 42})
        self.log_result("Consultant Email Generation", status, details)
        
        # Analytics dashboard
        status, details, data = self.test_endpoint("/api/analytics/dashboard", expected_keys=['metrics', 'charts'])
        self.log_result("Analytics Dashboard", status, details)
        
        return len([r for r in self.results[-4:] if r['status'] == 'PASS'])
    
    def run_email_tracking_tests(self):
        """Test email tracking system"""
        print("\n📧 TESTING EMAIL TRACKING SYSTEM")
        print("=" * 50)
        
        # Email tracking stats
        status, details, data = self.test_endpoint("/api/email-tracking-stats", expected_keys=['summary', 'emails'])
        self.log_result("Email Tracking Stats", status, details)
        
        # Lead email performance
        status, details, data = self.test_endpoint("/api/leads/42/email-performance", expected_keys=['performance', 'timeline'])
        self.log_result("Lead Email Performance", status, details)
        
        return len([r for r in self.results[-2:] if r['status'] == 'PASS'])
    
    def run_data_validation_tests(self):
        """Test data validation and quality systems"""
        print("\n🔍 TESTING DATA VALIDATION")
        print("=" * 50)
        
        # GDPR compliance check
        status, details, data = self.test_endpoint("/api/leads/42/gdpr-compliance")
        self.log_result("GDPR Compliance Check", status, details)
        
        # Email validation
        status, details, data = self.test_endpoint("/api/validate-email", method="POST",
                                                  data={"email": "test@example.com"})
        self.log_result("Email Validation", status, details)
        
        # Bulk operations
        status, details, data = self.test_endpoint("/api/bulk-operations/validate", method="POST",
                                                  data={"lead_ids": [42]})
        self.log_result("Bulk Operations", status, details)
        
        return len([r for r in self.results[-3:] if r['status'] == 'PASS'])
    
    def generate_report(self):
        """Generate comprehensive system report"""
        print("\n" + "=" * 60)
        print("🎯 LEADNGN SYSTEM VERIFICATION REPORT")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.results if r['status'] == 'FAIL'])
        warning_tests = len([r for r in self.results if r['status'] == 'WARN'])
        
        print(f"📊 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   ⚠️ Warnings: {warning_tests}")
        print(f"   🎯 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if self.errors:
            print(f"\n🚨 CRITICAL ISSUES ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error['test']}: {error['error']}")
        
        # System status
        if passed_tests >= total_tests * 0.8:
            print(f"\n🟢 SYSTEM STATUS: OPERATIONAL")
            print("   Most features are working correctly.")
        elif passed_tests >= total_tests * 0.6:
            print(f"\n🟡 SYSTEM STATUS: PARTIAL")
            print("   Core features working, some issues need attention.")
        else:
            print(f"\n🔴 SYSTEM STATUS: CRITICAL")
            print("   Multiple systems need immediate attention.")
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'warnings': warning_tests,
            'success_rate': passed_tests/total_tests*100,
            'status': 'OPERATIONAL' if passed_tests >= total_tests * 0.8 else 'PARTIAL' if passed_tests >= total_tests * 0.6 else 'CRITICAL'
        }
    
    def run_full_verification(self):
        """Run complete system verification"""
        print("🚀 STARTING LEADNGN SYSTEM VERIFICATION")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test suites
        core_passes = self.run_core_api_tests()
        ai_passes = self.run_ai_integration_tests()
        advanced_passes = self.run_advanced_features_tests()
        email_passes = self.run_email_tracking_tests()
        validation_passes = self.run_data_validation_tests()
        
        # Generate final report
        report = self.generate_report()
        
        return report

def main():
    """Main verification function"""
    verifier = SystemVerification()
    report = verifier.run_full_verification()
    
    # Save results to file
    with open('system_verification_results.json', 'w') as f:
        json.dump({
            'report': report,
            'detailed_results': verifier.results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: system_verification_results.json")
    
    return report

if __name__ == "__main__":
    main()