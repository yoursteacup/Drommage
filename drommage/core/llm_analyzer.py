"""
LLM Analyzer for intelligent diff interpretation
Uses Ollama for local LLM inference
"""

import json
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import sqlite3
from pathlib import Path

class AnalysisLevel(Enum):
    BRIEF = "brief"       # 1 line summary
    DETAILED = "detailed" # Paragraph with context  
    TECHNICAL = "technical" # Full analysis with examples

class ChangeType(Enum):
    DOCUMENTATION = "📝"  # Documentation changes
    FEATURE = "🚀"       # New features
    REFACTOR = "🔧"      # Code restructuring
    BUGFIX = "🐛"        # Bug fixes
    PERFORMANCE = "⚡"    # Performance improvements
    SECURITY = "🔒"      # Security updates
    BREAKING = "💥"      # Breaking changes
    MINOR = "✨"         # Minor improvements

@dataclass
class DiffAnalysis:
    """Analysis result for a diff"""
    summary: str
    change_type: ChangeType
    impact_level: str  # low/medium/high
    details: Optional[str] = None
    risks: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    confidence: float = 0.0

class LLMAnalyzer:
    def __init__(self, model: str = "mistral:latest", cache_dir: str = ".llm_cache"):
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "analysis_cache.db"
        self._init_cache_db()
        
        # Check if Ollama is available
        self.ollama_available = self._check_ollama()
        
    def _check_ollama(self) -> bool:
        """Check if Ollama is installed and running"""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=2
            )
            if result.returncode == 0:
                # Check if our model is available
                if self.model.split(":")[0] in result.stdout:
                    return True
                else:
                    print(f"⚠️  Model {self.model} not found. Pulling...")
                    self._pull_model()
                    return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️  Ollama not available. Install from https://ollama.ai")
            return False
    
    def _pull_model(self):
        """Pull the required model"""
        try:
            subprocess.run(["ollama", "pull", self.model], check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to pull model {self.model}")
    
    def _init_cache_db(self):
        """Initialize SQLite cache for LLM responses"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_cache (
                diff_hash TEXT PRIMARY KEY,
                level TEXT,
                analysis TEXT,
                timestamp INTEGER
            )
        """)
        conn.commit()
        conn.close()
    
    def _get_cached_analysis(self, diff_hash: str, level: AnalysisLevel) -> Optional[Dict]:
        """Retrieve cached analysis if available"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT analysis FROM analysis_cache WHERE diff_hash = ? AND level = ?",
            (diff_hash, level.value)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def _cache_analysis(self, diff_hash: str, level: AnalysisLevel, analysis: Dict):
        """Cache analysis result"""
        # Convert enums to strings for JSON serialization
        cache_data = {
            "summary": analysis.get("summary", ""),
            "change_type": analysis.get("change_type", ChangeType.MINOR).name if isinstance(analysis.get("change_type"), ChangeType) else analysis.get("change_type"),
            "impact_level": analysis.get("impact_level", "low"),
            "details": analysis.get("details"),
            "risks": analysis.get("risks"),
            "recommendations": analysis.get("recommendations"),
            "confidence": analysis.get("confidence", 0.0)
        }
        
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO analysis_cache (diff_hash, level, analysis, timestamp) VALUES (?, ?, ?, ?)",
            (diff_hash, level.value, json.dumps(cache_data), int(time.time()))
        )
        conn.commit()
        conn.close()
    
    def _call_ollama(self, prompt: str, status_callback=None) -> Optional[str]:
        """Call Ollama API for inference with status updates"""
        if not self.ollama_available:
            return None
        
        try:
            # Report status
            if status_callback:
                status_callback("🤖 Starting LLM inference...")
            
            start_time = time.time()
            
            # Use Popen for real-time monitoring
            process = subprocess.Popen(
                ["ollama", "run", self.model],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send prompt and get response
            stdout, stderr = process.communicate(input=prompt, timeout=30)
            
            elapsed = time.time() - start_time
            
            if status_callback:
                status_callback(f"✅ Analysis complete ({elapsed:.1f}s)")
            
            if process.returncode == 0:
                return stdout.strip()
            return None
            
        except subprocess.TimeoutExpired:
            if status_callback:
                status_callback("⏱️ LLM timeout (30s)")
            return None
        except Exception as e:
            if status_callback:
                status_callback(f"❌ LLM error: {str(e)[:50]}")
            return None
    
    def analyze_diff(self, 
                    old_text: str, 
                    new_text: str, 
                    context: str = "",
                    level: AnalysisLevel = AnalysisLevel.BRIEF,
                    status_callback=None) -> DiffAnalysis:
        """Analyze a diff between two text versions"""
        
        # Create hash for caching
        diff_content = f"{old_text}|||{new_text}|||{context}"
        diff_hash = hashlib.sha256(diff_content.encode()).hexdigest()
        
        # Check cache first
        cached = self._get_cached_analysis(diff_hash, level)
        if cached:
            if status_callback:
                status_callback("📦 Using cached analysis")
            return self._parse_analysis(cached)
        
        # Report analysis details
        if status_callback:
            lines_added = new_text.count('\n') - old_text.count('\n')
            chars_diff = len(new_text) - len(old_text)
            status_callback(f"📊 Analyzing: {abs(lines_added)} lines, {abs(chars_diff)} chars diff")
        
        # Generate prompt based on level
        prompt = self._generate_prompt(old_text, new_text, context, level)
        prompt_size = len(prompt)
        
        if status_callback:
            status_callback(f"📝 Prompt size: {prompt_size} chars, Level: {level.value}")
        
        # Get LLM response
        response = self._call_ollama(prompt, status_callback)
        
        if response:
            analysis = self._parse_llm_response(response, level)
            # Cache the result (convert to dict properly)
            analysis_dict = {
                "summary": analysis.summary,
                "change_type": analysis.change_type,
                "impact_level": analysis.impact_level,
                "details": analysis.details,
                "risks": analysis.risks,
                "recommendations": analysis.recommendations,
                "confidence": analysis.confidence
            }
            self._cache_analysis(diff_hash, level, analysis_dict)
            return analysis
        else:
            # Fallback to simple diff analysis
            return self._fallback_analysis(old_text, new_text)
    
    def _generate_prompt(self, old_text: str, new_text: str, context: str, level: AnalysisLevel) -> str:
        """Generate prompt for LLM based on analysis level"""
        
        if level == AnalysisLevel.BRIEF:
            prompt = f"""Analyze this text change and provide a ONE LINE summary (max 80 chars):

