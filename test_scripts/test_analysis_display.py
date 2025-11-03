#!/usr/bin/env python3
"""
Test script to show what analysis results should look like
"""

from core.llm_analyzer import DiffAnalysis, ChangeType

def show_analysis_example():
    print("\n" + "="*60)
    print(" DRommage v8 - Deep Analysis Display Example")
    print("="*60)
    
    # Example analysis result
    analysis = DiffAnalysis(
        summary="Updated API documentation to include authentication requirements and rate limiting information",
        change_type=ChangeType.FEATURE,
        impact_level="medium",
        details="The documentation was enhanced with critical security and performance information. Authentication requirements were added to ensure proper API usage. Rate limiting documentation helps developers understand usage constraints.",
        risks=["Existing integrations may need updates", "Breaking changes for unauthenticated users"],
        recommendations=["Update client libraries", "Add migration guide", "Notify API consumers"],
        confidence=0.85
    )
    
    print("\n🔍 Deep Analysis")
    print("-" * 40)
    
    # Change type and impact
    print(f"\n{analysis.change_type.value} Type: {analysis.change_type.name}")
    
    impact_bars = {"low": "▁▁▁", "medium": "▃▃▃", "high": "▇▇▇"}
    bars = impact_bars.get(analysis.impact_level, "▁▁▁")
    print(f"Impact: {bars} {analysis.impact_level}")
    
    # Summary
    print("\n📋 Summary:")
    print(f"  {analysis.summary}")
    
    # Details
    if analysis.details:
        print("\n📝 Details:")
        # Word wrap at 50 chars for demo
        words = analysis.details.split()
        line = ""
        for word in words:
            if len(line) + len(word) > 50:
                print(f"  {line}")
                line = word
            else:
                line = f"{line} {word}" if line else word
        if line:
            print(f"  {line}")
    
    # Risks
    if analysis.risks:
        print("\n⚠️  Risks:")
        for risk in analysis.risks:
            print(f"  • {risk}")
    
    # Recommendations
    if analysis.recommendations:
        print("\n💡 Recommendations:")
        for rec in analysis.recommendations:
            print(f"  • {rec}")
    
    print("\n" + "-"*40)
    print("Press ESC to return")
    
    print("\n" + "="*60)
    print("This is what should appear in the Deep Analysis panel")
    print("="*60 + "\n")

if __name__ == "__main__":
    show_analysis_example()