# test_setup.py
"""
Quick test to verify Claude Impact Analyzer setup
Run this before starting the main watcher
"""

import sys

def test_dependencies():
    """Check if all required packages are installed"""
    print("🔍 Checking dependencies...\n")
    
    missing = []
    
    # Check watchdog
    try:
        import watchdog
        print("✅ watchdog installed")
    except ImportError:
        print("❌ watchdog NOT installed")
        missing.append("watchdog")
    
    # Check requests
    try:
        import requests
        print("✅ requests installed")
    except ImportError:
        print("❌ requests NOT installed")
        missing.append("requests")
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed!\n")
    return True


def test_api_key():
    """Check if API key is configured"""
    print("🔍 Checking API key configuration...\n")
    
    try:
        from main import CLAUDE_API_KEY
        
        if not CLAUDE_API_KEY or CLAUDE_API_KEY == "your-api-key-here":
            print("❌ API key not configured!")
            print("   Update CLAUDE_API_KEY in main.py")
            return False
        
        if len(CLAUDE_API_KEY) < 20:
            print("⚠️  API key looks too short - verify it's correct")
            return False
        
        print(f"✅ API key configured (length: {len(CLAUDE_API_KEY)} chars)\n")
        return True
        
    except ImportError as e:
        print(f"❌ Could not import main.py: {e}")
        return False


def test_api_connection():
    """Test connection to Claude API"""
    print("🔍 Testing Claude API connection...\n")
    
    try:
        import requests
        from main import CLAUDE_API_KEY
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Say 'API test successful!' and nothing else."}]
        }
        
        print("📡 Sending test request to Claude API...")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("content", [])
            if content and content[0].get("type") == "text":
                print(f"✅ API Response: {content[0].get('text', '')}")
                print("✅ Claude API connection successful!\n")
                return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_project_path():
    """Check if project path exists"""
    print("🔍 Checking project path...\n")
    
    try:
        import os
        from main import PROJECT_PATH
        
        if os.path.exists(PROJECT_PATH):
            print(f"✅ Project path exists: {PROJECT_PATH}")
            
            # Count Python files
            py_files = []
            for root, _, files in os.walk(PROJECT_PATH):
                for f in files:
                    if f.endswith('.py'):
                        py_files.append(os.path.join(root, f))
            
            print(f"   Found {len(py_files)} Python file(s) to monitor\n")
            return True
        else:
            print(f"❌ Project path does not exist: {PROJECT_PATH}")
            print("   Update PROJECT_PATH in main.py")
            return False
            
    except Exception as e:
        print(f"❌ Error checking path: {e}")
        return False


def main():
    print("="*60)
    print("Claude Impact Analyzer - Setup Test")
    print("="*60)
    print()
    
    results = []
    
    # Run all tests
    results.append(("Dependencies", test_dependencies()))
    results.append(("API Key", test_api_key()))
    results.append(("Project Path", test_project_path()))
    results.append(("API Connection", test_api_connection()))
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    print()
    
    if all(result[1] for result in results):
        print("🎉 All tests passed! Ready to run the watcher.")
        print("   Start with: python main.py")
        return 0
    else:
        print("⚠️  Some tests failed. Fix the issues above before running.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
