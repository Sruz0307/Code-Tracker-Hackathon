# Code Watcher with Claude Impact Analysis

## Overview
This tool watches your Python files for changes and automatically generates an **interactive impact analysis** using Claude AI whenever you save a file.

## Features
- 🔍 **Real-time file monitoring** - Detects changes immediately when you save
- 📊 **Dependency tracking** - Maps how changes cascade through your codebase
- 🤖 **Claude AI Analysis** - Generates intelligent impact assessments
- 📈 **Interactive Visualization** - Opens a beautiful React dashboard in your browser
- 🎯 **Production Focus** - Highlights risks and testing requirements

## Setup

### 1. Install Dependencies
```bash
pip install watchdog requests
```

### 2. Configure Your API Key
Open `main.py` and update:
```python
CLAUDE_API_KEY = "your-api-key-here"
```

### 3. Set Your Project Path
In `main.py`, set the folder you want to watch:
```python
PROJECT_PATH = r"C:\path\to\your\project"
```

## How to Use

### Start the Watcher
```bash
cd code_watcher
python main.py
```

### Make Changes
1. Edit any Python file in your target folder
2. Save the file (Ctrl+S)
3. The watcher detects the change
4. Claude analyzes the impact
5. A browser window opens with the visualization

### What You Get

**Console Output:**
- Changed lines detected
- Added/deleted/modified variables and functions
- Dependency cascade effects

**Browser Visualization:**
- Interactive dependency graph
- Severity-coded changes (HIGH/MEDIUM/LOW)
- Compact impact analysis for each change
- Production risk assessment
- Testing recommendations

## File Structure

```
code_watcher/
├── main.py              # Entry point & orchestration
├── watcher.py           # File system monitoring
├── analyzer.py          # Code analysis & dependency tracking
├── claude_analyzer.py   # Claude API integration
└── cache_manager.py     # Change detection & caching
```

## How It Works

1. **Initial Scan**: Builds dependency graph of your entire project
2. **Watch Mode**: Monitors for file changes
3. **Change Detection**: Identifies modified lines
4. **Impact Analysis**: Traces dependencies to find affected code
5. **Claude Enhancement**: Sends context to Claude API
6. **Visualization**: Generates interactive React dashboard

## Configuration Options

### Disable Claude Analysis
Set `CLAUDE_API_KEY = None` in `main.py` to use local analysis only.

### Adjust Debouncing
In `watcher.py`, modify `debounce_interval`:
```python
ChangeHandler(callback, debounce_interval=0.5)  # seconds
```

### Output File
Change where analysis is logged:
```python
OUTPUT_PATH = PROJECT_PATH + r"\output.txt"
```

## API Usage

The Claude API is called with:
- **Model**: `claude-sonnet-4-20250514`
- **Max Tokens**: 8192
- **Timeout**: 120 seconds

Each file save triggers **one API call** with full context.

## Troubleshooting

### "requests library not found"
```bash
pip install requests
```

### "API Error: 401"
Check your API key in `main.py`

### "No changes detected"
The file content may be identical to the cached version. Try making a meaningful change.

### Browser doesn't open
- Check if the HTML file was created in your temp directory
- Manually open the file path printed in the console

### Visualization shows error
- Ensure you have internet connection (loads React from CDN)
- Check browser console for JavaScript errors

## Advanced Usage

### Analyze Specific Lines
The system automatically detects which lines changed. The impact analysis shows:
- Direct changes to variables/functions on those lines
- Downstream dependencies affected
- Second-order impacts through the call chain

### Understanding Severity Levels
- **HIGH**: Core business logic, multiple dependencies, wide blast radius
- **MEDIUM**: Localized changes with some downstream impact
- **LOW**: Isolated changes with minimal dependencies
- **VARIABLE**: Depends on context (e.g., line reordering)

## Example Output

When you save a file:
```
Detected change in: test1.py
Changed lines: [26, 27, 28]

 MODIFIED (and downstream impacts):
   Variables: {'test1.generate_account_number.account_number', ...}
   Functions: {'test1.create_account.create_account', ...}

============================================================
🤖 GENERATING CLAUDE IMPACT ANALYSIS...
============================================================
🤖 Calling Claude API for impact analysis...
✅ Visualization saved to: C:\Users\...\impact_analysis_20250113_143022.html
🌐 Opening in browser...
```

Then your browser opens with an interactive dashboard!

## Tips for Best Results

1. **Make focused changes** - Easier to analyze than massive refactors
2. **Save frequently** - Get instant feedback on each change
3. **Review before production** - Use the risk assessment to plan testing
4. **Check the graph** - Visual dependencies reveal hidden connections
5. **Read the compact analysis** - Focused insights from Claude

## License
MIT

## Credits
- Built with Claude AI
- Uses Watchdog for file monitoring
- React + Tailwind for visualization
