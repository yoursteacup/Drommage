# 🚀 DRommage - Intelligent Documentation Version Control

> *Where git meets AI to understand not just what changed, but why it matters*

## 🎯 What is DRommage?

DRommage is a revolutionary documentation versioning system that combines git-style region tracking with LLM-powered semantic analysis. It doesn't just show you diffs - it explains them, analyzes their impact, and provides actionable insights.

## ✨ Key Features

### 🧠 **Intelligent Diff Analysis**
- **Semantic Understanding**: Goes beyond line-by-line diffs to understand meaning
- **Multi-Level Analysis**: Brief summaries to deep technical breakdowns
- **Risk Assessment**: Identifies potential issues and breaking changes
- **Smart Recommendations**: Suggests next steps and improvements

### 🎨 **Beautiful Terminal UI**
- **Golden Ratio Layout**: Aesthetically pleasing proportions
- **Unicode Box Drawing**: Modern, clean interface design
- **Real-time Status Updates**: Never wonder what's happening
- **Color-Coded Regions**: Instantly see volatile vs stable areas

### ⚡ **Performance & Efficiency**
- **SQLite Caching**: Lightning-fast repeated analyses
- **Local LLM Support**: Privacy-first with Ollama integration
- **Region Tracking**: Efficiently monitors document evolution
- **Incremental Analysis**: Only analyzes what changed

## 🛠️ Installation

### Prerequisites
```bash
# Python 3.8+
python --version

# Ollama for local LLM (recommended)
# macOS:
brew install ollama

# Linux:
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the Mistral model
ollama pull mistral
```

### Quick Start
```bash
# Clone the repository
git clone git@github.com:yoursteacup/Drommage.git
cd Drommage

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run DRommage
python main_v8.py
```

## 🎮 Usage

### Keyboard Controls
| Key | Action |
|-----|--------|
| `↑↓` | Navigate versions |
| `B` | Brief analysis (quick summary) |
| `D` | Deep analysis (detailed with risks/recommendations) |
| `R` | Region details (see specific text regions) |
| `PgUp/Dn` | Scroll document |
| `ESC` | Go back |
| `Q` | Quit |

### Analysis Levels

#### 📝 **Brief Analysis** (`B`)
Quick one-line summary of changes - perfect for scanning through versions.

#### 🔍 **Deep Analysis** (`D`)
Comprehensive analysis including:
- Change type classification (feature/fix/docs/etc.)
- Impact assessment
- Detailed explanation
- Potential risks
- Actionable recommendations

## 🏗️ Architecture

```
DRommage/
├── core/
│   ├── git_engine.py      # Git-style region tracking
│   ├── llm_analyzer.py    # LLM integration & analysis
│   ├── region_index.py    # Region volatility tracking
│   └── tui_v8.py          # Terminal UI implementation
├── test_docs/             # Sample documents
└── main_v8.py            # Entry point
```

### Core Components

1. **GitDiffEngine**: Tracks document regions through versions using semantic hashing
2. **LLMAnalyzer**: Interfaces with Ollama for intelligent analysis
3. **RegionIndex**: Identifies volatile vs stable document sections
4. **DocTUIView**: Beautiful terminal interface with real-time updates

## 🔬 How It Works

1. **Region Detection**: Documents are parsed into semantic regions
2. **Change Tracking**: Each region gets a unique hash and is tracked across versions
3. **Smart Analysis**: When you request analysis, the LLM examines:
   - What changed (text diff)
   - Why it changed (semantic analysis)
   - What it means (impact assessment)
4. **Caching**: Results are stored for instant retrieval

## 💡 Use Cases

- **API Documentation**: Track breaking changes and compatibility
- **Technical Specs**: Monitor requirement evolution
- **Knowledge Bases**: Understand content drift over time
- **Compliance Docs**: Ensure critical sections remain stable
- **Team Documentation**: See who changed what and why

## 🚦 Status Indicators

During analysis, you'll see:
- `📊 Analyzing: X lines, Y chars diff` - Diff metrics
- `📝 Prompt size: X chars, Level: brief/detailed` - LLM prompt info
- `🤖 Starting LLM inference...` - Processing
- `✅ Analysis complete (X.Xs)` - Done with timing
- `📦 Using cached analysis` - Retrieved from cache

## 🎨 Visual Design

The interface uses carefully chosen visual elements:
- **Colors**: 11-color palette for different change types
- **Icons**: Semantic icons (🚀 feature, 🐛 bugfix, 📝 docs, etc.)
- **Layout**: Golden ratio (0.382) for panel sizing
- **Borders**: Unicode box drawing for clean lines

## 🔧 Configuration

### Using Different LLM Models
```python
# In main_v8.py, modify:
llm = LLMAnalyzer(model="mistral:latest")  # Change model here
```

### Adjusting Cache Location
```python
# Default: .llm_cache/
llm = LLMAnalyzer(cache_dir="custom_cache_path")
```

## 🐛 Troubleshooting

### Ollama Not Found
```bash
# Check installation
ollama list

# If not installed, see Prerequisites section
```

### Analysis Seems Stuck
- Check status bar for progress updates
- Default timeout is 30 seconds
- Press `Q` to quit if needed

### Cache Issues
```bash
# Clear cache if corrupted
rm -rf .llm_cache/
```

## 🚀 Future Roadmap

- [ ] Cloud LLM fallback (OpenAI/Claude API)
- [ ] Web UI version
- [ ] Collaborative features
- [ ] Export to CHANGELOG.md
- [ ] Git hooks integration
- [ ] VS Code extension

## 🤝 Contributing

We welcome contributions! Whether it's:
- Bug reports
- Feature requests  
- Code improvements
- Documentation updates

Feel free to open an issue or submit a PR.

## 📜 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with Anthropic's Claude
- Powered by Ollama and Mistral
- Inspired by the need for smarter documentation tools

---

**Remember**: DRommage doesn't just track changes - it understands them. 🧠✨

*Happy documenting!*