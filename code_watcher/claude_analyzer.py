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
            self._generate_visualization(response, file_path, changed_lines, 
                                        affected_vars, affected_funcs)
            return response
        
        return None
    
    def _build_analysis_prompt(self, file_path, changed_lines, affected_vars, affected_funcs,
                               added_vars, added_funcs, deleted_vars, deleted_funcs,
                               affected_by_deletion, code_content):
        """Build the prompt for Claude with all change information"""
        
        file_name = os.path.basename(file_path)
        
        prompt = f"""You are analyzing code changes for production deployment. Provide a detailed impact analysis.

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

Please provide:
1. For EACH changed line, analyze:
   - What specifically changed
   - Severity level (HIGH/MEDIUM/LOW/VARIABLE)
   - Production risk and impact
   
2. Overall assessment:
   - Deployment risk level (CRITICAL/HIGH/MEDIUM/LOW)
   - Required testing
   - Immediate actions needed

Format your response clearly with sections for each changed line and an overall summary.
Focus on ACTIONABLE insights for SME review before production deployment."""

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
                "max_tokens": 4096,
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
    
    def _generate_visualization(self, claude_response, file_path, changed_lines, 
                                affected_vars, affected_funcs):
        """Generate HTML visualization from Claude response"""
        try:
            # Extract text from Claude response
            analysis_text = ""
            for content_block in claude_response:
                if content_block.get("type") == "text":
                    analysis_text += content_block.get("text", "")
            
            if not analysis_text:
                print("⚠️  No analysis text received from Claude")
                return
            
            # Generate HTML visualization
            html_content = self._create_html_visualization(
                file_path, changed_lines, affected_vars, affected_funcs, analysis_text
            )
            
            # Save and open
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"impact_analysis_{timestamp}.html"
            temp_path = os.path.join(tempfile.gettempdir(), file_name)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Visualization saved to: {temp_path}")
            print("🌐 Opening in browser...")
            webbrowser.open('file://' + temp_path)
                
        except Exception as e:
            print(f"❌ Failed to generate visualization: {e}")
            import traceback
            traceback.print_exc()
    
    def _build_dependency_graph(self, file_path, changed_lines, affected_vars, affected_funcs):
        """Build dependency graph data structure for visualization"""
        from analyzer import build_full_graph_for_file
        
        # Get the full dependency graph
        full_graph = build_full_graph_for_file(file_path)
        
        nodes = []
        edges = []
        
        # Create nodes for changed lines (left side)
        x_line = 100
        y_start = 100
        y_spacing = 120
        
        for idx, line_num in enumerate(sorted(changed_lines)):
            node_id = f"line{line_num}"
            nodes.append({
                'id': node_id,
                'label': f'Line {line_num}',
                'type': 'changed',
                'severity': 'HIGH',
                'x': x_line,
                'y': y_start + (idx * y_spacing),
                'description': f'Code changed on line {line_num}',
                'impact': 'Source of change - propagates to dependent code'
            })
        
        # Create nodes for affected functions (middle)
        x_func = 350
        func_y = y_start
        func_spacing = 100
        
        for idx, func in enumerate(sorted(affected_funcs)):
            func_short = func.split('.')[-1] if '.' in func else func
            node_id = f"func_{func}"
            
            # Determine severity based on dependencies
            deps = full_graph.get('functions', {}).get(func, {}).get('depends_on', [])
            severity = 'HIGH' if len(deps) > 3 else 'MEDIUM'
            
            nodes.append({
                'id': node_id,
                'label': func_short,
                'type': 'affected',
                'severity': severity,
                'x': x_func,
                'y': func_y + (idx * func_spacing),
                'description': f'Function: {func}',
                'impact': f'Depends on {len(deps)} items',
                'funcsAffected': 1,
                'varsAffected': len([d for d in deps if d in full_graph.get('variables', {})])
            })
            
            # Create edges from changed lines to this function
            for line_num in changed_lines:
                edges.append({
                    'from': f"line{line_num}",
                    'to': node_id
                })
        
        # Create nodes for affected variables (right side)
        x_var = 600
        var_y = y_start
        var_spacing = 80
        
        for idx, var in enumerate(sorted(affected_vars)):
            var_short = var.split('.')[-1] if '.' in var else var
            node_id = f"var_{var}"
            
            # Determine severity
            deps = full_graph.get('variables', {}).get(var, {}).get('depends_on', [])
            severity = 'MEDIUM' if len(deps) > 2 else 'LOW'
            
            nodes.append({
                'id': node_id,
                'label': var_short,
                'type': 'affected',
                'severity': severity,
                'x': x_var,
                'y': var_y + (idx * var_spacing),
                'description': f'Variable: {var}',
                'impact': 'Modified due to upstream changes',
                'varsAffected': 1,
                'funcsAffected': 0
            })
            
            # Create edges from functions to variables
            for func in affected_funcs:
                func_node_id = f"func_{func}"
                # Check if this variable depends on this function
                var_deps = full_graph.get('variables', {}).get(var, {}).get('depends_on', [])
                if any(func in dep for dep in var_deps):
                    edges.append({
                        'from': func_node_id,
                        'to': node_id
                    })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def _create_html_visualization(self, file_path, changed_lines, affected_vars, 
                                   affected_funcs, claude_analysis):
        """Create standalone HTML with embedded React visualization using React.createElement"""
        
        file_name = os.path.basename(file_path)
        changed_lines_str = ", ".join(map(str, sorted(changed_lines)))
        
        # Build dependency graph data
        graph_data = self._build_dependency_graph(file_path, changed_lines, affected_vars, affected_funcs)
        graph_json = json.dumps(graph_data)
        
        # Escape analysis text for JavaScript
        claude_analysis_safe = claude_analysis.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        
        # Convert Python lists to JavaScript arrays
        vars_list = json.dumps([v.split('.')[-1] for v in sorted(affected_vars)] if affected_vars else [])
        funcs_list = json.dumps([f.split('.')[-1] for f in sorted(affected_funcs)] if affected_funcs else [])
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impact Analysis - {file_name}</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: #f3f4f6;
        }}
    </style>
