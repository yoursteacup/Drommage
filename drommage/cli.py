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
    # Check if first argument is a subcommand
    import sys
    subcommands = {'config', 'cache', 'analyze', 'prompts'}
    
    # If no args or first arg is not a subcommand, treat as analysis
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] not in subcommands):
        return run_legacy_analysis()
    
    # Parse with subcommands
    parser = argparse.ArgumentParser(
        description="DRommage - Git commit analysis with LLM-powered insights"
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Main analysis command (default)
    analyze_parser = subparsers.add_parser('analyze', help='Analyze commits (default)')
    _add_analysis_args(analyze_parser)
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure LLM providers')
    config_parser.add_argument('--repo', default='.', help='Repository path')
    
    # Cache command  
    cache_parser = subparsers.add_parser('cache', help='Manage analysis cache')
    cache_parser.add_argument('action', choices=['clear', 'stats', 'cleanup'], help='Cache action')
    cache_parser.add_argument('--repo', default='.', help='Repository path')
    cache_parser.add_argument('--mode', choices=['pat', 'brief', 'deep'], help='Specific mode to clear')
    
    # Prompts command
    prompts_parser = subparsers.add_parser('prompts', help='Manage prompt templates')
    prompts_parser.add_argument('action', choices=['list', 'show', 'categories'], help='Prompts action')
    prompts_parser.add_argument('--name', help='Prompt template name (for show action)')
    prompts_parser.add_argument('--category', help='Filter by category (for list action)')
    prompts_parser.add_argument('--repo', default='.', help='Repository path')
    
    args = parser.parse_args()
    
    # Handle subcommands
    if args.command == 'config':
        return run_config_interface(args)
    elif args.command == 'cache':
        return run_cache_command(args)
    elif args.command == 'prompts':
        return run_prompts_command(args)
    elif args.command == 'analyze' or args.command is None:
        # Default behavior - analysis
        if args.command is None:
            # No subcommand - parse as analysis with original args
            parser = argparse.ArgumentParser()
            _add_analysis_args(parser)
            args = parser.parse_args()
            return run_analysis_command(args)
        else:
            return run_analysis_command(args)
    else:
        parser.print_help()
        return 1


def _add_analysis_args(parser):
    """Add analysis arguments to parser"""
    
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
        "--prompt",
        help="Use custom prompt template (e.g. 'brief_security', 'deep_code_review')"
    )
    
    parser.add_argument(
        "--custom-prompt",
        help="Use custom prompt text directly"
    )
    
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="List available prompt templates"
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


def run_analysis_command(args) -> int:
    """Run analysis command"""
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


def run_legacy_analysis() -> int:
    """Run analysis with legacy argument parsing (no subcommand)"""
    parser = argparse.ArgumentParser(
        description="DRommage - Git commit analysis with LLM-powered insights"
    )
    _add_analysis_args(parser)
    args = parser.parse_args()
    return run_analysis_command(args)


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


def run_config_interface(args) -> int:
    """Run configuration interface"""
    try:
        from .core.config_tui import ConfigTUI
        
        print("🔧 Launching configuration interface...\n")
        config_tui = ConfigTUI(args.repo)
        config_tui.run()
        
        return 0
    except Exception as e:
        print(f"❌ Configuration interface failed: {e}")
        return 1


def run_cache_command(args) -> int:
    """Run cache management command"""
    try:
        engine = DRommageEngine(args.repo)
        
        if args.action == "clear":
            # Map CLI mode to AnalysisMode if specified
            mode = None
            if args.mode:
                mode_mapping = {"pat": "pattern", "brief": "brief", "deep": "deep"}
                mode = AnalysisMode(mode_mapping[args.mode])
            
            cleared = engine.clear_cache(mode=mode)
            print(f"🧹 Cleared {cleared} cache entries")
            
        elif args.action == "stats":
            stats = engine.get_cache_stats()
            print(f"📊 Cache statistics:")
            print(f"   Total entries: {stats.get('total_entries', 0)}")
            print(f"   Database size: {stats.get('db_size', 'unknown')}")
            print(f"   Cache location: {stats.get('cache_path', 'unknown')}")
            
        elif args.action == "cleanup":
            cleaned = engine.cleanup_cache()
            print(f"🗑️  Cleaned up {cleaned} old cache versions")
            
        return 0
        
    except Exception as e:
        print(f"❌ Cache command failed: {e}")
        return 1


def run_prompts_command(args) -> int:
    """Run prompts management command"""
    try:
        engine = DRommageEngine(args.repo)
        
        if args.action == "list":
            templates = engine.get_prompt_templates()
            categories = engine.get_prompt_categories()
            
            if args.category:
                # Filter by category
                if args.category not in categories:
                    print(f"❌ Category '{args.category}' not found")
                    print(f"Available categories: {', '.join(categories)}")
                    return 1
                
                filtered_templates = {name: info for name, info in templates.items() 
                                    if info['category'] == args.category}
                print(f"📝 Prompt templates in category '{args.category}':")
                for name, info in filtered_templates.items():
                    print(f"   • {name}: {info['description']}")
            else:
                # List all templates by category
                print("📝 Available prompt templates:")
                for category in categories:
                    print(f"\n  {category.upper()}:")
                    cat_templates = {name: info for name, info in templates.items() 
                                   if info['category'] == category}
                    for name, info in cat_templates.items():
                        print(f"    • {name}: {info['description']}")
                        
        elif args.action == "show":
            if not args.name:
                print("❌ --name required for show action")
                return 1
                
            templates = engine.get_prompt_templates()
            if args.name not in templates:
                print(f"❌ Prompt template '{args.name}' not found")
                print(f"Available templates: {', '.join(templates.keys())}")
                return 1
                
            template_info = templates[args.name]
            print(f"📝 Prompt template: {args.name}")
            print(f"   Description: {template_info['description']}")
            print(f"   Category: {template_info['category']}")
            print(f"   Variables: {', '.join(template_info['variables'])}")
            
            # Show example rendering if we have commits
            commits = engine.get_commits()
            if commits:
                example = engine.render_custom_prompt(args.name, commits[0].hash)
                if example:
                    print(f"\n   Example (latest commit):")
                    print("   " + "\n   ".join(example.split('\n')[:10]))
                    if len(example.split('\n')) > 10:
                        print("   ... (truncated)")
                        
        elif args.action == "categories":
            categories = engine.get_prompt_categories()
            print("📂 Available prompt categories:")
            for category in categories:
                count = len([t for t in engine.get_prompt_templates().values() 
                           if t['category'] == category])
                print(f"   • {category} ({count} templates)")
                
        return 0
        
    except Exception as e:
        print(f"❌ Prompts command failed: {e}")
        return 1


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