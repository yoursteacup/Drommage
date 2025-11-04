#!/usr/bin/env python3
"""
Test UI display of analyses
"""

import time
from drommage.core.llm_analyzer import LLMAnalyzer, AnalysisLevel
from drommage.core.analysis_queue import AnalysisQueue, AnalysisTask

def test_ui_display():
    print("🖥️ Testing UI Analysis Display...")
    
    # Create analyzer and queue
    analyzer = LLMAnalyzer()
    if not analyzer.ollama_available:
        print("⚠️  Ollama not available - can't test full flow")
        return
    
    queue = AnalysisQueue(analyzer)
    queue.start()
    
    # Test data
    old_text = "def calculate():\n    return 42"
    new_text = "def calculate_total():\n    return 42 + 8\n    # Added calculation logic"
    context = "test→ui: Function enhancement"
    
    # Track results
    results = {}
    
    def brief_callback(result):
        results['brief'] = result
        print(f"✅ Brief complete: {result.summary[:60]}...")
    
    def detailed_callback(result):
        results['detailed'] = result  
        print(f"✅ Detailed complete: {result.summary[:60]}...")
    
    # Create tasks
    brief_task = AnalysisTask(
        id="test_brief",
        old_text=old_text,
        new_text=new_text,
        context=context,
        level=AnalysisLevel.BRIEF,
        callback=brief_callback
    )
    
    detailed_task = AnalysisTask(
        id="test_detailed", 
        old_text=old_text,
        new_text=new_text,
        context=context,
        level=AnalysisLevel.DETAILED,
        callback=detailed_callback
    )
    
    # Add to queue
    print("📤 Adding tasks to queue...")
    queue.add_task(brief_task)
    queue.add_task(detailed_task)
    
    # Wait for completion
    print("⏳ Waiting for analyses...")
    start_time = time.time()
    while len(results) < 2 and time.time() - start_time < 30:
        time.sleep(0.5)
    
    queue.stop()
    
    if len(results) == 2:
        print("\n✅ Both analyses completed successfully!")
        print(f"Brief: {results['brief'].summary}")
        print(f"Detailed: {results['detailed'].summary}")
        print("\nThe UI should now be able to display these results properly.")
    else:
        print(f"\n❌ Only {len(results)}/2 analyses completed")

if __name__ == "__main__":
    test_ui_display()