</head>
<body>
    <div id="root"></div>
    
    <script>
        const React = window.React;
        const ReactDOM = window.ReactDOM;
        const e = React.createElement;
        const useState = React.useState;
        
        // Icons
        const AlertCircle = (props) => e('svg', Object.assign({{}}, props, {{
            xmlns: "http://www.w3.org/2000/svg",
            width: "24",
            height: "24",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2"
        }}),
            e('circle', {{ cx: "12", cy: "12", r: "10" }}),
            e('line', {{ x1: "12", y1: "8", x2: "12", y2: "12" }}),
            e('line', {{ x1: "12", y1: "16", x2: "12.01", y2: "16" }})
        );
        
        const GitBranch = (props) => e('svg', Object.assign({{}}, props, {{
            xmlns: "http://www.w3.org/2000/svg",
            width: "24",
            height: "24",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2"
        }}),
            e('line', {{ x1: "6", y1: "3", x2: "6", y2: "15" }}),
            e('circle', {{ cx: "18", cy: "6", r: "3" }}),
            e('circle', {{ cx: "6", cy: "18", r: "3" }}),
            e('path', {{ d: "M18 9a9 9 0 0 1-9 9" }})
        );
        
        const TrendingUp = (props) => e('svg', Object.assign({{}}, props, {{
            xmlns: "http://www.w3.org/2000/svg",
            width: "24",
            height: "24",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2"
        }}),
            e('polyline', {{ points: "22 7 13.5 15.5 8.5 10.5 2 17" }}),
            e('polyline', {{ points: "16 7 22 7 22 13" }})
        );
        
        const FileCode = (props) => e('svg', Object.assign({{}}, props, {{
            xmlns: "http://www.w3.org/2000/svg",
            width: "24",
            height: "24",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "2"
        }}),
            e('path', {{ d: "M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" }}),
            e('polyline', {{ points: "14 2 14 8 20 8" }})
        );
        
        // Dependency Graph Component
        function DependencyGraph(props) {{
            const data = props.data;
            const selectedNodeState = useState(null);
            const selectedNode = selectedNodeState[0];
            const setSelectedNode = selectedNodeState[1];
            
            if (!data || !data.nodes || data.nodes.length === 0) {{
                return e('div', {{ className: "text-center py-8 text-gray-500" }}, 
                    'No dependency graph available'
                );
            }}
            
            const getSeverityColor = (severity) => {{
                if (severity === 'HIGH') return '#ef4444';
                if (severity === 'MEDIUM') return '#f59e0b';
                if (severity === 'LOW') return '#10b981';
                if (severity === 'VARIABLE') return '#3b82f6';
                return '#6b7280';
            }};
            
            const getSeverityBg = (severity) => {{
                if (severity === 'HIGH') return '#fee2e2';
                if (severity === 'MEDIUM') return '#fef3c7';
                if (severity === 'LOW') return '#d1fae5';
                if (severity === 'VARIABLE') return '#dbeafe';
                return '#f3f4f6';
            }};
            
            return e('div', null,
                e('div', {{ 
                    className: "relative bg-white rounded-lg border",
                    style: {{ height: '600px' }}
                }},
                    e('svg', {{ 
                        width: "100%",
                        height: "100%",
                        className: "absolute inset-0"
                    }},
                        e('defs', null,
                            e('marker', {{
                                id: "arrowhead",
                                markerWidth: "10",
                                markerHeight: "10",
                                refX: "9",
                                refY: "3",
                                orient: "auto"
                            }},
                                e('polygon', {{
                                    points: "0 0, 10 3, 0 6",
                                    fill: "#6b7280"
                                }})
                            )
                        ),
                        data.edges.map((edge, i) => {{
                            const from = data.nodes.find(n => n.id === edge.from);
                            const to = data.nodes.find(n => n.id === edge.to);
                            if (!from || !to) return null;
                            
                            return e('line', {{
                                key: i,
                                x1: from.x,
                                y1: from.y,
                                x2: to.x,
                                y2: to.y,
                                stroke: "#9ca3af",
                                strokeWidth: "2",
                                markerEnd: "url(#arrowhead)",
                                opacity: "0.6"
                            }});
                        }})
                    ),
                    data.nodes.map((node) => 
                        e('div', {{
                            key: node.id,
                            className: "absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all hover:scale-110",
                            style: {{
                                left: node.x + 'px',
                                top: node.y + 'px',
                                backgroundColor: getSeverityBg(node.severity),
                                borderColor: getSeverityColor(node.severity),
                                borderWidth: '2px',
                                borderStyle: 'solid',
                                maxWidth: '180px',
                                zIndex: 10
                            }},
                            onClick: () => setSelectedNode(node)
                        }},
                            e('div', {{ className: "rounded-lg p-3 shadow-lg" }},
                                e('div', {{ 
                                    className: "text-xs font-bold mb-1",
                                    style: {{ color: getSeverityColor(node.severity) }}
                                }},
                                    node.type === 'changed' ? '🔴 CHANGED' : '⚠️ AFFECTED'
                                ),
                                e('div', {{ className: "text-sm font-semibold text-gray-900 break-words" }},
                                    node.label
                                ),
                                e('div', {{ 
                                    className: "text-xs px-2 py-1 rounded mt-2 text-white font-semibold",
                                    style: {{ backgroundColor: getSeverityColor(node.severity) }}
                                }},
                                    node.severity
                                )
                            )
                        )
                    )
                ),
                selectedNode && e('div', {{ 
                    className: "mt-4 bg-blue-50 border-l-4 border-blue-500 p-4 rounded"
                }},
                    e('h4', {{ className: "font-bold text-blue-900 mb-2" }}, selectedNode.label),
                    e('p', {{ className: "text-sm text-blue-800 mb-2" }}, selectedNode.description),
                    e('p', {{ className: "text-sm text-blue-700" }},
                        e('strong', null, 'Impact: '),
                        selectedNode.impact
                    )
                )
            );
        }}
        
        // Main Component
        function ImpactAnalysis() {{
            const activeTabState = useState('dependency');
            const activeTab = activeTabState[0];
            const setActiveTab = activeTabState[1];
            
            const data = {{
                fileName: '{file_name}',
                changedLines: '{changed_lines_str}',
                varsAffected: {len(affected_vars)},
                funcsAffected: {len(affected_funcs)},
                analysis: `{claude_analysis_safe}`,
                dependencyGraph: {graph_json},
                affectedVars: {vars_list},
                affectedFuncs: {funcs_list}
            }};
            
            return e('div', {{ className: "min-h-screen bg-gray-50 p-6" }},
                e('div', {{ className: "max-w-6xl mx-auto" }},
                    e('div', {{ className: "bg-white rounded-lg shadow-sm p-6 mb-6" }},
                        e('div', {{ className: "flex items-center mb-4" }},
                            e(FileCode, {{ className: "w-8 h-8 text-blue-500 mr-3" }}),
                            e('div', null,
                                e('h1', {{ className: "text-3xl font-bold text-gray-900" }}, 'Code Impact Analysis'),
                                e('p', {{ className: "text-gray-600 mt-1" }}, 'Production Deployment Risk Assessment')
                            )
                        ),
                        e('div', {{ className: "grid grid-cols-4 gap-4 mt-6" }},
                            e('div', {{ className: "bg-blue-50 rounded-lg p-4" }},
                                e('div', {{ className: "text-blue-600 text-sm font-semibold" }}, 'FILE'),
                                e('div', {{ className: "text-xl font-bold text-gray-900 mt-1" }}, data.fileName)
                            ),
                            e('div', {{ className: "bg-purple-50 rounded-lg p-4" }},
                                e('div', {{ className: "text-purple-600 text-sm font-semibold" }}, 'CHANGED LINES'),
                                e('div', {{ className: "text-xl font-bold text-gray-900 mt-1" }}, data.changedLines)
                            ),
                            e('div', {{ className: "bg-orange-50 rounded-lg p-4" }},
                                e('div', {{ className: "text-orange-600 text-sm font-semibold" }}, 'VARIABLES'),
                                e('div', {{ className: "text-xl font-bold text-gray-900 mt-1" }}, data.varsAffected)
                            ),
                            e('div', {{ className: "bg-green-50 rounded-lg p-4" }},
                                e('div', {{ className: "text-green-600 text-sm font-semibold" }}, 'FUNCTIONS'),
                                e('div', {{ className: "text-xl font-bold text-gray-900 mt-1" }}, data.funcsAffected)
                            )
                        )
                    ),
                    e('div', {{ className: "bg-white rounded-lg shadow-sm mb-6" }},
                        e('div', {{ className: "flex border-b" }},
                            e('button', {{
                                className: 'px-6 py-3 font-medium transition ' + (activeTab === 'dependency' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:text-blue-600'),
                                onClick: () => setActiveTab('dependency')
                            }},
                                e('div', {{ className: "flex items-center gap-2" }},
                                    e(GitBranch, {{ className: "w-4 h-4" }}),
                                    e('span', null, 'Dependency Graph')
                                )
                            ),
                            e('button', {{
                                className: 'px-6 py-3 font-medium transition ' + (activeTab === 'summary' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:text-blue-600'),
                                onClick: () => setActiveTab('summary')
                            }},
                                e('div', {{ className: "flex items-center gap-2" }},
                                    e(AlertCircle, {{ className: "w-4 h-4" }}),
                                    e('span', null, 'Impact Summary')
                                )
                            ),
                            e('button', {{
                                className: 'px-6 py-3 font-medium transition ' + (activeTab === 'analysis' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:text-blue-600'),
                                onClick: () => setActiveTab('analysis')
                            }},
                                e('div', {{ className: "flex items-center gap-2" }},
                                    e(TrendingUp, {{ className: "w-4 h-4" }}),
                                    e('span', null, 'Claude Analysis')
                                )
                            )
                        )
                    ),
                    e('div', {{ className: "bg-white rounded-lg shadow-sm p-6" }},
                        activeTab === 'dependency' && e('div', null,
                            e('h2', {{ className: "text-2xl font-bold mb-6" }}, 'Dependency Graph'),
                            e(DependencyGraph, {{ data: data.dependencyGraph }}),
                            e('div', {{ className: "grid grid-cols-2 gap-6 mt-8" }},
                                e('div', null,
                                    e('h3', {{ className: "font-semibold text-gray-900 mb-3" }}, 'Affected Variables (' + data.varsAffected + ')'),
                                    e('div', {{ className: "bg-gray-50 rounded p-4 max-h-80 overflow-y-auto" }},
                                        data.affectedVars.length > 0 
                                            ? e('div', {{ className: "space-y-2" }},
                                                data.affectedVars.map((v, i) => 
                                                    e('div', {{ 
                                                        key: i,
                                                        className: "text-sm font-mono bg-white p-2 rounded border"
                                                    }}, v)
                                                )
                                            )
                                            : e('p', {{ className: "text-gray-500 text-sm" }}, 'No variables affected')
                                    )
                                ),
                                e('div', null,
                                    e('h3', {{ className: "font-semibold text-gray-900 mb-3" }}, 'Affected Functions (' + data.funcsAffected + ')'),
                                    e('div', {{ className: "bg-gray-50 rounded p-4 max-h-80 overflow-y-auto" }},
                                        data.affectedFuncs.length > 0
                                            ? e('div', {{ className: "space-y-2" }},
                                                data.affectedFuncs.map((f, i) => 
                                                    e('div', {{ 
                                                        key: i,
                                                        className: "text-sm font-mono bg-white p-2 rounded border"
                                                    }}, f)
                                                )
                                            )
                                            : e('p', {{ className: "text-gray-500 text-sm" }}, 'No functions affected')
                                    )
                                )
                            )
                        ),
                        activeTab === 'summary' && e('div', null,
                            e('h2', {{ className: "text-2xl font-bold mb-4" }}, 'Impact Summary'),
                            e('div', {{ className: "space-y-4" }},
                                e('div', {{ className: "bg-red-50 border-l-4 border-red-500 p-4" }},
                                    e('h3', {{ className: "font-semibold text-red-900 flex items-center gap-2" }},
                                        e(AlertCircle, {{ className: "w-5 h-5" }}),
                                        'Changed Lines: ' + data.changedLines
                                    ),
                                    e('p', {{ className: "text-red-800 mt-2" }},
                                        'Affects ' + data.varsAffected + ' variable(s) and ' + data.funcsAffected + ' function(s) across your codebase.'
                                    )
                                ),
                                e('div', {{ className: "bg-blue-50 border-l-4 border-blue-500 p-4" }},
                                    e('h3', {{ className: "font-semibold text-blue-900" }}, 'Dependencies Tracked'),
                                    e('p', {{ className: "text-blue-800 mt-2" }},
                                        'All downstream impacts identified. Check the dependency graph for visual representation.'
                                    )
                                ),
                                e('div', {{ className: "bg-yellow-50 border-l-4 border-yellow-500 p-4" }},
                                    e('h3', {{ className: "font-semibold text-yellow-900" }}, 'Production Recommendation'),
                                    e('p', {{ className: "text-yellow-800 mt-2" }},
                                        "Review Claude's analysis before deployment. Focus on risk assessment and testing requirements."
                                    )
                                )
                            )
                        ),
                        activeTab === 'analysis' && e('div', null,
                            e('h2', {{ className: "text-2xl font-bold mb-4" }}, 'Claude AI Analysis'),
                            e('div', {{ className: "bg-gray-50 rounded-lg p-6 whitespace-pre-wrap text-gray-800" }},
                                data.analysis
                            )
                        )
                    ),
                    e('div', {{ className: "mt-6 bg-white rounded-lg shadow-sm p-4 text-center text-sm text-gray-600" }},
                        'Generated on ' + new Date().toLocaleString() + ' • Powered by Claude AI'
                    )
                )
            );
        }}
        
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(e(ImpactAnalysis));
    </script>
</body>
</html>"""
        
        return html_template
