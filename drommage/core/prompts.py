"""
Custom prompts system for DRommage.
Allows users to customize analysis prompts for different use cases.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from .git_integration import GitCommit


@dataclass
class PromptTemplate:
    """Template for LLM prompts with variable substitution"""
    name: str
    description: str
    template: str
    variables: List[str]
    category: str = "general"  # general, security, performance, architecture, etc.
    
    def render(self, commit: GitCommit, **kwargs) -> str:
        """Render template with commit data and custom variables"""
        # Standard commit variables
        variables = {
            "commit_hash": commit.hash[:8],
            "commit_hash_full": commit.hash,
            "message": commit.message,
            "author": commit.author,
            "date": commit.date,
            "files_changed": commit.files_changed,
            "insertions": commit.insertions,
            "deletions": commit.deletions,
            "total_changes": commit.insertions + commit.deletions,
        }
        
        # Add custom variables
        variables.update(kwargs)
        
        try:
            return self.template.format(**variables)
        except KeyError as e:
            # Fallback if variable is missing
            return self.template.replace("{" + str(e).strip("'") + "}", f"[{e}]")


class PromptManager:
    """Manages collection of prompt templates"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.prompts_file = self.config_dir / "prompts.json"
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompt templates from JSON file"""
        if not self.prompts_file.exists():
            self._create_default_prompts()
        
        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.templates = {}
            for prompt_data in data.get("prompts", []):
                template = PromptTemplate(
                    name=prompt_data["name"],
                    description=prompt_data["description"],
                    template=prompt_data["template"],
                    variables=prompt_data.get("variables", []),
                    category=prompt_data.get("category", "general")
                )
                self.templates[template.name] = template
                
        except Exception as e:
            print(f"Error loading prompts: {e}")
            self._create_default_prompts()
    
    def _create_default_prompts(self):
        """Create default prompt templates"""
        default_prompts = {
            "prompts": [
                {
                    "name": "brief_default",
                    "description": "Standard brief analysis",
                    "category": "general",
                    "variables": ["commit_hash", "message", "files_changed", "insertions", "deletions"],
                    "template": """Analyze this git commit briefly in one sentence.

Commit: {commit_hash}
Message: {message}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Provide a concise one-line summary of what this commit does and its significance."""
                },
                {
                    "name": "brief_security",
                    "description": "Security-focused brief analysis",
                    "category": "security",
                    "variables": ["commit_hash", "message", "files_changed", "insertions", "deletions"],
                    "template": """Analyze this git commit for security implications in one sentence.

Commit: {commit_hash}
Message: {message}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Focus on: authentication, authorization, input validation, data exposure, cryptography, and other security concerns. Provide a brief security assessment."""
                },
                {
                    "name": "brief_performance",
                    "description": "Performance-focused brief analysis",
                    "category": "performance",
                    "variables": ["commit_hash", "message", "files_changed", "insertions", "deletions"],
                    "template": """Analyze this git commit for performance implications in one sentence.

Commit: {commit_hash}
Message: {message}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Focus on: algorithm complexity, database queries, caching, memory usage, network calls, and other performance factors. Provide a brief performance assessment."""
                },
                {
                    "name": "brief_architecture",
                    "description": "Architecture-focused brief analysis",
                    "category": "architecture",
                    "variables": ["commit_hash", "message", "files_changed", "insertions", "deletions"],
                    "template": """Analyze this git commit for architectural implications in one sentence.

Commit: {commit_hash}
Message: {message}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Focus on: design patterns, separation of concerns, modularity, dependencies, coupling, and architectural decisions. Provide a brief architectural assessment."""
                },
                {
                    "name": "deep_default",
                    "description": "Standard deep analysis",
                    "category": "general",
                    "variables": ["commit_hash", "message", "author", "date", "files_changed", "insertions", "deletions"],
                    "template": """Analyze this git commit in detail. Return JSON with keys: summary, details, risks, recommendations.

Commit: {commit_hash}
Message: {message}
Author: {author}
Date: {date}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Analyze:
1. What type of change this is (feature, bugfix, refactor, etc.)
2. Potential impact and risks
3. Code quality implications
4. Recommendations for improvement

Return valid JSON format:
{{
  "summary": "Brief one-line summary",
  "details": "Detailed explanation of the changes",
  "risks": ["risk1", "risk2"],
  "recommendations": ["rec1", "rec2"]
}}"""
                },
                {
                    "name": "deep_security_audit",
                    "description": "Comprehensive security audit",
                    "category": "security",
                    "variables": ["commit_hash", "message", "author", "date", "files_changed", "insertions", "deletions"],
                    "template": """Perform a comprehensive security audit of this git commit. Return JSON with security-focused analysis.

