"""
DRommageEngine - Core business logic separated from UI.
Main API for commit analysis functionality.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict
from .git_integration import GitIntegration, GitCommit
from .analysis import AnalysisMode, AnalysisResult, ChangeType, CommitStats
from .cache import AnalysisCache
from .pattern_analyzer import PatternAnalyzer
from .providers import ProviderManager
from .prompts import PromptManager


class DRommageEngine:
    """
    Core business logic engine for DRommage.
    Handles commit loading, analysis coordination, and caching.
    Independent of any UI implementation.
    """
    
    def __init__(self, repo_path: str = ".", cache_dir: Optional[str] = None):
        """
        Initialize the DRommage engine.
        
        Args:
            repo_path: Path to git repository (default: current directory)
            cache_dir: Cache directory path (default: .drommage in repo)
        """
        self.repo_path = Path(repo_path).resolve()
        self.git = GitIntegration(str(self.repo_path))
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = self.repo_path / ".drommage"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self._cache = AnalysisCache(self.cache_dir)
        self._pattern_analyzer = PatternAnalyzer()
        self._prompt_manager = PromptManager(self.cache_dir)
        self._provider_manager = ProviderManager(self.cache_dir, self._prompt_manager)
        
        # State
        self._commits: List[GitCommit] = []
        self._current_analyses: Dict[str, Dict[AnalysisMode, AnalysisResult]] = {}
    
    def is_git_repository(self) -> bool:
        """Check if current directory is a git repository"""
        return self.git.is_git_repo()
    
    def get_repository_info(self) -> Dict[str, str]:
        """Get repository information"""
        if not self.is_git_repository():
            return {}
        return self.git.get_repo_info()
    
    def load_commits(self, limit: int = 50) -> List[GitCommit]:
        """
        Load recent commits from git repository.
        
        Args:
            limit: Maximum number of commits to load
            
        Returns:
            List of GitCommit objects
        """
        if not self.is_git_repository():
            return []
            
        self._commits = self.git.get_recent_commits(limit)
        return self._commits
    
    def get_commits(self) -> List[GitCommit]:
        """Get currently loaded commits"""
        return self._commits.copy()
    
    def find_commit(self, commit_hash: str) -> Optional[GitCommit]:
        """Find commit by hash in loaded commits"""
        for commit in self._commits:
            if commit.hash.startswith(commit_hash):
                return commit
        return None
    
    def get_commit_stats(self, commit: GitCommit) -> CommitStats:
        """Calculate statistics for a commit"""
        return CommitStats(
            files_added=len(commit.added_files),
            files_modified=len(commit.modified_files),
            files_deleted=len(commit.deleted_files),
            lines_added=commit.insertions,
            lines_deleted=commit.deletions
        )
    
    def analyze_commit(self, commit_hash: str, mode: AnalysisMode) -> Optional[AnalysisResult]:
        """
        Analyze a commit using specified mode.
        
        Args:
            commit_hash: Git commit hash
            mode: Analysis mode (PAT/BRIEF/DEEP)
            
        Returns:
            AnalysisResult or None if commit not found
        """
        commit = self.find_commit(commit_hash)
        if not commit:
            return None
            
        # Check cache first
        cached = self._cache.get_analysis(commit_hash, mode)
        if cached:
            return cached
        
        # Perform analysis based on mode
        result = None
        if mode == AnalysisMode.PAT:
            result = self._pattern_analyzer.analyze(commit)
        elif mode == AnalysisMode.BRIEF:
            result = self._analyze_llm_brief(commit)
        elif mode == AnalysisMode.DEEP:
            result = self._analyze_llm_deep(commit)
        
        # Cache the result
        if result:
            self._cache.store_analysis(result)
        
        return result
    
    def get_available_modes(self) -> List[AnalysisMode]:
        """
        Get list of analysis modes available in current environment.
        
        Returns:
            List of available AnalysisMode values
        """
        modes = [AnalysisMode.PAT]  # Pattern analysis always available
        
        # Check LLM availability
        if self._provider_manager.get_available_provider():
            modes.extend([AnalysisMode.BRIEF, AnalysisMode.DEEP])
        
        return modes
    
    def clear_cache(self, mode: Optional[AnalysisMode] = None, commit_hash: Optional[str] = None) -> int:
        """
        Clear analysis cache.
        
        Args:
            mode: Specific mode to clear, or None for all modes
            commit_hash: Specific commit to clear, or None for all commits
            
        Returns:
            Number of entries cleared
        """
        return self._cache.clear_cache(mode, commit_hash)
    
    def reanalyze_commit(self, commit_hash: str, mode: AnalysisMode) -> Optional[AnalysisResult]:
        """
        Force re-analysis of commit (bypass cache).
        
        Args:
            commit_hash: Git commit hash
            mode: Analysis mode
            
        Returns:
            Fresh AnalysisResult
        """
        # Clear cache entry first
        self._cache.clear_cache(mode, commit_hash)
        # Perform fresh analysis
        return self.analyze_commit(commit_hash, mode)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self._cache.get_cache_stats()
    
    def cleanup_cache(self, keep_versions: int = 3) -> int:
        """Clean up old cached analysis versions."""
        return self._cache.cleanup_old_versions(keep_versions)
    
    def get_provider_status(self) -> Dict:
        """Get status of all configured LLM providers."""
        providers = self._provider_manager.get_providers()
        return {
            "available_provider": bool(self._provider_manager.get_available_provider()),
            "providers": [
                {
                    "name": p.config.name,
                    "type": p.config.type,
                    "model": p.config.model,
                    "endpoint": p.config.endpoint,
                    "available": p.is_available(),
                    "priority": p.config.priority
                }
                for p in providers
            ]
        }
    
    def test_provider(self, provider_name: str) -> Dict:
        """Test specific provider."""
        return self._provider_manager.test_provider(provider_name)
    
    def _analyze_llm_brief(self, commit: GitCommit) -> AnalysisResult:
        """Analyze commit using brief LLM analysis"""
        provider = self._provider_manager.get_available_provider()
        if provider:
            result = provider.analyze_brief(commit)
            if result:
                return result
        
        # Fallback to placeholder
        return AnalysisResult(
            mode=AnalysisMode.BRIEF,
            commit_hash=commit.hash,
            provider="no_provider",
            version=1,
            summary="No LLM provider available. Configure with 'drommage config'"
        )
    
    def _analyze_llm_deep(self, commit: GitCommit) -> AnalysisResult:
        """Analyze commit using deep LLM analysis"""
        provider = self._provider_manager.get_available_provider()
        if provider:
            result = provider.analyze_deep(commit)
            if result:
                return result
        
        # Fallback to placeholder
        return AnalysisResult(
            mode=AnalysisMode.DEEP,
            commit_hash=commit.hash,
            provider="no_provider", 
            version=1,
            summary="No LLM provider available. Configure with 'drommage config'"
        )
    
    def _detect_change_type_basic(self, commit: GitCommit) -> ChangeType:
        """Basic change type detection from commit message"""
        message = commit.message.lower()
        
        # Conventional commits
        if message.startswith(('feat:', 'feature:')):
            return ChangeType.FEATURE
        elif message.startswith('fix:'):
            return ChangeType.BUGFIX
        elif message.startswith('docs:'):
            return ChangeType.DOCS
        elif message.startswith('refactor:'):
            return ChangeType.REFACTOR
        elif message.startswith('test:'):
            return ChangeType.TEST
        elif message.startswith('config:'):
            return ChangeType.CONFIG
            
        # Keyword detection
        if any(kw in message for kw in ['break', 'breaking', 'incompatible']):
            return ChangeType.BREAKING
        elif any(kw in message for kw in ['security', 'vulnerability', 'cve']):
            return ChangeType.SECURITY
        elif any(kw in message for kw in ['performance', 'optimize', 'speed']):
            return ChangeType.PERFORMANCE
        elif any(kw in message for kw in ['clean', 'remove', 'delete']):
            return ChangeType.CLEANUP
        elif any(kw in message for kw in ['add', 'implement', 'create']):
            return ChangeType.FEATURE
        elif any(kw in message for kw in ['fix', 'resolve', 'repair']):
            return ChangeType.BUGFIX
            
        return ChangeType.UNKNOWN
    
    def get_commit_by_hash(self, commit_hash: str) -> Optional[GitCommit]:
        """Get commit by hash"""
        for commit in self._commits:
            if commit.hash.startswith(commit_hash) or commit.hash == commit_hash:
                return commit
        return None
    
    # Prompt management methods
    def get_prompt_info(self) -> Dict:
        """Get information about loaded prompts"""
        return self._prompt_manager.get_prompt_info()
    
    def get_prompt_templates(self) -> Dict:
        """Get all prompt templates"""
        return {name: {
            "description": template.description,
            "category": template.category,
            "variables": template.variables
        } for name, template in self._prompt_manager.get_all_templates().items()}
    
    def get_prompt_categories(self) -> List[str]:
        """Get all prompt categories"""
        return self._prompt_manager.get_categories()
    
    def render_custom_prompt(self, template_name: str, commit_hash: str, **kwargs) -> Optional[str]:
        """Render a custom prompt template"""
        commit = self.get_commit_by_hash(commit_hash)
        if commit:
            return self._prompt_manager.render_prompt(template_name, commit, **kwargs)
        return None