"""
DRommage - AI-Powered Git Commit Analysis

DR (Доктор) + ommage (оммаж к Videodrome) = инструмент для понимания своих git коммитов через ретроспективу

Understanding what you were doing through git retrospection.
"""

__version__ = "1.0.2"
__author__ = "DRommage Contributors"

from .core.engine import DRommageEngine
from .core.analysis import AnalysisMode, AnalysisResult
from .core.providers import ProviderManager
from .core.prompts import PromptManager

__all__ = [
    "DRommageEngine",
    "AnalysisMode", 
    "AnalysisResult",
    "ProviderManager",
    "PromptManager"
]