# claude_analyzer.py
import json
import os
import webbrowser
import tempfile
from datetime import datetime

class ClaudeImpactAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.anthropic.com/v1/messages"
        
        # Check if requests is available
        try:
            import requests
            self.requests = requests
        except ImportError:
            print("⚠️  'requests' library not found. Install it with: pip install requests")
            self.requests = None
    
    def generate_impact_analysis(self, file_path, changed_lines, affected_vars, affected_funcs, 
                                 added_vars, added_funcs, deleted_vars, deleted_funcs,
                                 affected_by_deletion, code_content):
        """
        Send change data to Claude API and get impact analysis + visualization
        """
        
        if not self.requests:
            print("❌ Cannot proceed without 'requests' library")
            return None
        
        # Prepare the prompt for Claude
        prompt = self._build_analysis_prompt(
            file_path, changed_lines, affected_vars, affected_funcs,
            added_vars, added_funcs, deleted_vars, deleted_funcs,
            affected_by_deletion, code_content
        )
        
        # Call Claude API
        response = self._call_claude_api(prompt)
        
        if response:
            # Generate and open visualization
            self._generate_visualization(response, file_path)
            return response
        
        return None
    
    def _build_analysis_prompt(self, file_path, changed_lines, affected_vars, affected_funcs,
                               added_vars, added_funcs, deleted_vars, deleted_funcs,
                               affected_by_deletion, code_content):
        """Build the prompt for Claude with all change information"""
        
        file_name = os.path.basename(file_path)
        
        # Group changes by line for better analysis
        changes_by_line = {}
        for line_num in sorted(changed_lines):
            changes_by_line[f"line{line_num}"] = {
                "line_number": line_num,
                "severity": "unknown"
            }
        
        prompt = f"""You are analyzing code changes for production deployment. Create an interactive impact analysis visualization.

FILE: {file_name}
CHANGED LINES: {sorted(changed_lines)}

CHANGE SUMMARY:
- Added Variables: {len(added_vars)} → {list(added_vars) if added_vars else 'None'}
- Added Functions: {len(added_funcs)} → {list(added_funcs) if added_funcs else 'None'}
- Deleted Variables: {len(deleted_vars)} → {list(deleted_vars) if deleted_vars else 'None'}
- Deleted Functions: {len(deleted_funcs)} → {list(deleted_funcs) if deleted_funcs else 'None'}
- Modified Variables: {len(affected_vars)} → {list(affected_vars) if affected_vars else 'None'}
- Modified Functions: {len(affected_funcs)} → {list(affected_funcs) if affected_funcs else 'None'}
- Affected by Deletion: {len(affected_by_deletion)} → {list(affected_by_deletion) if affected_by_deletion else 'None'}

CURRENT CODE:
```python
{code_content}
```

TASK:
Create a React artifact (application/vnd.ant.react) with an interactive visualization showing:

1. **Dependency Graph**: Visual representation of how changes cascade through the code
2. **Impact by Line**: For each changed line, show:
   - Severity level (HIGH/MEDIUM/LOW/VARIABLE)
   - Number of variables affected
   - Number of functions affected
   - Description of what changed
   - Production risk assessment

3. **Compact Impact Analysis**: For each change, provide:
   - What specifically changed
   - Why it matters for production
   - Downstream ripple effects
   - Specific risks to watch for

4. **Production Risk Summary**: Overall deployment risk and required testing

Make it visually clear, interactive (clickable nodes), and focused on ACTIONABLE insights for SME review.
Use Tailwind CSS for styling, lucide-react for icons."""

        return prompt
    
    def _call_claude_api(self, prompt):
        """Make API call to Claude"""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8192,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            print("🤖 Calling Claude API for impact analysis...")
            response = self.requests.post(self.api_url, headers=headers, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("content", [])
            else:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Failed to call Claude API: {e}")
            return None
    
    def _generate_visualization(self, claude_response, file_path):
        """Extract React artifact from Claude response and open in browser"""
        try:
            # Look for React component in response
            react_component = None
            analysis_text = ""
            
            for content_block in claude_response:
                if content_block.get("type") == "text":
                    text = content_block.get("text", "")
                    analysis_text += text + "\n"
                    
                    # Try to extract React component
                    if "import React" in text or "import {" in text:
                        # Extract the component code
                        lines = text.split('\n')
                        component_lines = []
                        in_code_block = False
                        
                        for line in lines:
                            if line.strip().startswith('```') and ('jsx' in line or 'javascript' in line):
                                in_code_block = True
                                continue
                            elif line.strip() == '```' and in_code_block:
                                in_code_block = False
                                continue
                            
                            if in_code_block or (not line.strip().startswith('```') and 
                                                ('import' in line or 'const' in line or 
                                                 'function' in line or 'export' in line or
                                                 'return' in line or '<' in line)):
                                component_lines.append(line)
                        
                        if component_lines:
                            react_component = '\n'.join(component_lines)
                            break
            
            if react_component:
                # Wrap and save HTML
                html_content = self._wrap_react_component(react_component)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"impact_analysis_{timestamp}.html"
                temp_path = os.path.join(tempfile.gettempdir(), file_name)
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"✅ Visualization saved to: {temp_path}")
                print("🌐 Opening in browser...")
                webbrowser.open('file://' + temp_path)
            else:
                # No React component found, print text analysis
                print("\n" + "="*60)
                print("CLAUDE IMPACT ANALYSIS")
                print("="*60)
                print(analysis_text)
                print("="*60 + "\n")
                
        except Exception as e:
            print(f"❌ Failed to generate visualization: {e}")
            import traceback
            traceback.print_exc()
    
    def _wrap_react_component(self, react_code):
        """Wrap React component in HTML with necessary dependencies"""
        
        # Ensure the component exports properly
        if 'export default' not in react_code:
            # Find the main component name
            import re
            component_match = re.search(r'const\s+(\w+)\s*=', react_code)
            if component_match:
                component_name = component_match.group(1)
                react_code += f"\n\nexport default {component_name};"
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impact Analysis - Code Change Visualization</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
        }}
        #root {{
            width: 100vw;
            height: 100vh;
        }}
    </style>
