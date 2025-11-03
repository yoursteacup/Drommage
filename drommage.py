#!/usr/bin/env python3
"""
DRommage v8 - LLM-Powered Documentation Analysis
Now with intelligent diff interpretation and enhanced UI
"""

from pathlib import Path
from drommage.core.diff_tracker import GitDiffEngine
from drommage.core.region_analyzer import RegionIndex
from drommage.core.interface import DocTUIView
from drommage.core.git_integration import GitIntegration

PROJECT_ROOT = Path(__file__).parent

def main():
    print("🚀 Starting DRommage - Git Commit Analyzer...")
    
    # Initialize git integration
    git = GitIntegration()
    
    if not git.is_git_repo():
        print("❌ Not a git repository!")
        print("   Run 'git init' or navigate to a git repository.")
        return
    
    # Get git repository info
    repo_info = git.get_repo_info()
    print(f"📁 Repository: {repo_info.get('root', 'unknown')}")
    print(f"🌿 Branch: {repo_info.get('branch', 'unknown')}")
    
    # Get recent commits
    print("📊 Loading git commits...")
    commits = git.get_recent_commits(limit=50)
    
    if not commits:
        print("❌ No commits found!")
        return
    
    print(f"📚 Found {len(commits)} commits")
    
    # Create engines (keeping for region tracking, but using git data)
    print("🧩 Building analysis engines...")
    engine = GitDiffEngine(docs_dir=None, versions=[])  # Empty for now
    region_index = RegionIndex(engine)
    
    # Check for Ollama
    print("🤖 Checking for LLM support...")
    try:
        import subprocess
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print("✅ Ollama detected - AI analysis available")
        else:
            print("⚠️  Ollama not found - install from https://ollama.ai for AI features")
    except:
        print("⚠️  Ollama not available - using basic analysis")
    
    # Launch TUI
    print("\n📺 Launching interface...\n")
    tui = DocTUIView(
        engine=engine, 
        region_index=region_index, 
        commits=commits,
        git_integration=git
    )
    tui.run()
    
    print("\n👋 Thanks for using DRommage!")

if __name__ == "__main__":
    main()