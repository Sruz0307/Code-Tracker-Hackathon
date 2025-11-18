# claude_analyzer.py - Minimalist UI version
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
            
            # Build function-variable mappings based on which variables are used in which functions
            func_to_vars = {}
            var_to_funcs = {}
            
            # Analyze which variables are referenced by which functions
            for func in line_data['affected_funcs']:
                func_deps = full_graph.get('functions', {}).get(func, {}).get('depends_on', [])
                func_to_vars[func] = []
                
                for var in line_data['affected_vars']:
                    # Check if this variable is a dependency of this function
                    if var in func_deps or any(var in dep for dep in func_deps):
                        func_to_vars[func].append(var)
                        if var not in var_to_funcs:
                            var_to_funcs[var] = []
                        var_to_funcs[var].append(func)
            
            # Track which variables have been placed
            placed_vars = set()
            
            # Position functions and their related variables
            x_func = 350
            x_var = 600  # Horizontal position for variables
            current_y = graph_y_base
            func_spacing = 100  # Minimum spacing between function rows
            
            for func_idx, func in enumerate(sorted(line_data['affected_funcs'])):
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
                
                # Get related variables for this function
                related_vars = func_to_vars.get(func, [])
                num_related_vars = len(related_vars)
                
                # Position the function
                func_y = current_y
                
                nodes.append({
                    'id': node_id,
                    'label': func_short,
                    'type': 'affected',
                    'severity': severity,
                    'x': x_func,
                    'y': func_y,
                    'description': f'Function: {func}',
                    'impact': f'Has {num_deps} dependencies. Changes may affect dependent code',
                    'isShared': is_shared,
                    'affectedByLines': affected_by_lines,
                    'lineNumber': line_num,
                    'severityReason': reason,
                    'dependencyCount': num_deps
                })
                
                # Edge from changed line to function
                edges.append({'from': source_node_id, 'to': node_id})
                
                # Add related variables horizontally next to this function
                var_start_y = current_y
                for var_idx, var in enumerate(sorted(related_vars)):
                    var_short = var.split('.')[-1] if '.' in var else var
                    var_node_id = f"var_{var}_line{line_num}_func{func_idx}"
                    
                    is_var_shared = len(all_var_nodes.get(var, set())) > 1
                    var_affected_by_lines = list(all_var_nodes.get(var, {line_num}))
                    
                    var_deps = full_graph.get('variables', {}).get(var, {}).get('depends_on', [])
                    num_var_deps = len(var_deps)
                    
                    if num_var_deps > 4:
                        var_severity = 'MEDIUM'
                        var_reason = f'MEDIUM: {num_var_deps} dependencies (>4) - wide propagation'
                    elif num_var_deps > 0:
                        var_severity = 'LOW'
                        var_reason = f'LOW: {num_var_deps} dependencies (1-4) - limited scope'
                    else:
                        var_severity = 'LOW'
                        var_reason = 'LOW: No dependencies - isolated change'
                    
                    var_y = var_start_y + (var_idx * 90)
                    
                    nodes.append({
                        'id': var_node_id,
                        'label': var_short,
                        'type': 'affected',
                        'severity': var_severity,
                        'x': x_var,
                        'y': var_y,
                        'description': f'Variable: {var}',
                        'impact': f'Depends on {num_var_deps} items',
                        'isShared': is_var_shared,
                        'affectedByLines': var_affected_by_lines,
                        'lineNumber': line_num,
                        'severityReason': var_reason,
                        'dependencyCount': num_var_deps
                    })
                    
                    # Edge from function to its variable
                    edges.append({'from': node_id, 'to': var_node_id})
                    placed_vars.add(var)
                
                # Move down for next function
                # Space based on how many variables this function had
                current_y += max(num_related_vars * 90, func_spacing)
            
            # Add any orphaned variables (not connected to any function)
            orphaned_vars = [v for v in line_data['affected_vars'] if v not in placed_vars]
            
            if orphaned_vars:
                for var_idx, var in enumerate(sorted(orphaned_vars)):
                    var_short = var.split('.')[-1] if '.' in var else var
                    var_node_id = f"var_{var}_line{line_num}_orphan"
                    
                    is_var_shared = len(all_var_nodes.get(var, set())) > 1
                    var_affected_by_lines = list(all_var_nodes.get(var, {line_num}))
                    
                    var_deps = full_graph.get('variables', {}).get(var, {}).get('depends_on', [])
                    num_var_deps = len(var_deps)
                    
                    if num_var_deps > 4:
                        var_severity = 'MEDIUM'
                        var_reason = f'MEDIUM: {num_var_deps} dependencies (>4) - wide propagation'
                    elif num_var_deps > 0:
                        var_severity = 'LOW'
                        var_reason = f'LOW: {num_var_deps} dependencies (1-4) - limited scope'
                    else:
                        var_severity = 'LOW'
                        var_reason = 'LOW: No dependencies - isolated change'
                    
                    nodes.append({
                        'id': var_node_id,
                        'label': var_short,
                        'type': 'affected',
                        'severity': var_severity,
                        'x': x_var,
                        'y': current_y + (var_idx * 90),
                        'description': f'Variable: {var}',
                        'impact': f'Depends on {num_var_deps} items',
                        'isShared': is_var_shared,
                        'affectedByLines': var_affected_by_lines,
                        'lineNumber': line_num,
                        'severityReason': var_reason,
                        'dependencyCount': num_var_deps
                    })
                    
                    # Edge from changed line to orphaned variable
                    edges.append({'from': source_node_id, 'to': var_node_id})
            
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #fafafa;
        }}
        
        .content {{
            line-height: 1.6;
        }}
        
        .content h2 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: #1f2937;
        }}
        
        .content h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            color: #374151;
        }}
        
        .content p {{
            margin-bottom: 1rem;
        }}
        
        .content ul {{
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .content li {{
            margin-bottom: 0.5rem;
        }}
        
        .content code {{
            background: #f3f4f6;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            font-family: monospace;
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script>
        const e = React.createElement;
        const useState = React.useState;
        
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
            
            const getSeverityColor = (severity) => {{
                if (severity === 'HIGH') return '#dc2626';
                if (severity === 'MEDIUM') return '#f59e0b';
                return '#16a34a';
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
            
            return e('div', {{ className: 'min-h-screen bg-white' }},
                e('div', {{ className: 'max-w-7xl mx-auto px-8 py-8' }},
                    // Header
                    e('div', {{ className: 'border-b pb-6 mb-8' }},
                        e('div', {{ className: 'flex items-start justify-between' }},
                            e('div', null,
                                e('h1', {{ className: 'text-3xl font-semibold text-gray-900 mb-1' }}, 
                                    'Impact Analysis'
                                ),
                                e('p', {{ className: 'text-lg text-gray-600' }}, fileName)
                            ),
                            e('div', {{ 
                                className: 'px-4 py-2 rounded border-2 font-semibold',
                                style: {{ 
                                    borderColor: getRiskLevelColor(parsedAnalysis.risk_level),
                                    color: getRiskLevelColor(parsedAnalysis.risk_level)
                                }}
                            }}, 
                                parsedAnalysis.risk_level + ' RISK'
                            )
                        ),
                        e('div', {{ className: 'mt-4 flex gap-6 text-sm text-gray-600' }},
                            e('span', null, 'Lines: ' + changedLinesStr),
                            e('span', null, affectedFuncsCount + ' functions'),
                            e('span', null, affectedVarsCount + ' variables')
                        )
                    ),
                    
                    // Tabs
                    e('div', {{ className: 'border-b mb-8' }},
                        e('div', {{ className: 'flex gap-8' }},
                            ['overview', 'graph', 'details'].map(tab => 
                                e('button', {{
                                    key: tab,
                                    onClick: () => setActiveTab(tab),
                                    className: 'pb-3 font-medium border-b-2 transition-colors ' + 
                                        (activeTab === tab 
                                            ? 'border-gray-900 text-gray-900' 
                                            : 'border-transparent text-gray-500 hover:text-gray-900')
                                }}, 
                                    tab.charAt(0).toUpperCase() + tab.slice(1)
                                )
                            )
                        )
                    ),
                    
                    // Overview Tab
                    activeTab === 'overview' && e('div', {{ className: 'space-y-8' }},
                        parsedAnalysis.overview && e('div', null,
                            e('h2', {{ className: 'text-xl font-semibold mb-4' }}, 'Summary'),
                            e('div', {{ className: 'content text-gray-700' }}, parsedAnalysis.overview)
                        ),
                        
                        parsedAnalysis.immediate_actions.length > 0 && e('div', null,
                            e('h2', {{ className: 'text-xl font-semibold mb-4' }}, 'Immediate Actions'),
                            e('div', {{ className: 'space-y-2' }},
                                parsedAnalysis.immediate_actions.map((action, idx) =>
                                    e('div', {{ 
                                        key: idx,
                                        className: 'flex gap-3 p-4 border-l-4 border-red-500 bg-red-50'
                                    }},
                                        e('span', {{ className: 'font-semibold text-red-700' }}, (idx + 1) + '.'),
                                        e('p', {{ className: 'text-gray-800' }}, action)
                                    )
                                )
                            )
                        ),
                        
                        parsedAnalysis.testing_required.length > 0 && e('div', null,
                            e('h2', {{ className: 'text-xl font-semibold mb-4' }}, 'Testing Required'),
                            e('ul', {{ className: 'space-y-2 list-disc list-inside text-gray-700' }},
                                parsedAnalysis.testing_required.map((test, idx) =>
                                    e('li', {{ key: idx }}, test)
                                )
                            )
                        )
                    ),
                    
                    // Graph Tab
                    activeTab === 'graph' && e('div', null,
                        // Controls
                        e('div', {{ className: 'flex items-center gap-4 mb-6' }},
                            e('button', {{
                                onClick: () => setZoom(Math.max(0.5, zoom - 0.2)),
                                className: 'px-4 py-2 border rounded hover:bg-gray-50'
                            }}, '− Zoom Out'),
                            e('span', {{ className: 'px-4 py-2 font-medium' }}, 
                                (zoom * 100).toFixed(0) + '%'
                            ),
                            e('button', {{
                                onClick: () => setZoom(Math.min(2, zoom + 0.2)),
                                className: 'px-4 py-2 border rounded hover:bg-gray-50'
                            }}, '+ Zoom In'),
                            e('span', {{ className: 'ml-auto text-sm text-gray-500' }},
                                'Click any node for details'
                            )
                        ),
                        
                        // Legend
                        e('div', {{ className: 'flex gap-6 mb-6 pb-4 border-b text-sm' }},
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('div', {{ className: 'w-3 h-3 rounded border-2 border-red-600 bg-red-100' }}),
                                e('span', null, 'High')
                            ),
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('div', {{ className: 'w-3 h-3 rounded border-2 border-yellow-600 bg-yellow-100' }}),
                                e('span', null, 'Medium')
                            ),
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('div', {{ className: 'w-3 h-3 rounded border-2 border-green-600 bg-green-100' }}),
                                e('span', null, 'Low')
                            ),
                            e('div', {{ className: 'flex items-center gap-2' }},
                                e('div', {{ className: 'w-3 h-3 rounded border-2 border-dashed border-blue-600' }}),
                                e('span', null, 'Shared')
                            )
                        ),
                        
                        // Graph
                        e('div', {{ className: 'border overflow-auto', style: {{ maxHeight: '700px' }} }},
                            e('div', {{ 
                                className: 'relative bg-white',
                                style: {{ 
                                    height: (totalHeight * zoom) + 'px',
                                    width: (900 * zoom) + 'px',
                                    transform: 'scale(' + zoom + ')',
                                    transformOrigin: 'top left'
                                }}
                            }},
                                e('svg', {{ width: 900, height: totalHeight, className: 'absolute' }},
                                    e('defs', null,
                                        e('marker', {{ id: 'arrow', markerWidth: 8, markerHeight: 8, refX: 7, refY: 3, orient: 'auto' }},
                                            e('polygon', {{ points: '0 0,8 3,0 6', fill: '#9ca3af' }})
                                        ),
                                        e('marker', {{ id: 'arrow-blue', markerWidth: 8, markerHeight: 8, refX: 7, refY: 3, orient: 'auto' }},
                                            e('polygon', {{ points: '0 0,8 3,0 6', fill: '#3b82f6' }})
                                        )
                                    ),
                                    
                                    allEdges.map((edge, idx) => {{
                                        const from = allNodes.find(n => n.id === edge.from);
                                        const to = allNodes.find(n => n.id === edge.to);
                                        if (!from || !to) return null;
                                        return e('line', {{
                                            key: 'e' + idx,
                                            x1: from.x, y1: from.y, x2: to.x, y2: to.y,
                                            stroke: '#d1d5db', strokeWidth: 1.5,
                                            markerEnd: 'url(#arrow)'
                                        }});
                                    }}),
                                    
                                    graphData.crossGraphEdges.map((edge, idx) => {{
                                        const from = allNodes.find(n => n.id === edge.from);
                                        const to = allNodes.find(n => n.id === edge.to);
                                        if (!from || !to) return null;
                                        return e('line', {{
                                            key: 'c' + idx,
                                            x1: from.x, y1: from.y, x2: to.x, y2: to.y,
                                            stroke: '#3b82f6', strokeWidth: 2,
                                            strokeDasharray: '4,2',
                                            markerEnd: 'url(#arrow-blue)'
                                        }});
                                    }})
                                ),
                                
                                allNodes.map(node => {{
                                    const bgColor = node.severity === 'HIGH' ? '#fecaca' :
                                                   node.severity === 'MEDIUM' ? '#fef3c7' : '#d1fae5';
                                    const borderColor = node.isShared ? '#3b82f6' : getSeverityColor(node.severity);
                                    
                                    return e('div', {{
                                        key: node.id,
                                        className: 'absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer',
                                        style: {{
                                            left: node.x + 'px', top: node.y + 'px', zIndex: 10
                                        }},
                                        onClick: () => setSelectedNode(node)
                                    }},
                                        e('div', {{
                                            className: 'rounded border-2 p-3 bg-white shadow-sm hover:shadow-md transition-shadow',
                                            style: {{
                                                backgroundColor: bgColor,
                                                borderColor: borderColor,
                                                borderStyle: node.isShared ? 'dashed' : 'solid',
                                                minWidth: '160px',
                                                maxWidth: '200px'
                                            }}
                                        }},
                                            e('div', {{ className: 'text-xs font-medium mb-1', style: {{ color: borderColor }} }},
                                                node.type === 'changed' ? 'LINE ' + node.lineNumber : (node.isShared ? 'SHARED' : 'NODE')
                                            ),
                                            e('div', {{ className: 'font-semibold text-gray-900 mb-2' }}, node.label),
                                            e('div', {{
                                                className: 'text-xs px-2 py-1 rounded text-white font-medium inline-block',
                                                style: {{ backgroundColor: getSeverityColor(node.severity) }}
                                            }}, node.severity),
                                            node.dependencyCount !== undefined && e('div', {{ className: 'text-xs text-gray-600 mt-2' }},
                                                node.dependencyCount + ' deps'
                                            )
                                        )
                                    );
                                }})
                            )
                        ),
                        
                        // Selected node modal
                        selectedNode && e('div', {{
                            className: 'fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4',
                            onClick: () => setSelectedNode(null)
                        }},
                            e('div', {{
                                className: 'bg-white rounded border shadow-lg max-w-2xl w-full max-h-[80vh] overflow-auto p-6',
                                onClick: (ev) => ev.stopPropagation()
                            }},
                                e('div', {{ className: 'flex items-start justify-between mb-4' }},
                                    e('div', null,
                                        e('h3', {{ className: 'text-xl font-semibold' }}, selectedNode.label),
                                        e('p', {{ className: 'text-sm text-gray-600 mt-1' }}, selectedNode.description)
                                    ),
                                    e('button', {{
                                        onClick: () => setSelectedNode(null),
                                        className: 'text-gray-400 hover:text-gray-600 text-2xl font-light'
                                    }}, '×')
                                ),
                                
                                e('div', {{ className: 'mb-4' }},
                                    e('div', {{
                                        className: 'inline-flex items-center gap-2 px-3 py-2 rounded border-2 font-semibold',
                                        style: {{ 
                                            borderColor: getSeverityColor(selectedNode.severity),
                                            color: getSeverityColor(selectedNode.severity)
                                        }}
                                    }},
                                        e('span', null, selectedNode.severity + ' SEVERITY')
                                    )
                                ),
                                
                                e('div', {{ className: 'space-y-4' }},
                                    e('div', {{ className: 'border-l-4 border-blue-500 pl-4 py-2 bg-blue-50' }},
                                        e('h4', {{ className: 'font-semibold mb-1' }}, 'Why This Severity?'),
                                        e('p', {{ className: 'text-sm text-gray-700' }}, selectedNode.severityReason)
                                    ),
                                    
                                    e('div', {{ className: 'border-l-4 border-purple-500 pl-4 py-2 bg-purple-50' }},
                                        e('h4', {{ className: 'font-semibold mb-1' }}, 'Impact'),
                                        e('p', {{ className: 'text-sm text-gray-700' }}, selectedNode.impact)
                                    ),
                                    
                                    selectedNode.dependencyCount !== undefined && e('div', {{ className: 'border-l-4 border-green-500 pl-4 py-2 bg-green-50' }},
                                        e('h4', {{ className: 'font-semibold mb-1' }}, 'Dependencies'),
                                        e('p', {{ className: 'text-sm text-gray-700' }},
                                            selectedNode.dependencyCount + ' total dependencies. ' +
                                            (selectedNode.dependencyCount > 5 
                                                ? 'High count indicates complex interconnections.'
                                                : selectedNode.dependencyCount > 2
                                                ? 'Moderate complexity, test related functionality.'
                                                : 'Low count, relatively isolated.')
                                        )
                                    ),
                                    
                                    selectedNode.isShared && e('div', {{ className: 'border-l-4 border-yellow-500 pl-4 py-2 bg-yellow-50' }},
                                        e('h4', {{ className: 'font-semibold mb-1' }}, 'Shared Node'),
                                        e('p', {{ className: 'text-sm text-gray-700' }},
                                            'Affected by lines: ' + selectedNode.affectedByLines.join(', ') + '. Shared nodes accumulate risk from multiple sources.'
                                        )
                                    ),
                                    
                                    e('div', {{ className: 'border-l-4 border-gray-400 pl-4 py-2 bg-gray-50' }},
                                        e('h4', {{ className: 'font-semibold mb-1' }}, 'Recommended Actions'),
                                        e('ul', {{ className: 'text-sm text-gray-700 space-y-1 list-disc list-inside' }},
                                            selectedNode.severity === 'HIGH' && [
                                                e('li', {{ key: '1' }}, 'Thorough code review with senior developer'),
                                                e('li', {{ key: '2' }}, 'Comprehensive unit and integration tests'),
                                                e('li', {{ key: '3' }}, 'Manual QA testing in staging'),
                                                e('li', {{ key: '4' }}, 'Consider feature flag for rollout')
                                            ],
                                            selectedNode.severity === 'MEDIUM' && [
                                                e('li', {{ key: '1' }}, 'Peer review required'),
                                                e('li', {{ key: '2' }}, 'Test coverage for affected functionality'),
                                                e('li', {{ key: '3' }}, 'Monitor in production after deployment')
                                            ],
                                            selectedNode.severity === 'LOW' && [
                                                e('li', {{ key: '1' }}, 'Standard code review'),
                                                e('li', {{ key: '2' }}, 'Basic test coverage'),
                                                e('li', {{ key: '3' }}, 'Normal deployment process')
                                            ]
                                        )
                                    )
                                ),
                                
                                e('div', {{ className: 'mt-6 flex justify-end' }},
                                    e('button', {{
                                        onClick: () => setSelectedNode(null),
                                        className: 'px-4 py-2 border rounded hover:bg-gray-50'
                                    }}, 'Close')
                                )
                            )
                        )
                    ),
                    
                    // Details Tab
                    activeTab === 'details' && e('div', {{ className: 'space-y-8' }},
                        parsedAnalysis.line_analyses.length > 0 ? parsedAnalysis.line_analyses.map((lineAnalysis, idx) =>
                            e('div', {{ 
                                key: idx,
                                className: 'border-l-4 border-gray-300 pl-6 py-2'
                            }},
                                e('h3', {{ className: 'text-lg font-semibold mb-3' }}, lineAnalysis.title),
                                e('div', {{ className: 'content text-gray-700' }}, lineAnalysis.content)
                            )
                        ) : e('div', {{ className: 'text-center py-12' }},
                            e('p', {{ className: 'text-gray-500' }}, 'No detailed analysis available')
                        ),
                        
                        parsedAnalysis.overall_assessment && e('div', {{ className: 'border-t pt-8 mt-8' }},
                            e('h2', {{ className: 'text-xl font-semibold mb-4' }}, 'Overall Assessment'),
                            e('div', {{ className: 'content text-gray-700' }}, parsedAnalysis.overall_assessment)
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