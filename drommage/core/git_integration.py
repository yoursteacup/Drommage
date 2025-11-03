"""
Git integration - analyze real commit diffs instead of mock documents
"""

import subprocess
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GitCommit:
    """Represents a git commit"""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    files_changed: int
    insertions: int
    deletions: int

@dataclass 
class GitDiff:
    """Represents a diff between two commits"""
    from_commit: str
    to_commit: str
    files: List[str]
    diff_text: str
    stats: Dict[str, int]

class GitIntegration:
    """Integrates with git to get real commit data"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_recent_commits(self, limit: int = 20) -> List[GitCommit]:
        """Get recent commits from the repository"""
        if not self.is_git_repo():
            return []
        
        try:
            # Get commit info with pretty format
            cmd = [
                "git", "log", 
                f"--max-count={limit}",
                "--pretty=format:%H|%h|%s|%an|%ad|",
                "--date=short",
                "--numstat"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            return self._parse_commit_log(result.stdout)
            
        except Exception:
            return []
    
    def get_commit_diff(self, from_commit: str, to_commit: str, 
                       file_patterns: Optional[List[str]] = None) -> Optional[GitDiff]:
        """Get diff between two commits"""
        if not self.is_git_repo():
            return None
        
        try:
            # Build diff command
            cmd = ["git", "diff", f"{from_commit}..{to_commit}"]
            
            # Add file patterns if specified
            if file_patterns:
                cmd.append("--")
                cmd.extend(file_patterns)
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return None
            
            # Get changed files
            files_cmd = ["git", "diff", "--name-only", f"{from_commit}..{to_commit}"]
            if file_patterns:
                files_cmd.append("--")
                files_cmd.extend(file_patterns)
                
            files_result = subprocess.run(
                files_cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            files = files_result.stdout.strip().split('\n') if files_result.stdout.strip() else []
            
            # Get stats
            stats_cmd = ["git", "diff", "--numstat", f"{from_commit}..{to_commit}"]
            if file_patterns:
                stats_cmd.append("--")
                stats_cmd.extend(file_patterns)
                
            stats_result = subprocess.run(
                stats_cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            stats = self._parse_diff_stats(stats_result.stdout)
            
            return GitDiff(
                from_commit=from_commit,
                to_commit=to_commit,
                files=files,
                diff_text=result.stdout,
                stats=stats
            )
            
        except Exception:
            return None
    
    def get_file_content_at_commit(self, commit: str, file_path: str) -> Optional[str]:
        """Get file content at specific commit"""
        if not self.is_git_repo():
            return None
        
        try:
            result = subprocess.run(
                ["git", "show", f"{commit}:{file_path}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            return result.stdout if result.returncode == 0 else None
            
        except Exception:
            return None
    
    def get_repo_info(self) -> Dict[str, str]:
        """Get repository information"""
        if not self.is_git_repo():
            return {}
        
        info = {}
        
        try:
            # Get repo root
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info["root"] = result.stdout.strip()
            
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info["branch"] = result.stdout.strip()
            
            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info["remote"] = result.stdout.strip()
                
        except Exception:
            pass
        
        return info
    
    def _parse_commit_log(self, log_output: str) -> List[GitCommit]:
        """Parse git log output into GitCommit objects"""
        commits = []
        lines = log_output.strip().split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if '|' not in line:
                i += 1
                continue
            
            # Parse commit info line
            parts = line.split('|')
            if len(parts) < 5:
                i += 1
                continue
            
            hash_full, hash_short, message, author, date = parts[:5]
            
            # Parse numstat lines that follow
            insertions = deletions = files_changed = 0
            i += 1
            
            while i < len(lines) and lines[i] and '\t' in lines[i]:
                stat_parts = lines[i].split('\t')
                if len(stat_parts) >= 2:
                    try:
                        ins = int(stat_parts[0]) if stat_parts[0] != '-' else 0
                        dels = int(stat_parts[1]) if stat_parts[1] != '-' else 0
                        insertions += ins
                        deletions += dels
                        files_changed += 1
                    except ValueError:
                        pass
                i += 1
            
            commits.append(GitCommit(
                hash=hash_full,
                short_hash=hash_short,
                message=message,
                author=author,
                date=date,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions
            ))
        
        return commits
    
    def _parse_diff_stats(self, stats_output: str) -> Dict[str, int]:
        """Parse git diff --numstat output"""
        stats = {"insertions": 0, "deletions": 0, "files": 0}
        
        for line in stats_output.strip().split('\n'):
            if not line or '\t' not in line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 2:
                try:
                    ins = int(parts[0]) if parts[0] != '-' else 0
                    dels = int(parts[1]) if parts[1] != '-' else 0
                    stats["insertions"] += ins
                    stats["deletions"] += dels
                    stats["files"] += 1
                except ValueError:
                    pass
        
        return stats