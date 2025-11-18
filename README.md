# Code Impact Analyzer with AI-Powered Insights

## Overview

**Code Impact Analyzer** is an intelligent system that automatically tracks code changes in real-time and provides comprehensive impact analysis for production deployment decisions. By combining dependency graph analysis with Claude AI, it helps developers and SMEs understand the full scope of their code changes before deployment.

## Problem Statement

When developers modify code:
- **Unknown Impacts**: Changes to one line can affect multiple functions and variables across the codebase
- **Risk Assessment**: Difficult to gauge whether a change is LOW, MEDIUM, or HIGH risk
- **Production Failures**: Unanticipated downstream effects lead to bugs in production
- **Manual Review**: SMEs spend hours reviewing code without clear impact visualization

##  Solution

Our system provides:
1. **Real-time Change Detection**: Automatically detects when Python files are saved
2. **Dependency Graph Analysis**: Traces how changes cascade through variables and functions
3. **Per-Line Impact Tracking**: Separate graphs for each changed line showing individual and shared impacts
4. **AI-Powered Insights**: Claude AI analyzes severity levels and provides production risk assessments
5. **Interactive Visualization**: Zoom-enabled, clickable dependency graphs with detailed explanations

##  Installation

### Prerequisites
```bash
# Python 3.8+
pip install watchdog requests
```

### Setup
1. Clone the repository
2. Configure API key in .env file:

### Run
```bash
cd code_watcher
python main.py C:\path\to\your\project
```

##  Architecture
(Diagram available in the repo - architecture-diagram.jpg )
### High-Level Flow
```
File Save → Change Detection → Dependency Analysis → Claude AI Analysis → Interactive Visualization
```

### Components

#### 1. **File Watcher** (`watcher.py`)
- Monitors Python files for changes using `watchdog` library
- Triggers analysis pipeline on save events
- Debounces rapid changes (0.5s interval)

#### 2. **Code Analyzer** (`analyzer.py`)
- Parses Python code using AST (Abstract Syntax Tree)
- Builds dependency graphs for variables and functions
- Tracks:
  - Added/deleted/modified variables and functions
  - Dependency relationships
  - Cross-scope impacts

#### 3. **Cache Manager** (`cache_manager.py`)
- Stores baseline file states
- Compares current vs previous versions
- Detects line-level changes
- Manages dependency graph cache

#### 4. **Per-Line Impact Tracker**
- Analyzes each changed line independently
- Identifies shared dependencies across multiple line changes
- Tracks:
  - Which functions are affected by which lines
  - Which variables are affected by which lines
  - Cross-line dependency overlaps

#### 5. **Claude AI Analyzer** (`claude_analyzer.py`)
- Sends code context to Claude API
- Receives detailed impact analysis
- Generates severity assessments (HIGH/MEDIUM/LOW)
- Provides production risk recommendations

#### 6. **Visualization Generator**
- Creates interactive HTML with React
- Builds per-line dependency graphs
- Shows cross-graph connections for shared nodes
- Includes zoom controls and detailed node information

##  Key Features

### Real-Time Analysis
- Automatic detection on file save
- No manual triggers required
- Results appear within 10-20 seconds

### Per-Line Dependency Graphs
- Separate graph for each changed line
- Visual flow: `Changed Line → Functions → Variables`
- Stacked vertically with clear separators
- 900px spacing for better readability

### Shared Node Detection
- **Blue dashed borders** on nodes affected by multiple lines
- **Blue dashed arrows** connecting shared nodes across graphs
- Shows which lines affect each shared component
- Example: If lines 26 and 27 both affect `generate_account_number()`, it appears in both graphs with connections

### Severity Classification

**Functions:**
- **HIGH** (Red): >5 dependencies - "Complex logic, wide-reaching impact"
- **MEDIUM** (Yellow): 3-5 dependencies - "Moderate complexity"
- **LOW** (Green): ≤2 dependencies - "Simple, isolated logic"

