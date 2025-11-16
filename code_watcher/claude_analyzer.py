# claude_analyzer.py - Enhanced UI version
import json
import os
import webbrowser
import tempfile
from datetime import datetime

class ClaudeImpactAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.anthropic.com/v1/messages"
        
        try:
            import requests
            self.requests = requests
        except ImportError:
            print("⚠️  'requests' library not found. Install it with: pip install requests")
            self.requests = None
    
    def generate_impact_analysis(self, file_path, changed_lines, affected_vars, affected_funcs, 
                                 added_vars, added_funcs, deleted_vars, deleted_funcs,
                                 affected_by_deletion, code_content):
        if not self.requests:
            print("❌ Cannot proceed without 'requests' library")
            return None
        
        prompt = self._build_analysis_prompt(
            file_path, changed_lines, affected_vars, affected_funcs,
            added_vars, added_funcs, deleted_vars, deleted_funcs,
            affected_by_deletion, code_content
        )
        
        response = self._call_claude_api(prompt)
        
        if response:
            self._generate_visualization(response, file_path, changed_lines, 
                                        affected_vars, affected_funcs)
            return response
        
        return None
    
    def _build_analysis_prompt(self, file_path, changed_lines, affected_vars, affected_funcs,
                               added_vars, added_funcs, deleted_vars, deleted_funcs,
                               affected_by_deletion, code_content):
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
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]
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
        try:
            analysis_text = ""
            for content_block in claude_response:
                if content_block.get("type") == "text":
                    analysis_text += content_block.get("text", "")
            
            if not analysis_text:
                print("⚠️  No analysis text received from Claude")
                return
            
            html_content = self._create_html_visualization(
                file_path, changed_lines, affected_vars, affected_funcs, analysis_text
            )
            
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
    
    def _build_dependency_graphs_per_line(self, file_path, changed_lines, affected_vars, affected_funcs):
        from analyzer import build_full_graph_for_file, analyze_file_changes
        
        full_graph = build_full_graph_for_file(file_path)
        graphs_by_line = {}
        all_func_nodes = {}
        all_var_nodes = {}
        
        for line_num in sorted(changed_lines):
            line_affected_vars, line_affected_funcs = analyze_file_changes(file_path, [line_num])
            
            for func in line_affected_funcs:
                if func not in all_func_nodes:
                    all_func_nodes[func] = set()
                all_func_nodes[func].add(line_num)
            
            for var in line_affected_vars:
                if var not in all_var_nodes:
                    all_var_nodes[var] = set()
                all_var_nodes[var].add(line_num)
            
            graphs_by_line[line_num] = {
                'affected_vars': line_affected_vars,
                'affected_funcs': line_affected_funcs
            }
        
        all_graphs = []
        y_offset_per_graph = 900
        
        for idx, line_num in enumerate(sorted(changed_lines)):
            nodes = []
            edges = []
            graph_y_base = idx * y_offset_per_graph + 150
            line_data = graphs_by_line[line_num]
            
            source_node_id = f"line{line_num}"
            nodes.append({
                'id': source_node_id,
                'label': f'Line {line_num}',
                'type': 'changed',
                'severity': 'HIGH',
                'x': 120,
                'y': graph_y_base,
                'description': f'Code changed on line {line_num}',
                'impact': 'Source of change - this line was modified',
                'lineNumber': line_num,
                'severityReason': 'All changed lines are marked HIGH as they are the root cause of downstream impacts'
            })
            
            x_func = 400
            func_y = graph_y_base
            func_spacing = 120
            
            for fidx, func in enumerate(sorted(line_data['affected_funcs'])):
                func_short = func.split('.')[-1] if '.' in func else func
                node_id = f"func_{func}_line{line_num}"
                
                is_shared = len(all_func_nodes.get(func, set())) > 1
                affected_by_lines = list(all_func_nodes.get(func, {line_num}))
                
                deps = full_graph.get('functions', {}).get(func, {}).get('depends_on', [])
                num_deps = len(deps)
                
                if num_deps > 5:
                    severity = 'HIGH'
                    reason = f'HIGH: {num_deps} dependencies (>5) - complex logic, wide impact'
                elif num_deps > 2:
                    severity = 'MEDIUM'
                    reason = f'MEDIUM: {num_deps} dependencies (3-5) - moderate complexity'
                else:
                    severity = 'LOW'
                    reason = f'LOW: {num_deps} dependencies (≤2) - simple, isolated'
                
                nodes.append({
                    'id': node_id,
                    'label': func_short,
                    'type': 'affected',
                    'severity': severity,
                    'x': x_func,
                    'y': func_y + (fidx * func_spacing),
                    'description': f'Function: {func}',
                    'impact': f'Has {num_deps} dependencies. Changes may affect dependent code',
                    'isShared': is_shared,
                    'affectedByLines': affected_by_lines,
                    'lineNumber': line_num,
                    'severityReason': reason,
                    'dependencyCount': num_deps
                })
                
                edges.append({'from': source_node_id, 'to': node_id})
            
            x_var = 700
            var_y = graph_y_base
            var_spacing = 100
            
            for vidx, var in enumerate(sorted(line_data['affected_vars'])):
                var_short = var.split('.')[-1] if '.' in var else var
                node_id = f"var_{var}_line{line_num}"
                
                is_shared = len(all_var_nodes.get(var, set())) > 1
                affected_by_lines = list(all_var_nodes.get(var, {line_num}))
                
                deps = full_graph.get('variables', {}).get(var, {}).get('depends_on', [])
                num_deps = len(deps)
                
                if num_deps > 4:
                    severity = 'MEDIUM'
                    reason = f'MEDIUM: {num_deps} dependencies (>4) - wide propagation'
                elif num_deps > 0:
                    severity = 'LOW'
                    reason = f'LOW: {num_deps} dependencies (1-4) - limited scope'
                else:
                    severity = 'LOW'
                    reason = 'LOW: No dependencies - isolated change'
                
                nodes.append({
                    'id': node_id,
                    'label': var_short,
                    'type': 'affected',
                    'severity': severity,
                    'x': x_var,
                    'y': var_y + (vidx * var_spacing),
                    'description': f'Variable: {var}',
                    'impact': f'Depends on {num_deps} items',
                    'isShared': is_shared,
                    'affectedByLines': affected_by_lines,
                    'lineNumber': line_num,
                    'severityReason': reason,
                    'dependencyCount': num_deps
                })
                
                for func in line_data['affected_funcs']:
                    func_node_id = f"func_{func}_line{line_num}"
                    var_deps = full_graph.get('variables', {}).get(var, {}).get('depends_on', [])
                    if any(func in dep for dep in var_deps):
                        edges.append({'from': func_node_id, 'to': node_id})
            
            all_graphs.append({'lineNumber': line_num, 'nodes': nodes, 'edges': edges})
        
        cross_graph_edges = []
        
        for func, affecting_lines in all_func_nodes.items():
            if len(affecting_lines) > 1:
                lines_list = sorted(affecting_lines)
                for i in range(len(lines_list) - 1):
                    cross_graph_edges.append({
                        'from': f"func_{func}_line{lines_list[i]}",
                        'to': f"func_{func}_line{lines_list[i + 1]}",
                        'type': 'shared'
                    })
        
        for var, affecting_lines in all_var_nodes.items():
            if len(affecting_lines) > 1:
                lines_list = sorted(affecting_lines)
                for i in range(len(lines_list) - 1):
                    cross_graph_edges.append({
                        'from': f"var_{var}_line{lines_list[i]}",
                        'to': f"var_{var}_line{lines_list[i + 1]}",
                        'type': 'shared'
                    })
        
        return {
            'graphs': all_graphs,
            'crossGraphEdges': cross_graph_edges,
            'sharedFunctions': {k: list(v) for k, v in all_func_nodes.items() if len(v) > 1},
            'sharedVariables': {k: list(v) for k, v in all_var_nodes.items() if len(v) > 1}
        }
    
    def _parse_claude_analysis(self, analysis_text):
        """Parse Claude's analysis into structured sections"""
        sections = {
            'overview': '',
            'line_analyses': [],
            'overall_assessment': '',
            'risk_level': 'MEDIUM',
            'testing_required': [],
            'immediate_actions': []
        }
        
        lines = analysis_text.split('\n')
        current_section = 'overview'
        current_line_analysis = None
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect risk level
            if 'CRITICAL' in line_stripped.upper():
                sections['risk_level'] = 'CRITICAL'
            elif 'HIGH' in line_stripped.upper() and 'RISK' in line_stripped.upper():
                sections['risk_level'] = 'HIGH'
            elif 'LOW' in line_stripped.upper() and 'RISK' in line_stripped.upper():
                sections['risk_level'] = 'LOW'
            
            # Detect section headers
            if 'line' in line_stripped.lower() and any(c.isdigit() for c in line_stripped):
                if current_line_analysis:
                    sections['line_analyses'].append(current_line_analysis)
                current_line_analysis = {'title': line_stripped, 'content': ''}
                current_section = 'line_analysis'
            elif 'overall' in line_stripped.lower() or 'assessment' in line_stripped.lower():
                if current_line_analysis:
                    sections['line_analyses'].append(current_line_analysis)
                    current_line_analysis = None
                current_section = 'overall'
            elif 'testing' in line_stripped.lower() or 'test' in line_stripped.lower():
                current_section = 'testing'
            elif 'action' in line_stripped.lower() or 'recommendation' in line_stripped.lower():
                current_section = 'actions'
            else:
                # Add content to current section
                if current_section == 'line_analysis' and current_line_analysis:
                    current_line_analysis['content'] += line + '\n'
                elif current_section == 'overall':
                    sections['overall_assessment'] += line + '\n'
                elif current_section == 'testing':
                    if line_stripped and line_stripped.startswith(('-', '•', '*', '1', '2', '3')):
                        sections['testing_required'].append(line_stripped.lstrip('-•*123456789. '))
                elif current_section == 'actions':
                    if line_stripped and line_stripped.startswith(('-', '•', '*', '1', '2', '3')):
                        sections['immediate_actions'].append(line_stripped.lstrip('-•*123456789. '))
                elif current_section == 'overview':
                    sections['overview'] += line + '\n'
        
        if current_line_analysis:
            sections['line_analyses'].append(current_line_analysis)
        
        return sections
    
    def _create_html_visualization(self, file_path, changed_lines, affected_vars, affected_funcs, claude_analysis):
        file_name = os.path.basename(file_path)
        changed_lines_str = ", ".join(map(str, sorted(changed_lines)))
        
        graph_data = self._build_dependency_graphs_per_line(file_path, changed_lines, affected_vars, affected_funcs)
        graph_json_str = json.dumps(graph_data)
        
        # Parse the analysis
        parsed_analysis = self._parse_claude_analysis(claude_analysis)
        parsed_json_str = json.dumps(parsed_analysis)
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Impact Analysis - {file_name}</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ 
            margin: 0; 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .glass-effect {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        
        .severity-badge {{
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: .7; }}
        }}
        
        .node-card {{
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        .node-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }}
        
        .markdown-content h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            color: #1f2937;
        }}
        
        .markdown-content h2 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-top: 1.25rem;
            margin-bottom: 0.75rem;
            color: #374151;
        }}
        
        .markdown-content h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            color: #4b5563;
        }}
        
        .markdown-content p {{
            margin-bottom: 1rem;
            line-height: 1.625;
        }}
        
        .markdown-content ul, .markdown-content ol {{
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .markdown-content li {{
            margin-bottom: 0.5rem;
        }}
        
        .markdown-content code {{
            background: #f3f4f6;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
        }}
        
        .markdown-content pre {{
            background: #1f2937;
            color: #f9fafb;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            margin-bottom: 1rem;
        }}
        
        .markdown-content strong {{
            font-weight: 600;
            color: #111827;
        }}
        
        .markdown-content em {{
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script>
        const e = React.createElement;
        const useState = React.useState;
        const useEffect = React.useEffect;
        
        const graphData = {graph_json_str};
        const parsedAnalysis = {parsed_json_str};
        const fileName = "{file_name}";
        const changedLinesStr = "{changed_lines_str}";
        const affectedFuncsCount = {len(affected_funcs)};
        const affectedVarsCount = {len(affected_vars)};
        
        function App() {{
            const [zoom, setZoom] = useState(1);
            const [selectedNode, setSelectedNode] = useState(null);
            const [activeTab, setActiveTab] = useState('overview');
            const [showSeverityModal, setShowSeverityModal] = useState(false);
            const [severityNode, setSeverityNode] = useState(null);
            
            const getSeverityColor = (severity) => {{
                if (severity === 'HIGH') return '#dc2626';
                if (severity === 'MEDIUM') return '#f59e0b';
                return '#16a34a';
            }};
            
            const getSeverityBg = (severity) => {{
                if (severity === 'HIGH') return 'linear-gradient(135deg, #fecaca 0%, #fca5a5 100%)';
                if (severity === 'MEDIUM') return 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)';
                return 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)';
            }};
            
            const getRiskLevelColor = (risk) => {{
                if (risk === 'CRITICAL') return '#991b1b';
                if (risk === 'HIGH') return '#dc2626';
                if (risk === 'MEDIUM') return '#f59e0b';
                return '#16a34a';
            }};
            
            const totalHeight = graphData.graphs.length * 900;
            const allNodes = [];
            const allEdges = [];
            
            graphData.graphs.forEach(graph => {{
                allNodes.push(...graph.nodes);
                allEdges.push(...graph.edges);
            }});
            
            const handleNodeClick = (node) => {{
                setSelectedNode(node);
                setSeverityNode(node);
                setShowSeverityModal(true);
            }};
            
            return e('div', {{ className: 'min-h-screen p-8' }},
                e('div', {{ className: 'max-w-7xl mx-auto' }},
                    // Header
                    e('div', {{ className: 'glass-effect p-8 rounded-2xl shadow-2xl mb-8' }},
                        e('div', {{ className: 'flex items-center justify-between' }},
                            e('div', null,
                                e('h1', {{ className: 'text-4xl font-bold text-gray-900 mb-2' }}, 
                                    '🔍 Impact Analysis Report'
                                ),
                                e('p', {{ className: 'text-xl text-gray-600' }}, fileName)
                            ),
                            e('div', {{ 
                                className: 'px-6 py-3 rounded-xl font-bold text-white text-lg shadow-lg',
                                style: {{ backgroundColor: getRiskLevelColor(parsedAnalysis.risk_level) }}
                            }}, 
                                parsedAnalysis.risk_level + ' RISK'
                            )
                        ),
                        e('div', {{ className: 'mt-6 flex gap-6 text-sm' }},
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('span', {{ className: 'text-2xl' }}, '📝'),
                                e('span', {{ className: 'text-gray-700' }}, 'Lines: ' + changedLinesStr)
                            ),
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('span', {{ className: 'text-2xl' }}, '⚙️'),
                                e('span', {{ className: 'text-gray-700' }}, affectedFuncsCount + ' functions affected')
                            ),
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('span', {{ className: 'text-2xl' }}, '📊'),
                                e('span', {{ className: 'text-gray-700' }}, affectedVarsCount + ' variables affected')
                            )
                        )
                    ),
                    
                    // Tab Navigation
                    e('div', {{ className: 'glass-effect p-2 rounded-2xl shadow-lg mb-8' }},
                        e('div', {{ className: 'flex gap-2' }},
                            ['overview', 'graph', 'details'].map(tab => 
                                e('button', {{
                                    key: tab,
                                    onClick: () => setActiveTab(tab),
                                    className: 'flex-1 px-6 py-3 rounded-xl font-semibold transition-all duration-200 ' + 
                                        (activeTab === tab 
                                            ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg' 
                                            : 'text-gray-600 hover:bg-gray-100')
                                }}, 
                                    tab === 'overview' ? '📋 Overview' : 
                                    tab === 'graph' ? '🕸️ Dependency Graph' : 
                                    '📑 Detailed Analysis'
                                )
                            )
                        )
                    ),
                    
                    // Overview Tab
                    activeTab === 'overview' && e('div', {{ className: 'space-y-6' }},
                        // Key Findings
                        e('div', {{ className: 'glass-effect p-6 rounded-2xl shadow-lg' }},
                            e('h2', {{ className: 'text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2' }},
                                e('span', null, '🎯'),
                                'Key Findings'
                            ),
                            e('div', {{ className: 'markdown-content text-gray-700' }},
                                parsedAnalysis.overview || 'Analysis overview will appear here.'
                            )
                        ),
                        
                        // Immediate Actions
                        parsedAnalysis.immediate_actions.length > 0 && e('div', {{ className: 'glass-effect p-6 rounded-2xl shadow-lg' }},
                            e('h2', {{ className: 'text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2' }},
                                e('span', null, '⚡'),
                                'Immediate Actions Required'
                            ),
                            e('div', {{ className: 'space-y-3' }},
                                parsedAnalysis.immediate_actions.map((action, idx) =>
                                    e('div', {{ 
                                        key: idx,
                                        className: 'flex items-start gap-3 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg'
                                    }},
                                        e('span', {{ className: 'text-red-600 font-bold text-lg' }}, (idx + 1) + '.'),
                                        e('p', {{ className: 'text-gray-800 flex-1' }}, action)
                                    )
                                )
                            )
                        ),
                        
                        // Testing Required
                        parsedAnalysis.testing_required.length > 0 && e('div', {{ className: 'glass-effect p-6 rounded-2xl shadow-lg' }},
                            e('h2', {{ className: 'text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2' }},
                                e('span', null, '🧪'),
                                'Testing Required'
                            ),
                            e('div', {{ className: 'space-y-2' }},
                                parsedAnalysis.testing_required.map((test, idx) =>
                                    e('div', {{ 
                                        key: idx,
                                        className: 'flex items-center gap-3 p-3 bg-blue-50 rounded-lg'
                                    }},
                                        e('span', {{ className: 'text-blue-600' }}, '✓'),
                                        e('p', {{ className: 'text-gray-800' }}, test)
                                    )
                                )
                            )
                        )
                    ),
                    
                    // Graph Tab
                    activeTab === 'graph' && e('div', {{ className: 'glass-effect p-6 rounded-2xl shadow-lg' }},
                        // Zoom controls
                        e('div', {{ className: 'flex items-center gap-4 mb-6' }},
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('button', {{
                                    onClick: () => setZoom(Math.max(0.5, zoom - 0.2)),
                                    className: 'px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-blue-700 shadow-md'
                                }}, '🔍 Zoom Out'),
                                e('span', {{ className: 'px-4 py-2 bg-gray-100 rounded-lg font-bold text-gray-800' }}, 
                                    (zoom * 100).toFixed(0) + '%'
                                ),
                                e('button', {{
                                    onClick: () => setZoom(Math.min(2, zoom + 0.2)),
                                    className: 'px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-blue-700 shadow-md'
                                }}, '🔍 Zoom In')
                            ),
                            e('div', {{ className: 'ml-auto text-sm text-gray-600' }},
                                '💡 Click any node to see severity details'
                            )
                        ),
                        
                        // Legend
                        e('div', {{ className: 'flex gap-4 mb-6 p-4 bg-gray-50 rounded-lg' }},
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('div', {{ className: 'w-4 h-4 rounded bg-red-200 border-2 border-red-600' }}),
                                e('span', {{ className: 'text-sm font-medium' }}, 'HIGH')
                            ),
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('div', {{ className: 'w-4 h-4 rounded bg-yellow-200 border-2 border-yellow-600' }}),
                                e('span', {{ className: 'text-sm font-medium' }}, 'MEDIUM')
                            ),
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('div', {{ className: 'w-4 h-4 rounded bg-green-200 border-2 border-green-600' }}),
                                e('span', {{ className: 'text-sm font-medium' }}, 'LOW')
                            ),
                            e('div', {{ className: 'flex items-center gap-2 ml-4' }},
                                e('div', {{ className: 'w-4 h-4 rounded border-2 border-dashed border-blue-600' }}),
                                e('span', {{ className: 'text-sm font-medium' }}, 'Shared Node')
                            )
                        ),
                        
                        // Graph container
                        e('div', {{ className: 'overflow-auto border-2 border-gray-200 rounded-xl', style: {{ maxHeight: '700px' }} }},
                            e('div', {{ 
                                className: 'relative bg-gradient-to-br from-gray-50 to-gray-100',
                                style: {{ 
                                    height: (totalHeight * zoom) + 'px',
                                    width: (900 * zoom) + 'px',
                                    transform: 'scale(' + zoom + ')',
                                    transformOrigin: 'top left'
                                }}
                            }},
                                // SVG for edges
                                e('svg', {{ width: 900, height: totalHeight, className: 'absolute' }},
                                    e('defs', null,
                                        e('marker', {{ id: 'arrowhead', markerWidth: 10, markerHeight: 10, refX: 9, refY: 3, orient: 'auto' }},
                                            e('polygon', {{ points: '0 0,10 3,0 6', fill: '#6b7280' }})
                                        ),
                                        e('marker', {{ id: 'arrowhead-blue', markerWidth: 10, markerHeight: 10, refX: 9, refY: 3, orient: 'auto' }},
                                            e('polygon', {{ points: '0 0,10 3,0 6', fill: '#3b82f6' }})
                                        ),
                                        e('filter', {{ id: 'glow' }},
                                            e('feGaussianBlur', {{ stdDeviation: '3', result: 'coloredBlur' }}),
                                            e('feMerge', null,
                                                e('feMergeNode', {{ in: 'coloredBlur' }}),
                                                e('feMergeNode', {{ in: 'SourceGraphic' }})
                                            )
                                        )
                                    ),
                                    
                                    // Regular edges
                                    allEdges.map((edge, idx) => {{
                                        const fromNode = allNodes.find(n => n.id === edge.from);
                                        const toNode = allNodes.find(n => n.id === edge.to);
                                        if (!fromNode || !toNode) return null;
                                        return e('line', {{
                                            key: 'edge-' + idx,
                                            x1: fromNode.x,
                                            y1: fromNode.y,
                                            x2: toNode.x,
                                            y2: toNode.y,
                                            stroke: '#9ca3af',
                                            strokeWidth: 2,
                                            markerEnd: 'url(#arrowhead)',
                                            opacity: 0.6
                                        }});
                                    }}),
                                    
                                    // Cross-graph edges (shared nodes)
                                    graphData.crossGraphEdges.map((edge, idx) => {{
                                        const fromNode = allNodes.find(n => n.id === edge.from);
                                        const toNode = allNodes.find(n => n.id === edge.to);
                                        if (!fromNode || !toNode) return null;
                                        return e('line', {{
                                            key: 'cross-' + idx,
                                            x1: fromNode.x,
                                            y1: fromNode.y,
                                            x2: toNode.x,
                                            y2: toNode.y,
                                            stroke: '#3b82f6',
                                            strokeWidth: 3,
                                            strokeDasharray: '8,4',
                                            markerEnd: 'url(#arrowhead-blue)',
                                            filter: 'url(#glow)'
                                        }});
                                    }})
                                ),
                                
                                // Nodes
                                allNodes.map(node => {{
                                    return e('div', {{
                                        key: node.id,
                                        className: 'absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer node-card',
                                        style: {{
                                            left: node.x + 'px',
                                            top: node.y + 'px',
                                            zIndex: selectedNode && selectedNode.id === node.id ? 30 : 10
                                        }},
                                        onClick: () => handleNodeClick(node)
                                    }},
                                        e('div', {{
                                            className: 'rounded-xl p-4 shadow-xl',
                                            style: {{
                                                background: getSeverityBg(node.severity),
                                                borderColor: node.isShared ? '#3b82f6' : getSeverityColor(node.severity),
                                                borderWidth: node.isShared ? '3px' : '2px',
                                                borderStyle: node.isShared ? 'dashed' : 'solid',
                                                maxWidth: '220px',
                                                minWidth: '180px'
                                            }}
                                        }},
                                            e('div', {{
                                                className: 'flex items-center justify-between mb-2'
                                            }},
                                                e('div', {{
                                                    className: 'text-xs font-bold',
                                                    style: {{ color: node.isShared ? '#3b82f6' : getSeverityColor(node.severity) }}
                                                }},
                                                    node.type === 'changed' 
                                                        ? '🔴 LINE ' + node.lineNumber
                                                        : (node.isShared ? '🔗 SHARED' : '⚙️ NODE')
                                                ),
                                                e('button', {{
                                                    className: 'text-xs px-2 py-1 rounded bg-white bg-opacity-50 hover:bg-opacity-100 font-semibold',
                                                    onClick: (ev) => {{ ev.stopPropagation(); handleNodeClick(node); }}
                                                }}, 'ℹ️')
                                            ),
                                            e('div', {{ className: 'text-base font-bold text-gray-900 mb-2' }}, node.label),
                                            e('div', {{
                                                className: 'text-xs px-3 py-1 rounded-full text-white font-bold text-center shadow-md severity-badge',
                                                style: {{ backgroundColor: getSeverityColor(node.severity) }}
                                            }}, node.severity),
                                            node.isShared && e('div', {{ className: 'text-xs mt-2 text-blue-700 font-semibold bg-white bg-opacity-60 rounded px-2 py-1' }},
                                                '📍 Lines: ' + node.affectedByLines.join(', ')
                                            ),
                                            node.dependencyCount !== undefined && e('div', {{ className: 'text-xs mt-2 text-gray-700 font-medium' }},
                                                '🔗 ' + node.dependencyCount + ' dependencies'
                                            )
                                        )
                                    );
                                }})
                            )
                        )
                    ),
                    
                    // Details Tab
                    activeTab === 'details' && e('div', {{ className: 'space-y-6' }},
                        parsedAnalysis.line_analyses.length > 0 ? parsedAnalysis.line_analyses.map((lineAnalysis, idx) =>
                            e('div', {{ 
                                key: idx,
                                className: 'glass-effect p-6 rounded-2xl shadow-lg'
                            }},
                                e('h3', {{ className: 'text-xl font-bold text-gray-900 mb-4 flex items-center gap-2' }},
                                    e('span', null, '📍'),
                                    lineAnalysis.title
                                ),
                                e('div', {{ className: 'markdown-content text-gray-700' }},
                                    lineAnalysis.content
                                )
                            )
                        ) : e('div', {{ className: 'glass-effect p-8 rounded-2xl shadow-lg text-center' }},
                            e('p', {{ className: 'text-gray-600 text-lg' }}, 'No detailed line-by-line analysis available.')
                        ),
                        
                        // Overall Assessment
                        parsedAnalysis.overall_assessment && e('div', {{ className: 'glass-effect p-6 rounded-2xl shadow-lg' }},
                            e('h2', {{ className: 'text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2' }},
                                e('span', null, '📊'),
                                'Overall Assessment'
                            ),
                            e('div', {{ className: 'markdown-content text-gray-700' }},
                                parsedAnalysis.overall_assessment
                            )
                        )
                    ),
                    
                    // Severity Detail Modal
                    showSeverityModal && severityNode && e('div', {{
                        className: 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4',
                        onClick: () => setShowSeverityModal(false)
                    }},
                        e('div', {{
                            className: 'glass-effect p-8 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-auto',
                            onClick: (ev) => ev.stopPropagation()
                        }},
                            e('div', {{ className: 'flex items-start justify-between mb-6' }},
                                e('div', null,
                                    e('h3', {{ className: 'text-2xl font-bold text-gray-900' }}, severityNode.label),
                                    e('p', {{ className: 'text-gray-600 mt-1' }}, severityNode.description)
                                ),
                                e('button', {{
                                    onClick: () => setShowSeverityModal(false),
                                    className: 'text-gray-500 hover:text-gray-700 text-3xl font-bold leading-none'
                                }}, '×')
                            ),
                            
                            // Severity Badge Large
                            e('div', {{ className: 'mb-6' }},
                                e('div', {{
                                    className: 'inline-flex items-center gap-3 px-6 py-3 rounded-xl text-white font-bold text-lg shadow-lg',
                                    style: {{ backgroundColor: getSeverityColor(severityNode.severity) }}
                                }},
                                    e('span', null, severityNode.severity === 'HIGH' ? '🔴' : severityNode.severity === 'MEDIUM' ? '🟡' : '🟢'),
                                    e('span', null, severityNode.severity + ' SEVERITY')
                                )
                            ),
                            
                            // Details
                            e('div', {{ className: 'space-y-4' }},
                                e('div', {{ className: 'bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-xl border-l-4 border-blue-500' }},
                                    e('h4', {{ className: 'font-bold text-gray-900 mb-2 flex items-center gap-2' }},
                                        e('span', null, '🎯'),
                                        'Why This Severity?'
                                    ),
                                    e('p', {{ className: 'text-gray-700 leading-relaxed' }}, severityNode.severityReason)
                                ),
                                
                                e('div', {{ className: 'bg-gradient-to-r from-purple-50 to-pink-50 p-4 rounded-xl border-l-4 border-purple-500' }},
                                    e('h4', {{ className: 'font-bold text-gray-900 mb-2 flex items-center gap-2' }},
                                        e('span', null, '💥'),
                                        'Impact'
                                    ),
                                    e('p', {{ className: 'text-gray-700 leading-relaxed' }}, severityNode.impact)
                                ),
                                
                                severityNode.dependencyCount !== undefined && e('div', {{ className: 'bg-gradient-to-r from-green-50 to-emerald-50 p-4 rounded-xl border-l-4 border-green-500' }},
                                    e('h4', {{ className: 'font-bold text-gray-900 mb-2 flex items-center gap-2' }},
                                        e('span', null, '🔗'),
                                        'Dependencies'
                                    ),
                                    e('p', {{ className: 'text-gray-700 leading-relaxed' }},
                                        'This node has ' + severityNode.dependencyCount + ' total dependencies. ' +
                                        (severityNode.dependencyCount > 5 
                                            ? 'High dependency count indicates complex interconnections and wider blast radius for changes.'
                                            : severityNode.dependencyCount > 2
                                            ? 'Moderate dependency count suggests careful testing of related functionality.'
                                            : 'Low dependency count indicates relatively isolated impact.')
                                    )
                                ),
                                
                                severityNode.isShared && e('div', {{ className: 'bg-gradient-to-r from-yellow-50 to-amber-50 p-4 rounded-xl border-l-4 border-yellow-500' }},
                                    e('h4', {{ className: 'font-bold text-gray-900 mb-2 flex items-center gap-2' }},
                                        e('span', null, '⚠️'),
                                        'Shared Node Warning'
                                    ),
                                    e('p', {{ className: 'text-gray-700 leading-relaxed' }},
                                        'This node is affected by multiple changed lines (' + severityNode.affectedByLines.join(', ') + '). ' +
                                        'Shared nodes require extra attention as they accumulate risk from multiple sources.'
                                    )
                                ),
                                
                                e('div', {{ className: 'bg-gradient-to-r from-gray-50 to-slate-50 p-4 rounded-xl border-l-4 border-gray-400' }},
                                    e('h4', {{ className: 'font-bold text-gray-900 mb-2 flex items-center gap-2' }},
                                        e('span', null, '📋'),
                                        'Recommended Actions'
                                    ),
                                    e('ul', {{ className: 'list-disc list-inside space-y-1 text-gray-700' }},
                                        severityNode.severity === 'HIGH' && [
                                            e('li', {{ key: '1' }}, 'Conduct thorough code review with senior developer'),
                                            e('li', {{ key: '2' }}, 'Write comprehensive unit and integration tests'),
                                            e('li', {{ key: '3' }}, 'Perform manual QA testing in staging environment'),
                                            e('li', {{ key: '4' }}, 'Consider feature flag for gradual rollout')
                                        ],
                                        severityNode.severity === 'MEDIUM' && [
                                            e('li', {{ key: '1' }}, 'Peer review required before deployment'),
                                            e('li', {{ key: '2' }}, 'Ensure test coverage for affected functionality'),
                                            e('li', {{ key: '3' }}, 'Monitor closely in production after deployment')
                                        ],
                                        severityNode.severity === 'LOW' && [
                                            e('li', {{ key: '1' }}, 'Standard code review process'),
                                            e('li', {{ key: '2' }}, 'Basic test coverage verification'),
                                            e('li', {{ key: '3' }}, 'Normal deployment process acceptable')
                                        ]
                                    )
                                )
                            ),
                            
                            e('div', {{ className: 'mt-6 flex justify-end' }},
                                e('button', {{
                                    onClick: () => setShowSeverityModal(false),
                                    className: 'px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-blue-700 shadow-lg'
                                }}, 'Close')
                            )
                        )
                    )
                )
            );
        }}
        
        ReactDOM.createRoot(document.getElementById('root')).render(e(App));
    </script>
</body>
</html>'''
        
        return html