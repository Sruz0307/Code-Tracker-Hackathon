import os
import json
import time

class CacheManager:
    def __init__(self, project_path):
        self.project_path = project_path
        self.graph_file = os.path.join(project_path, "graph_cache.json")
        self.line_cache_file = os.path.join(project_path, "line_cache.json")
        self.line_cache = {}
        self.load_line_cache()

    # -----------------------------
    # Line cache
    # -----------------------------
    def load_line_cache(self):
        if os.path.exists(self.line_cache_file):
            with open(self.line_cache_file, "r", encoding="utf-8") as f:
                try:
                    self.line_cache = json.load(f)
                except json.JSONDecodeError:
                    self.line_cache = {}

    def save_line_cache(self):
        os.makedirs(os.path.dirname(self.line_cache_file), exist_ok=True)
        with open(self.line_cache_file, "w", encoding="utf-8") as f:
            json.dump(self.line_cache, f, indent=2)

    def get_changed_lines(self, file_path):
        """Compare file with cached version and return changed line numbers.
        Returns (changed_lines, current_lines, is_reorder_only, reorder_scope) 
        where reorder_scope indicates if reordering is within a function.
        """
        if not os.path.exists(file_path):
            return [], [], False, None

        with open(file_path, "r", encoding="utf-8") as f:
            current_lines = f.readlines()

        old_lines = self.line_cache.get(file_path, [])
        changed = []

        # Detect changed or new lines
        for i, line in enumerate(current_lines):
            if i >= len(old_lines) or line.strip() != old_lines[i].strip():
                changed.append(i + 1)

        # Check if it's just a reordering
        is_reorder_only = False
        reorder_scope = None
        
        if changed and len(current_lines) == len(old_lines):
            # Get sorted content of both versions
            old_content_sorted = sorted([line.strip() for line in old_lines if line.strip()])
            new_content_sorted = sorted([line.strip() for line in current_lines if line.strip()])
            
            # If sorted content is identical, it's just reordering
            if old_content_sorted == new_content_sorted:
                is_reorder_only = True
                reorder_scope = "file"
        
        # Check for local reordering within a specific range (like within a function)
        if changed and not is_reorder_only:
            # Check if only a contiguous block changed
            if changed:
                min_line = min(changed)
                max_line = max(changed)
                
                # Get the content of the changed range
                old_range = [old_lines[i-1].strip() for i in range(min_line, min(max_line+1, len(old_lines)+1))]
                new_range = [current_lines[i-1].strip() for i in range(min_line, min(max_line+1, len(current_lines)+1))]
                
                # If the sorted content within the range is the same, it's local reordering
                if sorted([line for line in old_range if line]) == sorted([line for line in new_range if line]):
                    is_reorder_only = True
                    reorder_scope = "local"

        return changed, current_lines, is_reorder_only, reorder_scope

    # -----------------------------
    # Graph cache
    # -----------------------------
    def save_graph(self, graph):
        """Save the dependency graph safely (convert sets to lists)."""
        os.makedirs(os.path.dirname(self.graph_file), exist_ok=True)

        def convert(obj):
            if isinstance(obj, set):
                return list(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj

        safe_graph = convert(graph)
        with open(self.graph_file, "w", encoding="utf-8") as f:
            json.dump(safe_graph, f, indent=2)

    def load_graph(self):
        """Load graph from cache."""
        if os.path.exists(self.graph_file):
            with open(self.graph_file, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def get_file_graph(self, file_path):
        """Get the cached graph for a specific file."""
        graph = self.load_graph()
        return graph.get(file_path, {"variables": {}, "functions": {}})

    # -----------------------------
    # Recursive affected computation
    # -----------------------------
    def get_ordered_recursive_affected(self, changed_vars, changed_funcs):
        """
        Returns lists of affected vars/functions in dependency order
        (first changed → indirectly affected → last).

        Cross-type dependencies (var→func or func→var) do not propagate
        unless the target is explicitly changed.
        """
        graph = self.load_graph()
        ordered_vars, ordered_funcs = [], []
        visited_vars, visited_funcs = set(), set()

        def matches(dep, target):
            """True if dependency matches unqualified target name."""
            return dep.split(".")[-1] == target.split(".")[-1]

        def visit_var(var):
            if var in visited_vars:
                return
            visited_vars.add(var)

            # ✅ only propagate to *other variables* that depend on this var
            for f_path, content in graph.items():
                for v_name, v_data in content.get("variables", {}).items():
                    for dep in v_data.get("depends_on", []):
                        if matches(dep, var):
                            visit_var(v_name)

            ordered_vars.append(var)

        def visit_func(func):
            if func in visited_funcs:
                return
            visited_funcs.add(func)

            # ✅ only propagate to *other functions* that depend on this func
            for f_path, content in graph.items():
                for func_name, f_data in content.get("functions", {}).items():
                    for dep in f_data.get("depends_on", []):
                        if matches(dep, func):
                            visit_func(func_name)

            ordered_funcs.append(func)

        # 🔹 Start traversal only within their own categories
        for v in changed_vars:
            visit_var(v)
        for f in changed_funcs:
            visit_func(f)

        ordered_vars.reverse()
        ordered_funcs.reverse()
        return ordered_vars, ordered_funcs

    # -----------------------------
    # Partial graph update
    # -----------------------------
    def update_partial_graph(self, file_path, affected_vars, affected_funcs, full_graph):
        """
        Update saved graph for a file and compute recursively affected elements.
        """
        graph = self.load_graph()
        graph[file_path] = full_graph
        self.save_graph(graph)

        ordered_vars, ordered_funcs = self.get_ordered_recursive_affected(
            affected_vars, affected_funcs
        )

        print(f"📊 Ordered affected variables: {ordered_vars}")
        print(f"📊 Ordered affected functions: {ordered_funcs}")
        print(f"✅ Updated partial graph for {file_path}")

    # -----------------------------
    # Baseline update
    # -----------------------------
    def update_file_baseline(self, file_path, new_file_lines):
        """
        Update the baseline content for a file so the current version
        becomes the new reference point for future change detection.
        """
        self.line_cache[file_path] = new_file_lines
        self.save_line_cache()