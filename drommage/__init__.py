"""
DRommage - Intelligent Documentation Version Control

A revolutionary documentation versioning system that combines git-style 
region tracking with LLM-powered semantic analysis.
"""

__version__ = "1.0.0"
__author__ = "Claude Code"

from .core.diff_tracker import GitDiffEngine
from .core.region_analyzer import RegionIndex
from .core.interface import DocTUIView
from .core.llm_analyzer import LLMAnalyzer, AnalysisLevel, DiffAnalysis, ChangeType

__all__ = [
    "GitDiffEngine",
    "RegionIndex", 
    "DocTUIView",
    "LLMAnalyzer",
    "AnalysisLevel",
    "DiffAnalysis",
    "ChangeType"
]