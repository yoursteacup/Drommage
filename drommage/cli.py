"""
CLI entry point for DRommage.
Handles argument parsing and interface selection.
"""

import argparse
import sys
from pathlib import Path
from .core.engine import DRommageEngine
from .core.analysis import AnalysisMode


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="DRommage - Git commit analysis with LLM-powered insights"
    )
    
    parser.add_argument(
        "--repo", 
        default=".",
        help="Repository path (default: current directory)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["tui", "cli"],
        default="tui", 
        help="Interface mode (default: tui)"
    )
    
    parser.add_argument(
        "--commit",
        help="Analyze specific commit (hash or HEAD)"
    )
    
    parser.add_argument(
        "--analysis",
        choices=["pat", "brief", "deep"],
        default="pat",
        help="Analysis type (default: pat)"
    )
    
    parser.add_argument(
        "--last",
        type=int,
        help="Analyze last N commits"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for CLI mode (default: text)"
    )
    
    args = parser.parse_args()
    
    # Create engine
    try:
        engine = DRommageEngine(args.repo)
    except Exception as e:
        print(f"❌ Error initializing DRommage: {e}")
        return 1
    
    # Check if git repository
    if not engine.is_git_repository():
        print("❌ Not a git repository!")
        print("   Run 'git init' or navigate to a git repository.")
        return 1
    
    # Show repository info
    repo_info = engine.get_repository_info()
    print(f"📁 Repository: {repo_info.get('root', 'unknown')}")
    print(f"🌿 Branch: {repo_info.get('branch', 'unknown')}")
    
    # Load commits
    commits = engine.load_commits(50)
    if not commits:
        print("❌ No commits found!")
        return 1
        
    print(f"📚 Found {len(commits)} commits")
    
    # Run interface based on mode
    if args.mode == "tui":
        return run_tui_interface(engine)
    elif args.mode == "cli":
        return run_cli_interface(engine, args)
    
    return 0


def run_tui_interface(engine: DRommageEngine) -> int:
    """Run TUI interface"""
    try:
        # Import and run TUI with new engine integration
        from .core.interface import DocTUIView
        
        print("\n📺 Launching TUI interface...\n")
        tui = DocTUIView(engine)  # ✅ Use new constructor
        tui.run()
        
        return 0
    except Exception as e:
        print(f"❌ TUI interface failed: {e}")
        print("Try running with --mode=cli")
        return 1


def run_cli_interface(engine: DRommageEngine, args) -> int:
    """Run CLI batch interface"""
    # Map CLI shortcuts to AnalysisMode values
    mode_mapping = {
        "pat": "pattern",
        "brief": "brief", 
        "deep": "deep"
    }
    analysis_mode = AnalysisMode(mode_mapping[args.analysis])
    
    if args.commit:
        # Analyze specific commit
        if args.commit == "HEAD":
            commits = engine.get_commits()
            commit_hash = commits[0].hash if commits else None
        else:
            commit_hash = args.commit
            
        if not commit_hash:
            print("❌ No commits found")
            return 1
            
        result = engine.analyze_commit(commit_hash, analysis_mode)
        if result:
            print_analysis_result(result, args.format)
        else:
            print(f"❌ Could not analyze commit {commit_hash}")
            return 1
            
    elif args.last:
        # Analyze last N commits
        commits = engine.get_commits()[:args.last]
        
        for commit in commits:
            result = engine.analyze_commit(commit.hash, analysis_mode)
            if result:
                print_analysis_result(result, args.format)
            else:
                print(f"❌ Could not analyze commit {commit.hash}")
                
    else:
        # Default: show recent commits with basic info
        commits = engine.get_commits()[:10]
        
        print("\n📊 Recent commits:")
        for i, commit in enumerate(commits):
            result = engine.analyze_commit(commit.hash, AnalysisMode.PAT)
            summary = result.summary if result else "No analysis"
            print(f"{i+1:2}. {commit.hash[:8]} - {summary}")
    
    return 0


def print_analysis_result(result, format_type: str = "text"):
    """Print analysis result in specified format"""
    if format_type == "json":
        import json
        data = {
            'commit_hash': result.commit_hash,
            'mode': result.mode.value,
            'provider': result.provider,
            'summary': result.summary,
            'details': result.details,
            'risks': result.risks,
            'recommendations': result.recommendations,
            'metadata': result.metadata
        }
        print(json.dumps(data, indent=2))
    else:
        # Text format
        print(f"\n📊 {result.commit_hash[:8]} ({result.mode.value}):")
        print(f"   {result.summary}")
        
        if result.details:
            print(f"   Details: {result.details}")
            
        if result.risks:
            print(f"   ⚠️  Risks: {', '.join(result.risks)}")
            
        if result.recommendations:
            print(f"   💡 Recommendations: {', '.join(result.recommendations)}")


if __name__ == "__main__":
    sys.exit(main())