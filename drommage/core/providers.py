"""
LLM Provider system for DRommage.
Supports multiple LLM backends: Ollama, OpenAI, Custom HTTP endpoints.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from .analysis import AnalysisResult, AnalysisMode
from .git_integration import GitCommit


@dataclass
class ProviderConfig:
    """Configuration for LLM provider"""
    name: str
    type: str  # "ollama", "openai", "http"
    endpoint: str
    model: str
    priority: int = 1
    api_key_env: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: int = 30
    enabled: bool = True
    prompts: Optional[Dict[str, str]] = None  # Custom prompt mapping: {"brief": "brief_security", "deep": "deep_code_review"}


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: ProviderConfig, prompt_manager=None):
        self.config = config
        self._available = None
        self.prompt_manager = prompt_manager
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and working"""
        pass
    
    @abstractmethod
    def analyze_brief(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Perform brief analysis of commit"""
        pass
    
    @abstractmethod
    def analyze_deep(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Perform deep analysis of commit"""
        pass
    
    def get_cost_info(self) -> Dict[str, Any]:
        """Get cost information for this provider"""
        # Default cost info - can be overridden by specific providers
        costs = {
            "openai": {
                "gpt-4o": {"input": 0.00250, "output": 0.01000},  # per 1k tokens
                "gpt-4o-mini": {"input": 0.000150, "output": 0.000600},
                "gpt-4": {"input": 0.03000, "output": 0.06000},
                "gpt-3.5-turbo": {"input": 0.000500, "output": 0.001500}
            },
            "anthropic": {
                "claude-3-opus-20240229": {"input": 0.01500, "output": 0.07500},
                "claude-3-sonnet-20240229": {"input": 0.00300, "output": 0.01500},
                "claude-3-haiku-20240307": {"input": 0.000250, "output": 0.00125}
            },
            "ollama": {"cost_per_1k_tokens": 0.0},  # Local is free
            "http": {"cost_per_1k_tokens": "varies"}  # Unknown
        }
        
        provider_costs = costs.get(self.config.type, {})
        model_cost = provider_costs.get(self.config.model, provider_costs)
        
        return {
            "provider": self.config.name,
            "type": self.config.type,
            "model": self.config.model,
            "cost_info": model_cost
        }
    
    def _get_prompt(self, mode: str, commit) -> str:
        """Get prompt for analysis mode (brief/deep)"""
        # Check if provider has custom prompt mapping
        if self.config.prompts and mode in self.config.prompts:
            template_name = self.config.prompts[mode]
            if self.prompt_manager:
                custom_prompt = self.prompt_manager.render_prompt(template_name, commit)
                if custom_prompt:
                    return custom_prompt
        
        # Fallback to default prompts
        if mode == "brief":
            return self._build_brief_prompt(commit)
        elif mode == "deep":
            return self._build_deep_prompt(commit)
        else:
            return self._build_brief_prompt(commit)
    
    def _build_brief_prompt(self, commit) -> str:
        """Default brief prompt - to be overridden by subclasses"""
        return f"Analyze this git commit briefly: {commit.message}"
    
    def _build_deep_prompt(self, commit) -> str:
        """Default deep prompt - to be overridden by subclasses"""
        return f"Analyze this git commit in detail: {commit.message}"


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""
    
    def is_available(self) -> bool:
        """Check if Ollama is running and model is available"""
        if self._available is not None:
            return self._available
        
        try:
            # Check if Ollama is running
            req = urllib.request.Request(f"{self.config.endpoint}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.getcode() != 200:
                    self._available = False
                    return False
                
                # Check if our model is available
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                model_names = [model.get("name", "") for model in models]
            
            # Check if our model exists (with or without tag)
            model_available = any(
                self.config.model in name or name.startswith(self.config.model.split(":")[0])
                for name in model_names
            )
            
            self._available = model_available
            return model_available
            
        except Exception:
            self._available = False
            return False
    
    def analyze_brief(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Brief analysis using Ollama"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("brief", commit)
        response = self._call_ollama(prompt)
        
        if response:
            return AnalysisResult(
                mode=AnalysisMode.BRIEF,
                commit_hash=commit.hash,
                provider=f"ollama_{self.config.model}",
                version=1,
                summary=response.strip(),
                metadata={
                    "model": self.config.model,
                    "provider_type": "ollama"
                }
            )
        return None
    
    def analyze_deep(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Deep analysis using Ollama"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("deep", commit)
        response = self._call_ollama(prompt)
        
        if response:
            # Parse structured response (JSON format expected)
            try:
                parsed = json.loads(response)
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"ollama_{self.config.model}",
                    version=1,
                    summary=parsed.get("summary", ""),
                    details=parsed.get("details", ""),
                    risks=parsed.get("risks", []),
                    recommendations=parsed.get("recommendations", []),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "ollama"
                    }
                )
            except json.JSONDecodeError:
                # Fallback to plain text
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"ollama_{self.config.model}",
                    version=1,
                    summary=response.strip(),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "ollama"
                    }
                )
        return None
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama API"""
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.config.endpoint}/api/generate",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                if response.getcode() == 200:
                    result = json.loads(response.read().decode())
                    return result.get("response", "")
            return None
            
        except Exception:
            return None
    
    def _build_brief_prompt(self, commit: GitCommit) -> str:
        """Build prompt for brief analysis"""
        return f"""Analyze this git commit briefly in one sentence.

