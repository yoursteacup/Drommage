"""
Pattern-based commit analysis without LLM dependency.
Analyzes commits using file patterns, conventional commits, and diff metrics.
"""

import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from .analysis import AnalysisResult, AnalysisMode, ChangeType, CommitStats
from .git_integration import GitCommit


class PatternAnalyzer:
    """
    Analyzes commits using pattern matching and heuristics.
    Full-featured analysis mode that works without any LLM dependency.
    """
    
    def __init__(self):
        # File pattern definitions
        self.file_patterns = {
            'config': {
                'extensions': {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'},
                'names': {'dockerfile', 'makefile', 'rakefile', 'gruntfile', 'gulpfile'},
                'patterns': ['*config*', '*settings*', '*.env*', '*.docker*']
            },
            'docs': {
                'extensions': {'.md', '.rst', '.txt', '.adoc', '.tex'},
                'names': {'readme', 'changelog', 'license', 'todo', 'authors'},
                'patterns': ['docs/*', 'doc/*', '*.docs.*']
            },
            'tests': {
                'extensions': {'.test.py', '.spec.py', '.test.js', '.spec.js'},
                'patterns': ['test_*', '*_test.*', 'tests/*', 'spec/*', '__tests__/*'],
                'names': set()
            },
            'frontend': {
                'extensions': {'.js', '.jsx', '.ts', '.tsx', '.vue', '.html', '.css', '.scss', '.sass'},
                'patterns': ['src/*', 'public/*', 'static/*', 'assets/*'],
                'names': set()
            },
            'backend': {
                'extensions': {'.py', '.java', '.go', '.rs', '.php', '.rb', '.cs', '.cpp', '.c'},
                'patterns': ['src/*', 'lib/*', 'server/*', 'api/*'],
                'names': set()
            },
            'database': {
                'extensions': {'.sql', '.migration'},
                'patterns': ['*migration*', '*schema*', 'db/*', 'database/*'],
                'names': {'schema'}
            },
            'security': {
                'patterns': ['*auth*', '*security*', '*crypto*', '*password*', '*token*', '*key*'],
                'extensions': {'.pem', '.key', '.crt'},
                'names': set()
            }
        }
        
        # Risk indicators
        self.risk_patterns = {
            'breaking': [
                r'\bbreaking\s+change\b',
                r'\bapi\s+change\b', 
                r'\bincompatible\b',
                r'\bmajor\s+version\b',
                r'\bremove.*deprecated\b'
            ],
            'security': [
                r'\bsecurity\b',
                r'\bvuln\b',
                r'\bcve\b',
                r'\bauth\b',
                r'\bpassword\b',
                r'\btoken\b',
                r'\bpermission\b'
            ],
            'performance': [
                r'\bperformance\b',
                r'\boptimiz\b',
                r'\bslow\b',
                r'\bmemory\s+leak\b',
                r'\bcaching\b'
            ],
            'database': [
                r'\bmigration\b',
                r'\bschema\b',
                r'\bdatabase\b',
                r'\bindex\b',
                r'\btable\b'
            ]
        }
    
    def analyze(self, commit: GitCommit) -> AnalysisResult:
        """
        Perform comprehensive pattern analysis of commit.
        
        Args:
            commit: GitCommit object to analyze
            
        Returns:
            AnalysisResult with pattern analysis
        """
        # Get file categorization
        file_categories = self._categorize_files(commit)
        
        # Detect change type from message and files
        change_type = self._detect_change_type(commit, file_categories)
        
        # Calculate commit statistics
        stats = self._calculate_stats(commit)
        
        # Identify risks
        risks = self._identify_risks(commit, file_categories)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(commit, file_categories, risks)
        
        # Create summary
        summary = self._generate_summary(change_type, stats, file_categories)
        
        # Build details
        details = self._build_details(commit, file_categories, stats)
        
        return AnalysisResult(
            mode=AnalysisMode.PAT,
            commit_hash=commit.hash,
            provider="pattern_analyzer",
            version=1,
            summary=summary,
            details=details,
            risks=risks,
            recommendations=recommendations,
            metadata={
                'change_type': change_type.value,
                'file_categories': file_categories,
                'stats': {
                    'files_changed': commit.files_changed,
                    'insertions': commit.insertions,
                    'deletions': commit.deletions,
                    'magnitude': stats['magnitude'],
                    'complexity_score': stats['complexity_score']
                }
            }
        )
    
    def _categorize_files(self, commit: GitCommit) -> Dict[str, List[str]]:
        """Categorize changed files by type."""
        categories = {
            'config': [], 'docs': [], 'tests': [], 'frontend': [],
            'backend': [], 'database': [], 'security': [], 'unknown': []
        }
        
        # Get file list from commit (need to implement in GitCommit)
        files = getattr(commit, 'changed_files', [])
        if not files:
            # If no file list, try to extract from message
            files = self._extract_files_from_message(commit.message)
        
        for file_path in files:
            file_path_lower = file_path.lower()
            path_obj = Path(file_path_lower)
            
            categorized = False
            
            for category, patterns in self.file_patterns.items():
                # Check extensions
                if path_obj.suffix in patterns.get('extensions', set()):
                    categories[category].append(file_path)
                    categorized = True
                    break
                
                # Check names
                if path_obj.stem in patterns.get('names', set()):
                    categories[category].append(file_path)
                    categorized = True
                    break
                
                # Check patterns
                for pattern in patterns.get('patterns', []):
                    if self._matches_pattern(file_path_lower, pattern):
                        categories[category].append(file_path)
                        categorized = True
                        break
                
                if categorized:
                    break
            
            if not categorized:
                categories['unknown'].append(file_path)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _detect_change_type(self, commit: GitCommit, file_categories: Dict[str, List[str]]) -> ChangeType:
        """Detect change type from commit message and affected files."""
        message = commit.message.lower()
        
        # Check conventional commits format
        conventional_match = re.match(r'^(\w+)(?:\([^)]+\))?\s*:\s*(.+)', message)
        if conventional_match:
            conv_type = conventional_match.group(1)
            if conv_type in ['feat', 'feature']:
                return ChangeType.FEATURE
            elif conv_type == 'fix':
                return ChangeType.BUGFIX
            elif conv_type == 'docs':
                return ChangeType.DOCS
            elif conv_type == 'refactor':
                return ChangeType.REFACTOR
            elif conv_type in ['test', 'tests']:
                return ChangeType.TEST
            elif conv_type in ['config', 'conf', 'ci', 'build']:
                return ChangeType.CONFIG
            elif conv_type in ['perf', 'performance']:
                return ChangeType.PERFORMANCE
            elif conv_type in ['security', 'sec']:
                return ChangeType.SECURITY
        
        # Check for breaking change indicators
        for pattern in self.risk_patterns['breaking']:
            if re.search(pattern, message, re.IGNORECASE):
                return ChangeType.BREAKING
        
        # Check for security indicators
        for pattern in self.risk_patterns['security']:
            if re.search(pattern, message, re.IGNORECASE):
                return ChangeType.SECURITY
        
        # Check for performance indicators
        for pattern in self.risk_patterns['performance']:
            if re.search(pattern, message, re.IGNORECASE):
                return ChangeType.PERFORMANCE
        
        # Analyze based on file types
        if 'docs' in file_categories and len(file_categories) == 1:
            return ChangeType.DOCS
        
        if 'tests' in file_categories and len(file_categories) == 1:
            return ChangeType.TEST
        
        if 'config' in file_categories:
            return ChangeType.CONFIG
        
        if 'security' in file_categories:
            return ChangeType.SECURITY
        
        if 'database' in file_categories:
            return ChangeType.FEATURE  # Database changes usually add features
        
        # Check message keywords
        if any(kw in message for kw in ['add', 'implement', 'create', 'new']):
            return ChangeType.FEATURE
        elif any(kw in message for kw in ['fix', 'resolve', 'repair', 'correct']):
            return ChangeType.BUGFIX
        elif any(kw in message for kw in ['clean', 'remove', 'delete', 'unused']):
            return ChangeType.CLEANUP
        elif any(kw in message for kw in ['refactor', 'restructure', 'reorganize']):
            return ChangeType.REFACTOR
        
        return ChangeType.UNKNOWN
    
    def _calculate_stats(self, commit: GitCommit) -> Dict[str, any]:
        """Calculate comprehensive commit statistics."""
        # Basic stats
        total_lines = commit.insertions + commit.deletions
        change_ratio = commit.insertions / max(1, commit.deletions)
        
        # Magnitude classification
        if total_lines < 10:
            magnitude = "tiny"
        elif total_lines < 50:
            magnitude = "small"
        elif total_lines < 200:
            magnitude = "medium"
        elif total_lines < 500:
            magnitude = "large"
        else:
            magnitude = "massive"
        
        # Complexity score (0-100)
        # Based on files changed, lines changed, and change ratio
        complexity_score = min(100, (
            commit.files_changed * 10 +
            min(50, total_lines // 10) +
            min(20, abs(change_ratio - 1) * 10)
        ))
        
        return {
            'magnitude': magnitude,
            'complexity_score': complexity_score,
            'change_ratio': change_ratio,
            'total_lines': total_lines
        }
    
    def _identify_risks(self, commit: GitCommit, file_categories: Dict[str, List[str]]) -> List[str]:
        """Identify potential risks in the commit."""
        risks = []
        message = commit.message.lower()
        
        # Check message for risk patterns
        for risk_type, patterns in self.risk_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    if risk_type == 'breaking':
                        risks.append("Potential breaking change detected")
                    elif risk_type == 'security':
                        risks.append("Security-related changes require careful review")
                    elif risk_type == 'performance':
                        risks.append("Performance changes may affect system behavior")
                    elif risk_type == 'database':
                        risks.append("Database changes may require migration coordination")
                    break
        
        # File-based risk detection
        if 'security' in file_categories:
            risks.append("Security-sensitive files modified")
        
        if 'database' in file_categories:
            risks.append("Database schema changes detected")
        
        if 'config' in file_categories:
            risks.append("Configuration changes may affect deployment")
        
        # Size-based risks
        if commit.files_changed > 20:
            risks.append("Large number of files changed - review scope carefully")
        
        if commit.insertions + commit.deletions > 1000:
            risks.append("Massive code changes - consider breaking into smaller commits")
        
        return risks
    
    def _generate_recommendations(self, commit: GitCommit, file_categories: Dict[str, List[str]], risks: List[str]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Based on risks
        if any('breaking' in risk.lower() for risk in risks):
            recommendations.append("Update version number and changelog for breaking changes")
            recommendations.append("Ensure backward compatibility documentation is updated")
        
        if any('security' in risk.lower() for risk in risks):
            recommendations.append("Request security team review before deployment")
            recommendations.append("Verify no sensitive data is exposed in logs")
        
        if any('database' in risk.lower() for risk in risks):
            recommendations.append("Coordinate migration timing with deployment team")
            recommendations.append("Test migration on staging environment first")
        
        # Based on file categories
        if 'tests' in file_categories and len(file_categories) > 1:
            recommendations.append("Ensure test coverage adequately covers the changes")
        elif 'tests' not in file_categories and ('backend' in file_categories or 'frontend' in file_categories):
            recommendations.append("Consider adding tests for the new functionality")
        
        if 'docs' not in file_categories and commit.insertions > 100:
            recommendations.append("Consider updating documentation for significant changes")
        
        # Based on commit size
        if commit.files_changed > 15:
            recommendations.append("Consider breaking large changes into smaller, focused commits")
        
        if commit.insertions + commit.deletions > 500:
            recommendations.append("Large commits are harder to review - consider splitting")
        
        return recommendations
    
    def _generate_summary(self, change_type: ChangeType, stats: Dict, file_categories: Dict[str, List[str]]) -> str:
        """Generate concise summary of changes."""
        # Build file type summary
        if file_categories:
            primary_types = list(file_categories.keys())[:2]  # Top 2 categories
            type_desc = " & ".join(primary_types)
        else:
            type_desc = "code"
        
        # Build size description
        magnitude = stats['magnitude']
        if magnitude == "massive":
            size_desc = "Major"
        elif magnitude == "large":
            size_desc = "Significant"
        elif magnitude in ["medium", "small"]:
            size_desc = "Moderate"
        else:
            size_desc = "Minor"
        
        return f"{size_desc} {change_type.value.split()[1].lower()} in {type_desc}"
    
    def _build_details(self, commit: GitCommit, file_categories: Dict[str, List[str]], stats: Dict) -> str:
        """Build detailed analysis description."""
        details = []
        
        # Commit overview
        details.append(f"Commit modifies {commit.files_changed} files with {commit.insertions} additions and {commit.deletions} deletions")
        
        # File breakdown
        if file_categories:
            details.append("\nFile categories affected:")
            for category, files in file_categories.items():
                details.append(f"  • {category.title()}: {len(files)} files")
        
        # Complexity assessment
        complexity = stats['complexity_score']
        if complexity > 70:
            details.append(f"\nHigh complexity change (score: {complexity}/100) - requires careful review")
        elif complexity > 40:
            details.append(f"\nModerate complexity change (score: {complexity}/100)")
        else:
            details.append(f"\nLow complexity change (score: {complexity}/100)")
        
        # Change ratio analysis
        ratio = stats['change_ratio']
        if ratio > 5:
            details.append("Primarily additive change - likely new feature implementation")
        elif ratio < 0.2:
            details.append("Primarily deletion - likely cleanup or removal")
        else:
            details.append("Balanced additions and deletions - likely refactoring or modification")
        
        return "\n".join(details)
    
    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches glob-like pattern."""
        if '*' not in pattern:
            return pattern in file_path
        
        # Convert glob pattern to regex
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(regex_pattern, file_path))
    
    def _extract_files_from_message(self, message: str) -> List[str]:
        """Extract file names from commit message as fallback."""
        # Look for file-like patterns in commit message
        file_patterns = re.findall(r'\b\w+\.\w{1,4}\b', message)
        path_patterns = re.findall(r'\b\w+/[\w./]+\b', message)
        return file_patterns + path_patterns