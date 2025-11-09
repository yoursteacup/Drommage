"""
Core analysis data structures and enums for DRommage.
Defines the fundamental types used across the application.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


class AnalysisMode(Enum):
    """Analysis modes with specific order: PAT → BRIEF → DEEP"""
    PAT = "pattern"     # Pattern analysis (no LLM required)
    BRIEF = "brief"     # Brief LLM analysis  
    DEEP = "deep"       # Deep LLM analysis with details


class ChangeType(Enum):
    """Types of changes detected in commits"""
    FEATURE = "🚀 Feature"
    BUGFIX = "🐛 Bug Fix"
    DOCS = "📝 Documentation" 
    REFACTOR = "♻️ Refactor"
    SECURITY = "🔒 Security"
    BREAKING = "🚨 Breaking"
    CLEANUP = "🗑️ Cleanup"
    PERFORMANCE = "⚡ Performance"
    TEST = "✅ Test"
    CONFIG = "⚙️ Configuration"
    UNKNOWN = "📊 Change"


@dataclass
class AnalysisResult:
    """Result of commit analysis"""
    mode: AnalysisMode
    commit_hash: str
    provider: str
    version: int
    summary: str
    details: Optional[str] = None
    risks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"{self.mode.value}: {self.summary}"


@dataclass 
class CommitStats:
    """Statistics about a commit's changes"""
    files_added: int = 0
    files_modified: int = 0  
    files_deleted: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    
    @property
    def total_files(self) -> int:
        return self.files_added + self.files_modified + self.files_deleted
    
    @property
    def add_delete_ratio(self) -> float:
        if self.lines_deleted == 0:
            return float('inf') if self.lines_added > 0 else 0
        return self.lines_added / self.lines_deleted
    
    @property 
    def magnitude_description(self) -> str:
        """Human readable description of change magnitude"""
        ratio = self.add_delete_ratio
        
        if ratio == float('inf'):
            return "Pure addition"
        elif ratio > 5:
            return "Major addition" 
        elif ratio > 2:
            return "Expansion"
        elif 0.5 < ratio < 2:
            return "Balanced change"
        elif ratio < 0.2:
            return "Major cleanup"
        else:
            return "Reduction"