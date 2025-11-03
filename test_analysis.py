#!/usr/bin/env python3
"""
Test LLM analysis engine
"""

from drommage.core.llm_analyzer import LLMAnalyzer, AnalysisLevel

def test_llm_analyzer():
    print("🤖 Testing LLM Analyzer...")
    
    analyzer = LLMAnalyzer()
    print(f"   Ollama available: {analyzer.ollama_available}")
    
    if not analyzer.ollama_available:
        print("   ⚠️  Skipping analysis test - Ollama not available")
        return
    
    # Test with simple diff
    old_text = "def hello():\n    print('hello')"
    new_text = "def hello_world():\n    print('hello world')\n    print('goodbye')"
    context = "Function rename and expansion"
    
    print("   📝 Testing brief analysis...")
    try:
        brief_result = analyzer.analyze_diff(old_text, new_text, context, AnalysisLevel.BRIEF)
        print(f"   ✅ Brief analysis: {brief_result.summary[:50]}...")
        print(f"   ✅ Change type: {brief_result.change_type}")
        print(f"   ✅ Impact: {brief_result.impact_level}")
    except Exception as e:
        print(f"   ❌ Brief analysis failed: {e}")
    
    print("   📊 Testing deep analysis...")
    try:
        deep_result = analyzer.analyze_diff(old_text, new_text, context, AnalysisLevel.DETAILED)
        print(f"   ✅ Deep analysis: {deep_result.summary[:50]}...")
        print(f"   ✅ Details: {len(deep_result.details) if deep_result.details else 0} chars")
        print(f"   ✅ Risks: {len(deep_result.risks) if deep_result.risks else 0} items")
        print(f"   ✅ Recommendations: {len(deep_result.recommendations) if deep_result.recommendations else 0} items")
    except Exception as e:
        print(f"   ❌ Deep analysis failed: {e}")

if __name__ == "__main__":
    print("🚀 LLM Analysis Engine Test\n")
    
    try:
        test_llm_analyzer()
        print("\n✅ Analysis test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()