</head>
<body>
    <div id="root"></div>
    
    <script type="text/babel">
        // Lucide React icons (inline lightweight version)
        const {{ createElement: h }} = React;
        
        const AlertCircle = (props) => h('svg', {{
            ...props,
            xmlns: "http://www.w3.org/2000/svg",
            width: "24",
            height: "24",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round"
        }}, 
            h('circle', {{ cx: "12", cy: "12", r: "10" }}),
            h('line', {{ x1: "12", y1: "8", x2: "12", y2: "12" }}),
            h('line', {{ x1: "12", y1: "16", x2: "12.01", y2: "16" }})
        );
        
        const TrendingUp = (props) => h('svg', {{
            ...props,
            xmlns: "http://www.w3.org/2000/svg",
            width: "24",
            height: "24",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round"
        }},
            h('polyline', {{ points: "22 7 13.5 15.5 8.5 10.5 2 17" }}),
            h('polyline', {{ points: "16 7 22 7 22 13" }})
        );
        
        const GitBranch = (props) => h('svg', {{
            ...props,
            xmlns: "http://www.w3.org/2000/svg",
            width: "24",
            height: "24",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeLinejoin: "round"
        }},
            h('line', {{ x1: "6", y1: "3", x2: "6", y2: "15" }}),
            h('circle', {{ cx: "18", cy: "6", r: "3" }}),
            h('circle', {{ cx: "6", cy: "18", r: "3" }}),
            h('path', {{ d: "M18 9a9 9 0 0 1-9 9" }})
        );
        
        {react_code}
        
        // Find the component to render
        const ComponentToRender = (typeof DependencyGraph !== 'undefined') ? DependencyGraph : 
                                   (typeof ImpactAnalysis !== 'undefined') ? ImpactAnalysis :
                                   (typeof App !== 'undefined') ? App : null;
        
        if (ComponentToRender) {{
            const root = ReactDOM.createRoot(document.getElementById('root'));
            root.render(React.createElement(ComponentToRender));
        }} else {{
            document.getElementById('root').innerHTML = '<div style="padding: 20px; color: red;">Error: Could not find React component to render</div>';
        }}
    </script>
</body>
</html>"""
        
        return html_template