Commit: {commit_hash}
Message: {message}
Author: {author}
Date: {date}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Security Analysis Framework:
1. Authentication & Authorization changes
2. Input validation and sanitization
3. Data exposure and privacy concerns
4. Cryptographic implementations
5. Dependency security
6. Infrastructure security
7. Business logic vulnerabilities

Return valid JSON format:
{{
  "summary": "Security assessment summary",
  "details": "Detailed security analysis",
  "risks": ["security risk 1", "security risk 2"],
  "recommendations": ["security recommendation 1", "security recommendation 2"],
  "security_score": "HIGH/MEDIUM/LOW risk level",
  "owasp_categories": ["A01", "A02", "etc if applicable"]
}}"""
                },
                {
                    "name": "deep_code_review",
                    "description": "Detailed code review analysis",
                    "category": "quality",
                    "variables": ["commit_hash", "message", "author", "date", "files_changed", "insertions", "deletions"],
                    "template": """Perform a detailed code review of this git commit. Return JSON with comprehensive code quality analysis.

Commit: {commit_hash}
Message: {message}
Author: {author}
Date: {date}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Code Review Criteria:
1. Code style and conventions
2. Logic and algorithm efficiency
3. Error handling and edge cases
4. Test coverage implications
5. Documentation quality
6. Maintainability and readability
7. Best practices adherence

Return valid JSON format:
{{
  "summary": "Code review summary",
  "details": "Detailed code quality analysis",
  "risks": ["code quality issue 1", "code quality issue 2"],
  "recommendations": ["improvement 1", "improvement 2"],
  "quality_score": "1-10 scale",
  "categories": {{"style": "rating", "logic": "rating", "maintainability": "rating"}}
}}"""
                },
                {
                    "name": "deep_business_impact",
                    "description": "Business impact analysis",
                    "category": "business",
                    "variables": ["commit_hash", "message", "author", "date", "files_changed", "insertions", "deletions"],
                    "template": """Analyze the business impact of this git commit. Return JSON with business-focused analysis.

Commit: {commit_hash}
Message: {message}
Author: {author}
Date: {date}
Files changed: {files_changed}
Lines: +{insertions}, -{deletions}

Business Analysis Framework:
1. User experience impact
2. Feature completeness
3. Business process changes
4. Revenue/cost implications
5. Compliance and regulatory impact
6. Stakeholder communication needs
7. Release and deployment considerations

Return valid JSON format:
{{
  "summary": "Business impact summary",
  "details": "Detailed business analysis",
  "risks": ["business risk 1", "business risk 2"],
  "recommendations": ["business recommendation 1", "business recommendation 2"],
  "impact_level": "HIGH/MEDIUM/LOW business impact",
  "stakeholders": ["stakeholder1", "stakeholder2"]
}}"""
                }
            ]
        }
        
        self.config_dir.mkdir(exist_ok=True)
        with open(self.prompts_file, 'w', encoding='utf-8') as f:
            json.dump(default_prompts, f, indent=2, ensure_ascii=False)
        
        # Load the created defaults
        self._load_prompts()
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get prompt template by name"""
        return self.templates.get(name)
    
    def get_templates_by_category(self, category: str) -> List[PromptTemplate]:
        """Get all templates in a category"""
        return [t for t in self.templates.values() if t.category == category]
    
    def get_all_templates(self) -> Dict[str, PromptTemplate]:
        """Get all templates"""
        return self.templates.copy()
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        categories = set(t.category for t in self.templates.values())
        return sorted(list(categories))
    
    def add_template(self, template: PromptTemplate) -> bool:
        """Add new template"""
        try:
            self.templates[template.name] = template
            self._save_prompts()
            return True
        except Exception:
            return False
    
    def remove_template(self, name: str) -> bool:
        """Remove template"""
        try:
            if name in self.templates:
                del self.templates[name]
                self._save_prompts()
                return True
            return False
        except Exception:
            return False
    
    def _save_prompts(self):
        """Save templates to file"""
        data = {
            "prompts": [
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "variables": t.variables,
                    "template": t.template
                }
                for t in self.templates.values()
            ]
        }
        
        with open(self.prompts_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def render_prompt(self, template_name: str, commit: GitCommit, **kwargs) -> Optional[str]:
        """Render a prompt template with commit data"""
        template = self.get_template(template_name)
        if template:
            return template.render(commit, **kwargs)
        return None
    
    def get_prompt_info(self) -> Dict[str, Any]:
        """Get information about loaded prompts"""
        categories = {}
        for template in self.templates.values():
            if template.category not in categories:
                categories[template.category] = []
            categories[template.category].append({
                "name": template.name,
                "description": template.description,
                "variables": template.variables
            })
        
        return {
            "total_prompts": len(self.templates),
            "categories": categories,
            "config_file": str(self.prompts_file)
        }