Commit: {commit.hash[:8]}
Message: {commit.message}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

Provide a concise one-line summary of what this commit does and its significance."""
    
    def _build_deep_prompt(self, commit: GitCommit) -> str:
        """Build prompt for deep analysis"""
        return f"""Analyze this git commit in detail. Return JSON with keys: summary, details, risks, recommendations.

Commit: {commit.hash[:8]}
Message: {commit.message}
Author: {commit.author}
Date: {commit.date}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

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


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is available"""
        import os
        if self._available is not None:
            return self._available
        
        api_key = os.getenv(self.config.api_key_env or "OPENAI_API_KEY")
        self._available = bool(api_key)
        return self._available
    
    def analyze_brief(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Brief analysis using OpenAI"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("brief", commit)
        response = self._call_openai(prompt, max_tokens=100)
        
        if response:
            return AnalysisResult(
                mode=AnalysisMode.BRIEF,
                commit_hash=commit.hash,
                provider=f"openai_{self.config.model}",
                version=1,
                summary=response.strip(),
                metadata={
                    "model": self.config.model,
                    "provider_type": "openai"
                }
            )
        return None
    
    def analyze_deep(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Deep analysis using OpenAI"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("deep", commit)
        response = self._call_openai(prompt, max_tokens=500)
        
        if response:
            # Parse structured response (JSON format expected)
            try:
                parsed = json.loads(response)
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"openai_{self.config.model}",
                    version=1,
                    summary=parsed.get("summary", ""),
                    details=parsed.get("details", ""),
                    risks=parsed.get("risks", []),
                    recommendations=parsed.get("recommendations", []),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "openai"
                    }
                )
            except json.JSONDecodeError:
                # Fallback to plain text
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"openai_{self.config.model}",
                    version=1,
                    summary=response.strip(),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "openai"
                    }
                )
        return None
    
    def _call_openai(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Call OpenAI API"""
        import os
        
        api_key = os.getenv(self.config.api_key_env or "OPENAI_API_KEY")
        if not api_key:
            return None
        
        try:
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.config.endpoint}/chat/completions",
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
            )
            
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                if response.getcode() == 200:
                    result = json.loads(response.read().decode())
                    return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return None
            
        except Exception:
            return None
    
    def _build_brief_prompt(self, commit: GitCommit) -> str:
        """Build prompt for brief analysis"""
        return f"""Analyze this git commit briefly in one sentence.

Commit: {commit.hash[:8]}
Message: {commit.message}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

Provide a concise one-line summary of what this commit does and its significance."""
    
    def _build_deep_prompt(self, commit: GitCommit) -> str:
        """Build prompt for deep analysis"""
        return f"""Analyze this git commit in detail. Return JSON with keys: summary, details, risks, recommendations.

Commit: {commit.hash[:8]}
Message: {commit.message}
Author: {commit.author}
Date: {commit.date}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

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


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider"""
    
    def is_available(self) -> bool:
        """Check if Anthropic API key is available"""
        import os
        if self._available is not None:
            return self._available
        
        api_key = os.getenv(self.config.api_key_env or "ANTHROPIC_API_KEY")
        self._available = bool(api_key)
        return self._available
    
    def analyze_brief(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Brief analysis using Anthropic Claude"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("brief", commit)
        response = self._call_anthropic(prompt, max_tokens=100)
        
        if response:
            return AnalysisResult(
                mode=AnalysisMode.BRIEF,
                commit_hash=commit.hash,
                provider=f"anthropic_{self.config.model}",
                version=1,
                summary=response.strip(),
                metadata={
                    "model": self.config.model,
                    "provider_type": "anthropic"
                }
            )
        return None
    
    def analyze_deep(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Deep analysis using Anthropic Claude"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("deep", commit)
        response = self._call_anthropic(prompt, max_tokens=500)
        
        if response:
            # Parse structured response (JSON format expected)
            try:
                parsed = json.loads(response)
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"anthropic_{self.config.model}",
                    version=1,
                    summary=parsed.get("summary", ""),
                    details=parsed.get("details", ""),
                    risks=parsed.get("risks", []),
                    recommendations=parsed.get("recommendations", []),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "anthropic"
                    }
                )
            except json.JSONDecodeError:
                # Fallback to plain text
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"anthropic_{self.config.model}",
                    version=1,
                    summary=response.strip(),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "anthropic"
                    }
                )
        return None
    
    def _call_anthropic(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Call Anthropic API"""
        import os
        
        api_key = os.getenv(self.config.api_key_env or "ANTHROPIC_API_KEY")
        if not api_key:
            return None
        
        try:
            payload = {
                "model": self.config.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.config.endpoint}/v1/messages",
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                }
            )
            
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                if response.getcode() == 200:
                    result = json.loads(response.read().decode())
                    content = result.get("content", [])
                    if content and len(content) > 0:
                        return content[0].get("text", "")
            return None
            
        except Exception:
            return None
    
    def _build_brief_prompt(self, commit: GitCommit) -> str:
        """Build prompt for brief analysis"""
        return f"""Analyze this git commit briefly in one sentence.

Commit: {commit.hash[:8]}
Message: {commit.message}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

Provide a concise one-line summary of what this commit does and its significance."""
    
    def _build_deep_prompt(self, commit: GitCommit) -> str:
        """Build prompt for deep analysis"""
        return f"""Analyze this git commit in detail. Return JSON with keys: summary, details, risks, recommendations.

Commit: {commit.hash[:8]}
Message: {commit.message}
Author: {commit.author}
Date: {commit.date}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

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


class GenericHTTPProvider(LLMProvider):
    """Generic HTTP provider for any OpenAI-compatible API"""
    
    def is_available(self) -> bool:
        """Check if endpoint is available"""
        if self._available is not None:
            return self._available
        
        try:
            # Simple ping to check if endpoint is reachable
            req = urllib.request.Request(self.config.endpoint)
            if self.config.headers:
                for key, value in self.config.headers.items():
                    req.add_header(key, value)
            
            with urllib.request.urlopen(req, timeout=5) as response:
                self._available = response.getcode() in [200, 404, 405]  # Endpoint exists
                return self._available
            
        except Exception:
            self._available = False
            return False
    
    def analyze_brief(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Brief analysis using generic HTTP endpoint"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("brief", commit)
        response = self._call_http(prompt, max_tokens=100)
        
        if response:
            return AnalysisResult(
                mode=AnalysisMode.BRIEF,
                commit_hash=commit.hash,
                provider=f"http_{self.config.name}",
                version=1,
                summary=response.strip(),
                metadata={
                    "model": self.config.model,
                    "provider_type": "http",
                    "endpoint": self.config.endpoint
                }
            )
        return None
    
    def analyze_deep(self, commit: GitCommit) -> Optional[AnalysisResult]:
        """Deep analysis using generic HTTP endpoint"""
        if not self.is_available():
            return None
        
        prompt = self._get_prompt("deep", commit)
        response = self._call_http(prompt, max_tokens=500)
        
        if response:
            # Parse structured response (JSON format expected)
            try:
                parsed = json.loads(response)
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"http_{self.config.name}",
                    version=1,
                    summary=parsed.get("summary", ""),
                    details=parsed.get("details", ""),
                    risks=parsed.get("risks", []),
                    recommendations=parsed.get("recommendations", []),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "http",
                        "endpoint": self.config.endpoint
                    }
                )
            except json.JSONDecodeError:
                # Fallback to plain text
                return AnalysisResult(
                    mode=AnalysisMode.DEEP,
                    commit_hash=commit.hash,
                    provider=f"http_{self.config.name}",
                    version=1,
                    summary=response.strip(),
                    metadata={
                        "model": self.config.model,
                        "provider_type": "http",
                        "endpoint": self.config.endpoint
                    }
                )
        return None
    
    def _call_http(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Call generic HTTP endpoint"""
        try:
            # Default OpenAI-compatible format
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.config.endpoint}/chat/completions" if not self.config.endpoint.endswith('/chat/completions') else self.config.endpoint,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Add custom headers
            if self.config.headers:
                for key, value in self.config.headers.items():
                    req.add_header(key, value)
            
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                if response.getcode() == 200:
                    result = json.loads(response.read().decode())
                    return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return None
            
        except Exception:
            return None
    
    def _build_brief_prompt(self, commit: GitCommit) -> str:
        """Build prompt for brief analysis"""
        return f"""Analyze this git commit briefly in one sentence.

Commit: {commit.hash[:8]}
Message: {commit.message}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

Provide a concise one-line summary of what this commit does and its significance."""
    
    def _build_deep_prompt(self, commit: GitCommit) -> str:
        """Build prompt for deep analysis"""
        return f"""Analyze this git commit in detail. Return JSON with keys: summary, details, risks, recommendations.

Commit: {commit.hash[:8]}
Message: {commit.message}
Author: {commit.author}
Date: {commit.date}
Files changed: {commit.files_changed}
Lines: +{commit.insertions}, -{commit.deletions}

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


class ProviderManager:
    """Manages LLM providers and configuration"""
    
    def __init__(self, config_dir: Path, prompt_manager=None):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "providers.json"
        self.prompt_manager = prompt_manager
        self.providers: List[LLMProvider] = []
        self._load_config()
    
    def _load_config(self):
        """Load provider configuration from JSON"""
        if not self.config_file.exists():
            self._create_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            self.providers = []
            for provider_config in config_data.get("providers", []):
                config = ProviderConfig(**provider_config)
                if config.enabled:
                    provider = self._create_provider(config)
                    if provider:
                        self.providers.append(provider)
            
            # Sort by priority
            self.providers.sort(key=lambda p: p.config.priority)
            
        except Exception as e:
            print(f"Error loading provider config: {e}")
            self.providers = []
    
    def _create_provider(self, config: ProviderConfig) -> Optional[LLMProvider]:
        """Create provider instance from config"""
        if config.type == "ollama":
            return OllamaProvider(config, self.prompt_manager)
        elif config.type == "openai":
            return OpenAIProvider(config, self.prompt_manager)
        elif config.type == "anthropic":
            return AnthropicProvider(config, self.prompt_manager)
        elif config.type == "http":
            return GenericHTTPProvider(config, self.prompt_manager)
        return None
    
    def _create_default_config(self):
        """Create default provider configuration"""
        default_config = {
            "providers": [
                {
                    "name": "ollama_mistral",
                    "type": "ollama",
                    "endpoint": "http://localhost:11434",
                    "model": "mistral:latest",
                    "priority": 1,
                    "enabled": True,
                    "timeout": 30
                },
                {
                    "name": "openai_gpt4",
                    "type": "openai",
                    "endpoint": "https://api.openai.com/v1",
                    "model": "gpt-4o-mini",
                    "priority": 2,
                    "api_key_env": "OPENAI_API_KEY",
                    "enabled": False,
                    "timeout": 30
                },
                {
                    "name": "anthropic_claude",
                    "type": "anthropic",
                    "endpoint": "https://api.anthropic.com",
                    "model": "claude-3-haiku-20240307",
                    "priority": 3,
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "enabled": False,
                    "timeout": 30
                },
                {
                    "name": "local_llama",
                    "type": "http",
                    "endpoint": "http://localhost:8080/v1",
                    "model": "llama-3-8b",
                    "priority": 4,
                    "enabled": False,
                    "timeout": 30,
                    "headers": {
                        "Authorization": "Bearer your-api-key-here"
                    },
                    "prompts": {
                        "brief": "brief_default",
                        "deep": "deep_default"
                    }
                }
            ]
        }
        
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
    
    def get_available_provider(self) -> Optional[LLMProvider]:
        """Get first available provider"""
        for provider in self.providers:
            if provider.is_available():
                return provider
        return None
    
    def get_providers(self) -> List[LLMProvider]:
        """Get all configured providers"""
        return self.providers.copy()
    
    def test_provider(self, provider_name: str) -> Dict[str, Any]:
        """Test specific provider availability"""
        for provider in self.providers:
            if provider.config.name == provider_name:
                return {
                    "name": provider.config.name,
                    "type": provider.config.type,
                    "available": provider.is_available(),
                    "model": provider.config.model,
                    "endpoint": provider.config.endpoint
                }
        
        return {"error": f"Provider {provider_name} not found"}
    
    def save_config(self):
        """Save current provider configuration"""
        config_data = {
            "providers": [
                {
                    "name": p.config.name,
                    "type": p.config.type,
                    "endpoint": p.config.endpoint,
                    "model": p.config.model,
                    "priority": p.config.priority,
                    "api_key_env": p.config.api_key_env,
                    "headers": p.config.headers,
                    "timeout": p.config.timeout,
                    "enabled": p.config.enabled,
                    "prompts": p.config.prompts
                }
                for p in self.providers
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)