**Variables:**
- **MEDIUM** (Yellow): >4 dependencies - "Wide propagation potential"
- **LOW** (Green): 1-4 dependencies - "Limited scope"
- **LOW** (Green): 0 dependencies - "Isolated change"

**Changed Lines:**
- **HIGH** (Red): Always - "Root cause of downstream impacts"

### Interactive Visualization
- **Zoom Controls**: 0.5x to 2.0x magnification
- **Click to Inspect**: Click any node to see:
  -  Description: What the node represents
  -  Impact: How it affects the codebase
  -  Severity Explanation: WHY it's marked HIGH/MEDIUM/LOW
  -  Dependencies: Total count of dependencies
  -  Shared Info: Which lines affect this node (if shared)
- **Scrollable Canvas**: Navigate large dependency trees easily

### Claude AI Analysis Tab
- Detailed line-by-line analysis
- Production risk assessment
- Required testing recommendations
- Immediate actions needed

##  Output Format

### Console Output
```
Detected change in: test1.py
Changed lines: [26, 27, 28]

 MODIFIED (and downstream impacts):
   Variables: {'test1.create_account.account_number', ...}
   Functions: {'test1.generate_account_number', ...}

 GENERATING CLAUDE IMPACT ANALYSIS...
 Visualization saved to: C:\Users\...\impact_analysis_20250118.html
 Opening in browser...
```

### Visual Output
- **Header**: File name, changed lines, stats (vars/funcs affected)
- **Graph Tab**: Interactive per-line dependency graphs
- **Analysis Tab**: Full Claude AI insights
- **Node Details Panel**: Shows when clicking nodes



The watcher will start monitoring your target directory. Save any Python file to trigger analysis.

## 📁 Project Structure

```
code_watcher/
├── main.py                 # Entry point, orchestrates analysis pipeline
├── watcher.py             # File system monitoring
├── analyzer.py            # AST parsing and dependency tracking
├── cache_manager.py       # Change detection and caching
├── claude_analyzer.py     # Claude API integration + visualization
├── package.json           # VS Code extension manifest (future)
├── extension.ts           # VS Code extension code (future)
├── README.md              # This file
├── QUICKSTART.md          # Quick setup guide
└── test_setup.py          # Setup verification script
```

## 🔧 Configuration

### Analysis Settings
- **Debounce Interval**: Adjust in `watcher.py` (default: 0.5s)
- **API Timeout**: Set in `claude_analyzer.py` (default: 120s)
- **Graph Spacing**: Modify in `_build_dependency_graphs_per_line()`:
  - `y_offset_per_graph = 900` (spacing between graphs)
  - `func_spacing = 120` (spacing between function nodes)
  - `var_spacing = 100` (spacing between variable nodes)

### Output Settings
- **Output File**: Change `OUTPUT_PATH` in `main.py`
- **Zoom Range**: Adjust min/max in HTML template (default: 0.5x-2.0x)

##  Use Cases

### 1. Pre-Commit Review
Run analysis before committing to see full impact of changes

### 2. Code Review Preparation
Generate visual reports for SME review meetings

### 3. Production Risk Assessment
Understand deployment risks before pushing to production

### 4. Refactoring Safety
Ensure refactoring doesn't break unexpected dependencies

### 5. Onboarding New Developers
Teach codebase structure through visual dependency exploration

##  Example Scenario

**Developer changes 2 lines in `test1.py`:**

**Line 26**: Modifies `generate_account_number()` logic
**Line 27**: Changes `create_account()` parameters

**System Output:**
1. Two separate dependency graphs (one per line)
2. Shows `generate_account_number()` appears in BOTH graphs (shared node)
3. Blue dashed arrow connects the two instances
4. Click on shared node reveals: "Affected by lines: 26, 27"
5. Severity: HIGH (>5 dependencies)
6. Claude analysis: "CRITICAL - Both changes affect account creation pipeline"

##  Technical Details