OLD: {old_text[:500]}
NEW: {new_text[:500]}

Respond with ONLY the summary line, no explanation."""
        
        elif level == AnalysisLevel.DETAILED:
            prompt = f"""Analyze this documentation change:

OLD VERSION:
{old_text[:1000]}

NEW VERSION:
{new_text[:1000]}

CONTEXT: {context}

Provide a detailed JSON analysis with:
{{
  "Summary": "one line summary",
  "Type of change": "documentation|feature|bugfix|refactor|performance|security",
  "Impact level": "low|medium|high",
  "What specifically changed and why it matters": "detailed explanation (2-3 sentences)",
  "Risks": ["potential risk 1", "potential risk 2"],
  "Recommendations": ["recommendation 1", "recommendation 2"]
}}

Consider risks like compatibility issues, breaking changes, missing information.
Consider recommendations like next steps, improvements, documentation needs."""
        
        else:  # TECHNICAL
            prompt = f"""Technical analysis of documentation change:

OLD VERSION:
{old_text}

NEW VERSION:
{new_text}

CONTEXT: {context}

Provide detailed analysis as JSON:
{{
  "summary": "one line summary",
  "change_type": "documentation|feature|bugfix|refactor|performance|security|breaking",
  "impact_level": "low|medium|high",
  "details": "detailed explanation of changes",
  "risks": ["list", "of", "potential", "risks"],
  "recommendations": ["list", "of", "recommendations"],
  "semantic_changes": "what changed in meaning, not just text"
}}"""
        
        return prompt
    
    def _parse_llm_response(self, response: str, level: AnalysisLevel) -> DiffAnalysis:
        """Parse LLM response into DiffAnalysis object"""
        
        if level == AnalysisLevel.BRIEF:
            # Simple one-line response
            return DiffAnalysis(
                summary=response[:80],
                change_type=ChangeType.MINOR,
                impact_level="low",
                confidence=0.8
            )
        
        else:
            # Try to parse JSON response
            try:
                data = json.loads(response)
                
                # Handle different key formats (lowercase, Title Case, etc.)
                # Try multiple key variations
                summary = (data.get("summary") or 
                          data.get("Summary") or 
                          data.get("1. Summary") or
                          "Changes detected")
                
                # Get change type from various possible keys
                change_type_str = (data.get("change_type") or 
                                  data.get("Type of change") or 
                                  data.get("2. Type of change") or
                                  data.get("type") or 
                                  "minor").lower()
                
                # Map change type
                type_map = {
                    "documentation": ChangeType.DOCUMENTATION,
                    "feature": ChangeType.FEATURE,
                    "bugfix": ChangeType.BUGFIX,
                    "refactor": ChangeType.REFACTOR,
                    "performance": ChangeType.PERFORMANCE,
                    "security": ChangeType.SECURITY,
                    "breaking": ChangeType.BREAKING
                }
                change_type = type_map.get(change_type_str, ChangeType.MINOR)
                
                # Get impact level
                impact = (data.get("impact_level") or 
                         data.get("Impact level") or 
                         data.get("3. Impact level") or
                         data.get("impact") or 
                         "low").lower()
                
                # Get details from various keys
                details = (data.get("details") or 
                          data.get("Details") or
                          data.get("What specifically changed and why it matters") or
                          data.get("4. What specifically changed and why it matters") or
                          data.get("semantic_changes"))
                
                # Get risks and recommendations
                risks = data.get("risks") or data.get("Risks")
                recommendations = data.get("recommendations") or data.get("Recommendations")
                
                return DiffAnalysis(
                    summary=summary,
                    change_type=change_type,
                    impact_level=impact,
                    details=details,
                    risks=risks,
                    recommendations=recommendations,
                    confidence=0.9
                )
            except json.JSONDecodeError:
                # Fallback for non-JSON response
                # Try to extract meaningful info from text response
                summary = response[:150] if response else "Analysis failed"
                
                # Try to detect change type from keywords
                change_type = ChangeType.MINOR
                response_lower = response.lower() if response else ""
                if "feature" in response_lower or "added" in response_lower:
                    change_type = ChangeType.FEATURE
                elif "fix" in response_lower or "bug" in response_lower:
                    change_type = ChangeType.BUGFIX
                elif "security" in response_lower:
                    change_type = ChangeType.SECURITY
                elif "breaking" in response_lower:
                    change_type = ChangeType.BREAKING
                elif "refactor" in response_lower:
                    change_type = ChangeType.REFACTOR
                elif "documentation" in response_lower:
                    change_type = ChangeType.DOCUMENTATION
                
                # For DETAILED level, create synthetic structure
                if level == AnalysisLevel.DETAILED:
                    lines = response.split('\n') if response else []
                    summary = lines[0][:150] if lines else "Analysis completed"
                    details = '\n'.join(lines[1:]) if len(lines) > 1 else response
                    
                    return DiffAnalysis(
                        summary=summary,
                        change_type=change_type,
                        impact_level="medium",
                        details=details,
                        risks=["Review changes carefully"],
                        recommendations=["Verify functionality after changes"],
                        confidence=0.6
                    )
                else:
                    return DiffAnalysis(
                        summary=summary,
                        change_type=change_type,
                        impact_level="low",
                        details=response,
                        confidence=0.5
                    )
    
    def _parse_analysis(self, cached: Dict) -> DiffAnalysis:
        """Parse cached analysis back to DiffAnalysis object"""
        change_type = ChangeType.MINOR
        for ct in ChangeType:
            if ct.name == cached.get("change_type", "MINOR"):
                change_type = ct
                break
                
        return DiffAnalysis(
            summary=cached.get("summary", ""),
            change_type=change_type,
            impact_level=cached.get("impact_level", "low"),
            details=cached.get("details"),
            risks=cached.get("risks"),
            recommendations=cached.get("recommendations"),
            confidence=cached.get("confidence", 0.0)
        )
    
    def _fallback_analysis(self, old_text: str, new_text: str) -> DiffAnalysis:
        """Simple fallback analysis without LLM"""
        old_lines = old_text.count('\n')
        new_lines = new_text.count('\n')
        
        if new_lines > old_lines:
            summary = f"Added {new_lines - old_lines} lines"
            change_type = ChangeType.FEATURE
        elif new_lines < old_lines:
            summary = f"Removed {old_lines - new_lines} lines"
            change_type = ChangeType.REFACTOR
        else:
            summary = "Modified content"
            change_type = ChangeType.MINOR
        
        # Detect common patterns
        if "API" in new_text and "API" not in old_text:
            change_type = ChangeType.FEATURE
            summary = "Added API documentation"
        elif "fix" in new_text.lower():
            change_type = ChangeType.BUGFIX
            summary = "Bug fix or correction"
        elif "security" in new_text.lower():
            change_type = ChangeType.SECURITY
            summary = "Security-related changes"
        
        return DiffAnalysis(
            summary=summary,
            change_type=change_type,
            impact_level="low",
            confidence=0.3
        )
    
    def analyze_region(self, region_history: List[Dict], level: AnalysisLevel = AnalysisLevel.BRIEF, status_callback=None) -> str:
        """Analyze the complete history of a region"""
        
        if not region_history:
            return "No history available"
        
        # Build context from history
        changes = []
        for entry in region_history:
            version = entry.get("version", "unknown")
            action = entry.get("action", "modified")
            changes.append(f"{version}: {action}")
        
        context = "Region evolution: " + " → ".join(changes)
        
        # Get the latest state
        latest = region_history[-1]
        if "new_lines" in latest:
            current_text = "\n".join(latest["new_lines"])
        elif "lines" in latest:
            current_text = "\n".join(latest["lines"])
        else:
            current_text = "Content unavailable"
        
        # Analyze evolution
        if len(region_history) > 1:
            first = region_history[0]
            if "lines" in first:
                original_text = "\n".join(first["lines"])
            else:
                original_text = ""
            
            analysis = self.analyze_diff(original_text, current_text, context, level, status_callback)
            return f"{analysis.change_type.value} {analysis.summary}"
        else:
            return f"✨ Region created in {region_history[0].get('version', 'unknown')}"
    
    def get_commit_message(self, analyses: List[DiffAnalysis]) -> str:
        """Generate a commit message from multiple analyses"""
        
        if not analyses:
            return "chore: Update documentation"
        
        # Group by change type
        by_type = {}
        for analysis in analyses:
            if analysis.change_type not in by_type:
                by_type[analysis.change_type] = []
            by_type[analysis.change_type].append(analysis.summary)
        
        # Pick the most significant change type
        priority = [
            ChangeType.BREAKING,
            ChangeType.SECURITY,
            ChangeType.FEATURE,
            ChangeType.BUGFIX,
            ChangeType.PERFORMANCE,
            ChangeType.REFACTOR,
            ChangeType.DOCUMENTATION,
            ChangeType.MINOR
        ]
        
        main_type = None
        for ct in priority:
            if ct in by_type:
                main_type = ct
                break
        
        if not main_type:
            return "chore: Update documentation"
        
        # Generate message
        type_prefixes = {
            ChangeType.BREAKING: "BREAKING CHANGE",
            ChangeType.SECURITY: "security",
            ChangeType.FEATURE: "feat",
            ChangeType.BUGFIX: "fix",
            ChangeType.PERFORMANCE: "perf",
            ChangeType.REFACTOR: "refactor",
            ChangeType.DOCUMENTATION: "docs",
            ChangeType.MINOR: "chore"
        }
        
        prefix = type_prefixes.get(main_type, "chore")
        summaries = by_type[main_type]
        
        if len(summaries) == 1:
            return f"{prefix}: {summaries[0]}"
        else:
            return f"{prefix}: {summaries[0]} and {len(summaries)-1} other changes"