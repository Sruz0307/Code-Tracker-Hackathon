# claude_analyzer.py - Fixed bracket errors
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
    
    def _create_html_visualization(self, file_path, changed_lines, affected_vars, affected_funcs, claude_analysis):
        file_name = os.path.basename(file_path)
        changed_lines_str = ", ".join(map(str, sorted(changed_lines)))
        
        graph_data = self._build_dependency_graphs_per_line(file_path, changed_lines, affected_vars, affected_funcs)
        graph_json_str = json.dumps(graph_data)
        
        # Properly escape for JavaScript template literal
        claude_analysis_safe = (claude_analysis
            .replace('\\', '\\\\')
            .replace('`', '\\`')
            .replace('${', '\\${'))
        
        # Build HTML using a readable JavaScript structure
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Impact Analysis - {file_name}</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ margin: 0; font-family: sans-serif; background: #f3f4f6; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script>
        const e = React.createElement;
        const useState = React.useState;
        
        const graphData = {graph_json_str};
        graphData.analysis = `{claude_analysis_safe}`;
        
        function App() {{
            const [zoom, setZoom] = useState(1);
            const [selectedNode, setSelectedNode] = useState(null);
            const [activeTab, setActiveTab] = useState('graph');
            
            const getSeverityColor = (severity) => {{
                if (severity === 'HIGH') return '#ef4444';
                if (severity === 'MEDIUM') return '#f59e0b';
                return '#10b981';
            }};
            
            const getSeverityBg = (severity) => {{
                if (severity === 'HIGH') return '#fee2e2';
                if (severity === 'MEDIUM') return '#fef3c7';
                return '#d1fae5';
            }};
            
            const totalHeight = graphData.graphs.length * 900;
            const allNodes = [];
            const allEdges = [];
            
            graphData.graphs.forEach(graph => {{
                allNodes.push(...graph.nodes);
                allEdges.push(...graph.edges);
            }});
            
            return e('div', {{ className: 'min-h-screen p-6' }},
                e('div', {{ className: 'max-w-6xl mx-auto' }},
                    // Header
                    e('div', {{ className: 'bg-white p-6 rounded-lg shadow mb-6' }},
                        e('h1', {{ className: 'text-3xl font-bold' }}, 'Impact Analysis: {file_name}'),
                        e('p', {{ className: 'text-gray-600 mt-2' }}, 
                            'Changed Lines: {changed_lines_str} • ' +
                            '{len(affected_vars)} variables • {len(affected_funcs)} functions affected')
                    ),
                    
                    // Tab selector
                    e('div', {{ className: 'bg-white p-4 rounded-lg shadow mb-4' }},
                        e('div', {{ className: 'flex gap-2' }},
                            e('button', {{
                                onClick: () => setActiveTab('graph'),
                                className: 'px-4 py-2 rounded ' + (activeTab === 'graph' ? 'bg-blue-500 text-white' : 'bg-gray-200')
                            }}, 'Dependency Graph'),
                            e('button', {{
                                onClick: () => setActiveTab('analysis'),
                                className: 'px-4 py-2 rounded ' + (activeTab === 'analysis' ? 'bg-blue-500 text-white' : 'bg-gray-200')
                            }}, 'Claude Analysis')
                        )
                    ),
                    
                    // Graph tab
                    activeTab === 'graph' && e('div', {{ className: 'bg-white p-4 rounded-lg shadow' }},
                        // Zoom controls
                        e('div', {{ className: 'flex gap-2 mb-4' }},
                            e('button', {{
                                onClick: () => setZoom(Math.max(0.5, zoom - 0.2)),
                                className: 'px-3 py-2 bg-blue-100 rounded hover:bg-blue-200'
                            }}, 'Zoom Out'),
                            e('span', {{ className: 'px-3 py-2 font-bold' }}, zoom.toFixed(1) + 'x'),
                            e('button', {{
                                onClick: () => setZoom(Math.min(2, zoom + 0.2)),
                                className: 'px-3 py-2 bg-blue-100 rounded hover:bg-blue-200'
                            }}, 'Zoom In')
                        ),
                        
                        // Graph container
                        e('div', {{ className: 'overflow-auto border', style: {{ maxHeight: '800px' }} }},
                            e('div', {{ 
                                className: 'relative bg-white',
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
                                            e('polygon', {{ points: '0 0,10 3,0 6', fill: '#666' }})
                                        ),
                                        e('marker', {{ id: 'arrowhead-blue', markerWidth: 10, markerHeight: 10, refX: 9, refY: 3, orient: 'auto' }},
                                            e('polygon', {{ points: '0 0,10 3,0 6', fill: '#3b82f6' }})
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
                                            stroke: '#999',
                                            strokeWidth: 2,
                                            markerEnd: 'url(#arrowhead)'
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
                                            strokeDasharray: '5,5',
                                            markerEnd: 'url(#arrowhead-blue)'
                                        }});
                                    }})
                                ),
                                
                                // Nodes
                                allNodes.map(node => {{
                                    return e('div', {{
                                        key: node.id,
                                        className: 'absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer hover:scale-110 transition-transform',
                                        style: {{
                                            left: node.x + 'px',
                                            top: node.y + 'px',
                                            zIndex: 10
                                        }},
                                        onClick: () => setSelectedNode(node)
                                    }},
                                        e('div', {{
                                            className: 'rounded-lg p-3 shadow-lg',
                                            style: {{
                                                backgroundColor: getSeverityBg(node.severity),
                                                borderColor: node.isShared ? '#3b82f6' : getSeverityColor(node.severity),
                                                borderWidth: node.isShared ? '3px' : '2px',
                                                borderStyle: node.isShared ? 'dashed' : 'solid',
                                                maxWidth: '200px'
                                            }}
                                        }},
                                            e('div', {{
                                                className: 'text-xs font-bold mb-1',
                                                style: {{ color: node.isShared ? '#3b82f6' : getSeverityColor(node.severity) }}
                                            }},
                                                node.type === 'changed' 
                                                    ? '🔴 LINE ' + node.lineNumber
                                                    : (node.isShared ? '🔗 SHARED' : '⚠️')
                                            ),
                                            e('div', {{ className: 'text-sm font-semibold' }}, node.label),
                                            e('div', {{
                                                className: 'text-xs px-2 py-1 rounded mt-2 text-white font-semibold',
                                                style: {{ backgroundColor: node.isShared ? '#3b82f6' : getSeverityColor(node.severity) }}
                                            }}, node.severity),
                                            node.isShared && e('div', {{ className: 'text-xs mt-1 text-blue-600 font-semibold' }},
                                                'Lines: ' + node.affectedByLines.join(', ')
                                            )
                                        )
                                    );
                                }})
                            )
                        ),
                        
                        // Selected node details
                        selectedNode && e('div', {{ className: 'mt-4 bg-gradient-to-r from-blue-50 to-blue-100 border-l-4 border-blue-500 p-5 rounded-lg shadow-md' }},
                            e('div', {{ className: 'flex justify-between mb-3' }},
                                e('h4', {{ className: 'font-bold text-lg' }}, selectedNode.label),
                                e('button', {{
                                    onClick: () => setSelectedNode(null),
                                    className: 'text-blue-600 hover:text-blue-800 font-bold text-xl'
                                }}, '✕')
                            ),
                            e('div', {{ className: 'space-y-3' }},
                                e('div', {{ className: 'bg-white rounded p-3' }},
                                    e('p', {{ className: 'text-sm font-semibold mb-1' }}, '📋 Description'),
                                    e('p', {{ className: 'text-sm' }}, selectedNode.description)
                                ),
                                e('div', {{ className: 'bg-white rounded p-3' }},
                                    e('p', {{ className: 'text-sm font-semibold mb-1' }}, '💥 Impact'),
                                    e('p', {{ className: 'text-sm' }}, selectedNode.impact)
                                ),
                                e('div', {{ className: 'bg-white rounded p-3' }},
                                    e('p', {{ className: 'text-sm font-semibold mb-1' }}, '🎯 Severity Explanation'),
                                    e('p', {{ className: 'text-sm' }}, selectedNode.severityReason)
                                ),
                                selectedNode.dependencyCount !== undefined && e('div', {{ className: 'bg-white rounded p-3' }},
                                    e('p', {{ className: 'text-sm font-semibold mb-1' }}, '🔗 Dependencies'),
                                    e('p', {{ className: 'text-sm' }}, selectedNode.dependencyCount + ' total dependencies')
                                ),
                                selectedNode.isShared && e('div', {{ className: 'bg-blue-100 rounded p-3 border border-blue-300' }},
                                    e('p', {{ className: 'text-sm font-semibold mb-1' }}, '🔗 Shared Node'),
                                    e('p', {{ className: 'text-sm' }}, 'Affected by lines: ' + selectedNode.affectedByLines.join(', '))
                                )
                            )
                        )
                    ),
                    
                    // Analysis tab
                    activeTab === 'analysis' && e('div', {{ className: 'bg-white p-6 rounded-lg shadow' }},
                        e('h2', {{ className: 'text-2xl font-bold mb-4' }}, 'Claude AI Analysis'),
                        e('div', {{ className: 'whitespace-pre-wrap text-gray-800' }}, graphData.analysis)
                    )
                )
            );
        }}
        
        ReactDOM.createRoot(document.getElementById('root')).render(e(App));
    </script>
</body>
</html>'''
        
        return html