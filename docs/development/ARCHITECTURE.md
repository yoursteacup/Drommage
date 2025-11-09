# 🏗️ DRommage Architecture Design

## 📋 Core Principles

### **CLI Tool Philosophy:**
- **Self-contained utility** - like git, grep, ls
- **pip install drommage** for distribution convenience
- **Runs in git repositories** to analyze commits
- **Two modes:** Interactive TUI + Batch CLI for AI agents

### **API-First Core:**
```
CLI Interface → DRommageEngine → Git/LLM/Cache
     ↑              ↑              ↑
  Parsing        Core Logic    Data Sources
```

## 🎯 Target Architecture

### **File Structure:**
```
drommage/
├── cli.py                    # Entry point & argument parsing
├── core/
│   ├── engine.py            # DRommageEngine - main business logic
│   ├── analysis.py          # AnalysisResult, AnalysisMode enums
│   ├── pattern_analyzer.py  # Pattern analysis (LLM-free)
│   ├── cache.py             # SQLite cache with versioning
│   ├── providers.py         # LLM provider system
│   └── git_integration.py   # Git commands (existing)
├── interfaces/
│   ├── tui.py              # Refactored from interface.py
│   └── config.py           # drommage config TUI
└── __init__.py             # Package exports (minimal)
```

### **Core Classes:**

#### **DRommageEngine - Business Logic Core:**
```python
class DRommageEngine:
    def __init__(self, repo_path=".", cache_dir=".drommage"):
        self.git = GitIntegration(repo_path)
        self.cache = AnalysisCache(cache_dir)
        self.pattern_analyzer = PatternAnalyzer() 
        self.llm_provider = self._load_provider()
    
    def load_commits(self, limit=50) -> List[GitCommit]
    def analyze_commit(self, commit_hash, mode) -> AnalysisResult
    def get_available_modes() -> List[AnalysisMode]
    def reanalyze_commit(self, commit_hash, mode) -> AnalysisResult
```

#### **AnalysisMode & Results:**
```python
class AnalysisMode(Enum):
    PAT = "pattern"     # Pattern analysis (no LLM)
    BRIEF = "brief"     # Brief LLM analysis
    DEEP = "deep"       # Deep LLM analysis

@dataclass
class AnalysisResult:
    mode: AnalysisMode
    commit_hash: str
    provider: str
    version: int
    summary: str
    details: Optional[str] = None
    risks: List[str] = None
    recommendations: List[str] = None
    metadata: Dict = None
    created_at: datetime = None
```

## 🔌 Provider System

### **Universal LLM Providers:**
```python
class LLMProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool: pass
    @abstractmethod  
    def analyze(self, commit, level) -> AnalysisResult: pass
    @abstractmethod
    def get_cost_info(self) -> Dict: pass

# Implementations:
# - OllamaProvider (localhost HTTP)
# - OpenAIProvider (cloud API)  
# - AnthropicProvider (cloud API)
# - CustomHTTPProvider (generic HTTP endpoint)
```

### **Provider Configuration (.drommage/providers.json):**
```json
{
  "providers": [
    {
      "name": "ollama_local",
      "type": "ollama",
      "endpoint": "http://localhost:11434",
      "model": "mistral:latest",
      "priority": 1
    },
    {
      "name": "openai_gpt4", 
      "type": "openai",
      "api_key_env": "OPENAI_API_KEY",
      "model": "gpt-4o-mini",
      "priority": 2
    }
  ]
}
```

## 🗄️ Cache System

### **SQLite Schema (.drommage/cache.db):**
```sql
CREATE TABLE analyses (
    commit_hash TEXT NOT NULL,
    mode TEXT NOT NULL,
    provider TEXT NOT NULL,
    version INTEGER NOT NULL,
    summary TEXT,
    details JSON,
    risks JSON,
    recommendations JSON, 
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (commit_hash, mode, version)
);

CREATE TABLE providers_usage (
    provider TEXT PRIMARY KEY,
    total_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    avg_response_time REAL DEFAULT 0.0,
    last_used TIMESTAMP
);

CREATE INDEX idx_analyses_lookup ON analyses(commit_hash, mode);
CREATE INDEX idx_analyses_date ON analyses(created_at DESC);
```

### **Cache Management Commands:**
```bash
drommage cache clear                    # Clear all cache
drommage cache clear --mode=brief       # Clear specific mode
drommage cache stats                    # Show cache statistics  
drommage cache reanalyze HEAD           # Force re-analysis
drommage cache vacuum                   # SQLite cleanup
```

## 🎮 Interface Modes

### **TUI Mode (Interactive):**
```bash
drommage                # Default TUI mode
drommage --tui          # Explicit TUI mode
```
- **Curses interface** with commit list + analysis panels
- **PAT → BRIEF → DEEP** toggle with `d` key
- **Real-time provider switching**
- **Cache indicators** (cached vs fresh analysis)

### **Batch Mode (AI Agents):**
```bash
# Single commit analysis
drommage --commit=HEAD --mode=pattern --format=json

# Multiple commits
drommage --last=10 --mode=brief --format=text

# Commit range
drommage --since="1 week ago" --mode=deep --output=analysis.json

# Provider specific
drommage --provider=ollama_local --commit=HEAD --mode=brief
```

### **Configuration Mode:**
```bash
drommage config                 # TUI for provider setup
drommage config list            # List configured providers  
drommage config test ollama     # Test specific provider
drommage config add openai      # Add new provider (interactive)
```

## 🚀 Implementation Strategy

### **Phase 1: Core Separation**
1. Extract `DRommageEngine` from current `DocTUIView`
2. Create `AnalysisCache` with SQLite backend
3. Implement `PatternAnalyzer` as standalone component
4. Refactor TUI to use engine API

### **Phase 2: CLI Interface** 
1. Add `argparse` based CLI argument parsing
2. Implement batch mode for AI agents
3. Add JSON/text output formatters
4. Create `drommage config` command

### **Phase 3: Provider System**
1. Abstract current `LLMAnalyzer` into provider interface
2. Implement multiple provider backends
3. Add provider configuration management
4. Implement cost tracking and usage statistics

### **Phase 4: Cache Enhancement**
1. Add versioning support to cache
2. Implement cache management commands
3. Add cache statistics and cleanup tools
4. Optimize cache performance for large repositories

---

**Last Updated:** 2025-11-07  
**Status:** Design Phase - Ready for Implementation