### Dependency Detection Algorithm
1. Parse file with Python AST
2. Build qualified names: `file.class.function.variable`
3. Track dependencies for each entity
4. Normalize across scopes to detect cross-scope impacts
5. Recursively expand to find all downstream effects

### Per-Line Tracking
1. Analyze each changed line independently using `analyze_file_changes([line_num])`
2. Build separate node/edge lists for each line
3. Detect shared nodes by comparing affected entities
4. Create cross-graph edges between matching node IDs
5. Position graphs vertically with consistent x-coordinates for alignment

### Severity Calculation
- **Functions**: Based on dependency count (dependencies = functions/vars it uses)
- **Variables**: Based on dependency count (dependencies = items it depends on)
- **Changed Lines**: Always HIGH (source of change)

### Graph Layout
- **X-axis**: Changed lines (120px) → Functions (400px) → Variables (700px)
- **Y-axis**: Stacked graphs, 900px apart
- **Connections**: 
  - Gray arrows: Within-graph dependencies
  - Blue dashed arrows: Cross-graph shared node connections

##  Security

- API keys stored locally in code (not committed to git)
- Analysis runs locally on your machine
- Only sends code snippets to Claude API
- HTML visualizations stored in temp directory
- No data persistence beyond session

##  Performance

- **Initial Scan**: 2-5 seconds (depends on project size)
- **Per-File Analysis**: 1-2 seconds (local analysis)
- **Claude API Call**: 5-15 seconds (network dependent)
- **Total Time**: ~10-20 seconds from save to visualization
- **Memory**: ~50-100MB (depends on graph complexity)

##  Troubleshooting

### "No changes detected"
- Ensure file content actually changed
- Check if file is in monitored directory
- Verify cache isn't stale (restart watcher)

### "API Error 401"
- Check Claude API key in `main.py`
- Verify API key has not expired
- Ensure proper formatting (no quotes/spaces)

### "Module not found"
```bash
pip install watchdog requests
```

### "Browser doesn't open"
- HTML file path printed in console
- Open manually from temp directory
- Check default browser settings

### "Graph nodes overlapping"
- Increase spacing values in `_build_dependency_graphs_per_line()`
- Use zoom controls to adjust view
- Reduce number of nodes by filtering

##  Limitations

- **Language Support**: Currently Python only
- **File Size**: Large files (>1000 lines) may have crowded graphs
- **API Costs**: Each analysis uses Claude API tokens (~$0.03 per analysis)
- **Real-time Only**: Doesn't analyze git history (only current changes)
- **Single File**: Analyzes one file at a time

##  Future Enhancements

### Phase 1: VS Code Extension (In Progress)
- Inline severity badges in editor
- Side panel with persistent graph
- Auto-analyze on save within VS Code
- Status bar indicators

### Phase 2: Multi-Language Support
- JavaScript/TypeScript
- Java
- C#
- Go

### Phase 3: Advanced Features
- Git integration (analyze commits/PRs)
- Team collaboration (shared reports)
- Historical trend analysis
- Custom severity thresholds
- Export to PDF/Markdown

### Phase 4: Enterprise Features
- CI/CD integration
- Pre-commit hooks
- Slack/Teams notifications
- Dashboard for multiple projects

##  Technical Stack

- **Language**: Python 3.8+
- **AST Parsing**: Python `ast` module
- **File Watching**: `watchdog` library
- **API Client**: `requests` library
- **AI Model**: Claude Sonnet 4 (Anthropic)
- **Visualization**: React 18 + Tailwind CSS
- **Browser Rendering**: Static HTML with embedded React

##  Team

Developed for SME Hackathon - Attempt 3 v4

##  License

MIT License - See LICENSE file for details

##  Contributing

This is an internal hackathon project. For questions or suggestions, contact the development team.

##  Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the QUICKSTART.md guide
3. Run `python test_setup.py` to verify setup
4. Check console output for detailed error messages

---

