# 🚀 Quick Start Guide

## Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install watchdog requests
```

### Step 2: Test Your Setup
```bash
python test_setup.py
```

This will verify:
- ✅ All packages are installed
- ✅ API key is configured
- ✅ Project path exists
- ✅ Claude API connection works

### Step 3: Start the Watcher
```bash
python main.py
```

You should see:
```
Scanning project folder...
 Initial analysis complete.
 Watching for changes...
Press Ctrl+C to stop.
```

## Try It Out

1. **Open a Python file** in your target folder (e.g., `test1.py`)
2. **Make a change** - modify a variable or function
3. **Save the file** (Ctrl+S or Cmd+S)
4. **Watch the magic!** 
   - Console shows detected changes
   - Claude analyzes impact
   - Browser opens with visualization

## What You'll See

### In Console:
```
Detected change in: C:\...\test1.py
Changed lines: [26]

 MODIFIED (and downstream impacts):
   Variables: {'test1.create_account.account_number', ...}
   Functions: {'test1.generate_account_number', ...}

============================================================
🤖 GENERATING CLAUDE IMPACT ANALYSIS...
============================================================
✅ Visualization saved to: C:\Users\...\temp\impact_analysis_20250113_143022.html
🌐 Opening in browser...
```

### In Browser:
- 📊 Interactive dependency graph
- 🎯 Severity levels for each change
- 📝 Compact impact analysis
- ⚠️ Production risk assessment
- ✅ Testing recommendations

## Tips

- **First time?** Try changing a simple variable assignment
- **Want detail?** Change function logic and see cascade effects
- **Testing disabled?** Set `CLAUDE_API_KEY = None` for local-only analysis
- **Too many alerts?** Increase `debounce_interval` in `watcher.py`

## Troubleshooting

### "Module not found"
```bash
pip install watchdog requests
```

### "API key not configured"
Edit `main.py` and set your actual API key

### "Project path does not exist"
Edit `main.py` and set `PROJECT_PATH` to your folder

### Browser doesn't open
Look for the file path in console and open manually

## Need Help?

Read the full documentation in `README.md`

---

**Ready?** Run `python test_setup.py` to get started! 🎉
