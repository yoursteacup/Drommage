#!/usr/bin/env python3
"""
Quick test to verify DRommage components work
"""

from drommage.core.git_integration import GitIntegration
from drommage.core.analysis_queue import AnalysisQueue
from drommage.core.llm_analyzer import LLMAnalyzer

def test_git_integration():
    print("🔍 Testing Git Integration...")
    git = GitIntegration()
    
    print(f"   Is git repo: {git.is_git_repo()}")
    
    if git.is_git_repo():
        commits = git.get_recent_commits(limit=5)
        print(f"   Found {len(commits)} commits")
        
        if commits:
            latest = commits[0]
            print(f"   Latest: {latest.short_hash} - {latest.message[:50]}")
            
            if len(commits) > 1:
                diff = git.get_commit_diff(commits[1].hash, commits[0].hash)
                if diff:
                    print(f"   Diff stats: {diff.stats}")
                    print(f"   Files changed: {len(diff.files)}")

def test_analysis_queue():
    print("\n🔄 Testing Analysis Queue...")
    llm = LLMAnalyzer()
    queue = AnalysisQueue(llm)
    
    print(f"   LLM available: {llm.ollama_available}")
    print(f"   Queue size: {queue.get_queue_size()}")
    
    queue.start()
    print("   ✅ Queue started")
    
    queue.stop()
    print("   🛑 Queue stopped")

if __name__ == "__main__":
    print("🚀 DRommage Component Test\n")
    
    try:
        test_git_integration()
        test_analysis_queue()
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()