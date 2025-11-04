#!/usr/bin/env python3
"""
Test JSON parser fix for markdown wrapped responses
"""

from drommage.core.llm_analyzer import LLMAnalyzer, AnalysisLevel

def test_json_parser():
    print("🧪 Testing JSON Parser...")
    
    analyzer = LLMAnalyzer()
    
    # Simulate markdown-wrapped JSON response (like from LLM)
    mock_response = '''```json
{
  "Summary": "Documentation update for DRommage debugging", 
  "Type of change": "documentation",
  "Impact level": "low",
  "What specifically changed and why it matters": "Added detailed debugging guide for DRommage",
  "Risks": ["Risk of misinterpretation", "Outdated information"],
  "Recommendations": ["Keep docs updated", "Add examples"]
}
```'''
    
    print(f"📄 Mock response length: {len(mock_response)}")
    print(f"📄 Starts with: {mock_response[:50]}...")
    
    try:
        result = analyzer._parse_llm_response(mock_response, AnalysisLevel.DETAILED)
        print(f"✅ Parsing SUCCESS!")
        print(f"   Summary: {result.summary}")
        print(f"   Type: {result.change_type}")
        print(f"   Impact: {result.impact_level}")
        print(f"   Details: {result.details[:50] if result.details else 'None'}...")
        print(f"   Risks: {len(result.risks) if result.risks else 0} items")
        print(f"   Recommendations: {len(result.recommendations) if result.recommendations else 0} items")
        
    except Exception as e:
        print(f"❌ Parsing FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_json_parser()