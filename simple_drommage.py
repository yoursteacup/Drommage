#!/usr/bin/env python3
"""
ПРОСТАЯ версия DRommage без сложного интерфейса
"""

import time
from drommage.core.git_integration import GitIntegration
from drommage.core.llm_analyzer import LLMAnalyzer, AnalysisLevel

def main():
    print("🚀 Simple DRommage - Git Commit Analyzer")
    
    # Инициализация
    git = GitIntegration()
    if not git.is_git_repo():
        print("❌ Not a git repository!")
        return
    
    commits = git.get_recent_commits(limit=10)
    if not commits:
        print("❌ No commits found!")
        return
    
    analyzer = LLMAnalyzer()
    if not analyzer.ollama_available:
        print("❌ Ollama not available!")
        return
    
    print(f"📚 Found {len(commits)} commits\n")
    
    # Показать коммиты
    for i, commit in enumerate(commits[:5]):
        print(f"{i+1}. {commit.short_hash} - {commit.message[:60]}")
    
    # Автоматический анализ первого коммита
    print("\n🔍 Auto-analyzing first commit...")
    analyze_commit(git, analyzer, commits, 0)

def analyze_commit(git, analyzer, commits, idx):
    current = commits[idx]
    
    if idx >= len(commits) - 1:
        print("⚠️ No previous commit to compare")
        return
    
    prev = commits[idx + 1]
    
    print(f"\n📊 Analyzing: {prev.short_hash} → {current.short_hash}")
    print(f"📝 Message: {current.message}")
    
    # Получить diff
    diff = git.get_commit_diff(prev.hash, current.hash)
    if not diff:
        print("❌ Could not get diff")
        return
    
    # Получить содержимое
    prev_content = ""
    curr_content = ""
    
    if diff.files:
        main_file = diff.files[0]
        print(f"📁 Main file: {main_file}")
        
        prev_file = git.get_file_content_at_commit(prev.hash, main_file)
        curr_file = git.get_file_content_at_commit(current.hash, main_file)
        
        if prev_file:
            prev_content = prev_file
        if curr_file:
            curr_content = curr_file
    
    if not curr_content:
        curr_content = diff.diff_text
    
    # Анализ
    print("🤖 Running LLM analysis...")
    
    try:
        result = analyzer.analyze_diff(
            prev_content,
            curr_content,
            f"{prev.short_hash}→{current.short_hash}: {current.message[:30]}",
            AnalysisLevel.BRIEF
        )
        
        print("\n✅ ANALYSIS COMPLETE!")
        print("=" * 60)
        print(f"🏷️  Type: {result.change_type.name}")
        print(f"📊 Impact: {result.impact_level}")
        print(f"📋 Summary:\n{result.summary}")
        
        if result.details:
            print(f"\n📝 Details:\n{result.details}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    main()