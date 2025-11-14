import ast
import os
import builtins

# -----------------------------
# Analyze whole project
# -----------------------------
def analyze_project(project_path):
    """
    Walk the project folder and analyze all Python files.
    Returns a graph of variables/functions with their dependencies.
    """
    graph = {}
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                file_graph = build_full_graph_for_file(file_path)
                graph[file_path] = file_graph
    return graph


# -----------------------------
# Build full graph for one file
# -----------------------------
def build_full_graph_for_file(file_path):
    """
    Returns a dict:
    {
      "variables": {qualified_var: {"depends_on": [...]}} ,
      "functions": {qualified_func: {"depends_on": [...]}} ,
    }
    Qualifies each name as file[.class][.function].name.
    """
    graph = {"variables": {}, "functions": {}}
    if not os.path.exists(file_path):
        return graph

    file_name = os.path.splitext(os.path.basename(file_path))[0]
    builtin_names = set(dir(builtins))

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
    except Exception as e:
        print(f"❌ Failed to parse {file_path}: {e}")
        return graph

    class Analyzer(ast.NodeVisitor):
        def __init__(self, file_name, graph):
            self.file_name = file_name
            self.graph = graph
            self.current_class = []
            self.current_func = []
            self.func_params = {}  # function_name → [param names]

        def qualify(self, name):
            parts = [self.file_name] + self.current_class + self.current_func + [name]
            return ".".join(parts)

        # -----------------------------
        # Classes and functions
        # -----------------------------
        def visit_ClassDef(self, node):
            self.current_class.append(node.name)
            self.generic_visit(node)
            self.current_class.pop()

        def visit_FunctionDef(self, node):
            self.current_func.append(node.name)
            q_name = self.qualify(node.name)

            # store parameter names for dependency propagation
            param_names = [a.arg for a in node.args.args]
            self.func_params[q_name] = param_names

            deps = set()
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and n.id not in builtin_names:
                    deps.add(self.qualify(n.id))
                elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    if n.func.id not in builtin_names:
                        deps.add(self.qualify(n.func.id))

            # also connect params as internal dependencies
            for param in param_names:
                deps.add(self.qualify(param))

            self.graph["functions"][q_name] = {"depends_on": sorted(deps)}
            self.generic_visit(node)
            self.current_func.pop()

        # -----------------------------
        # Variables and assignments
        # -----------------------------
        def visit_Assign(self, node):
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue

                var_name = target.id
                scoped_name = self.qualify(var_name)
                depends_on = set()

                # --- CASE 1: Right side is a function call ---
                if isinstance(node.value, ast.Call):
                    # identify called function
                    if isinstance(node.value.func, ast.Name):
                        func_name = node.value.func.id
                        qualified_func = self.qualify(func_name)
                        depends_on.add(qualified_func)

                        # connect argument vars → called function params
                        for arg in node.value.args:
                            if isinstance(arg, ast.Name):
                                arg_name = self.qualify(arg.id)
                                depends_on.add(arg_name)

                                # propagate argument → parameter link
                                for f_name, params in self.func_params.items():
                                    if f_name.endswith(f".{func_name}"):
                                        for param in params:
                                            qualified_param = f"{f_name}.{param}"
                                            self.graph["variables"].setdefault(
                                                qualified_param,
                                                {"depends_on": []}
                                            )["depends_on"].append(arg_name)
                    elif isinstance(node.value.func, ast.Attribute):
                        depends_on.add(node.value.func.attr)

                # --- CASE 2: Regular variable assignment ---
                else:
                    for child in ast.walk(node.value):
                        if isinstance(child, ast.Name):
                            depends_on.add(self.qualify(child.id))

                self.graph["variables"][scoped_name] = {
                    "depends_on": sorted(depends_on)
                }

            self.generic_visit(node)

    # Run analyzer
    Analyzer(file_name, graph).visit(tree)
    return graph


# -----------------------------
# Find affected functions by line numbers
# -----------------------------
def get_functions_at_lines(file_path, line_numbers):
    """
    Given line numbers, return the function names that contain those lines.
    """
    file_graph = build_full_graph_for_file(file_path)
    affected_functions = set()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
    except Exception:
        return affected_functions
    
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    class FunctionFinder(ast.NodeVisitor):
        def __init__(self, file_name):
            self.file_name = file_name
            self.current_class = []
            self.current_func = []
            self.functions = []  # List of (func_name, start_line, end_line)
        
        def qualify(self, name):
            parts = [self.file_name] + self.current_class + [name]
            return ".".join(parts)
        
        def visit_ClassDef(self, node):
            self.current_class.append(node.name)
            self.generic_visit(node)
            self.current_class.pop()
        
        def visit_FunctionDef(self, node):
            func_name = self.qualify(node.name)
            start_line = node.lineno
            # Find the last line of the function
            end_line = node.lineno
            for child in ast.walk(node):
                if hasattr(child, 'lineno'):
                    end_line = max(end_line, child.lineno)
            
            self.functions.append((func_name, start_line, end_line))
            self.generic_visit(node)
    
    finder = FunctionFinder(file_name)
    finder.visit(tree)
    
    # Check which functions contain the changed lines
    for func_name, start, end in finder.functions:
        for line_num in line_numbers:
            if start <= line_num <= end:
                affected_functions.add(func_name)
                break
    
    return affected_functions


# -----------------------------
# Find affected lines
# -----------------------------
def analyze_file_changes(file_path, changed_lines):
    """
    Given changed lines, return affected variable and function names.
    Expands impact through the dependency graph (normalized across scopes).
    """
    file_graph = build_full_graph_for_file(file_path)
    affected_vars, affected_funcs = set(), set()
    added_vars, added_funcs = set(), set()
    deleted_vars, deleted_funcs = set(), set()

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # -----------------------------
    # STEP 1 – Detect directly changed items
    # -----------------------------
    for i, line in enumerate(lines, start=1):
        if i not in changed_lines:
            continue

        stripped = line.strip()

        if stripped.startswith("def "):
            func_name = stripped.split("def ")[1].split("(")[0].strip()
            for f_name in file_graph["functions"]:
                if f_name.endswith(f".{func_name}"):
                    affected_funcs.add(f_name)
            continue

        if "=" in line and not line.strip().startswith("#"):
            left_side = line.split("=")[0].strip()
            var_name = left_side.split(".")[-1]
            for v in file_graph["variables"]:
                if v.endswith(f".{var_name}"):
                    affected_vars.add(v)

    # -----------------------------
    # STEP 2 – Normalize helper
    # -----------------------------
    def normalize(name):
        """Trim nested scopes like test1.fn1.fn2.var -> test1.var"""
        parts = name.split(".")
        if len(parts) > 2:
            # Keep only filename + last part (to unify scopes)
            return f"{parts[0]}.{parts[-1]}"
        return name

    normalized_vars = {normalize(v) for v in affected_vars}
    normalized_funcs = {normalize(f) for f in affected_funcs}

    # -----------------------------
    # STEP 3 – Recursive expansion with normalization
    # -----------------------------
    def expand_impacts():
        changed = True
        while changed:
            changed = False
            for var, info in file_graph["variables"].items():
                deps = {normalize(d) for d in info["depends_on"]}
                if any(d in normalized_vars or d in normalized_funcs for d in deps):
                    if var not in affected_vars:
                        affected_vars.add(var)
                        normalized_vars.add(normalize(var))
                        changed = True

            for func, info in file_graph["functions"].items():
                deps = {normalize(d) for d in info["depends_on"]}
                if any(d in normalized_vars or d in normalized_funcs for d in deps):
                    if func not in affected_funcs:
                        affected_funcs.add(func)
                        normalized_funcs.add(normalize(func))
                        changed = True

    expand_impacts()

    return affected_vars, affected_funcs


# -----------------------------
# Track added variables
# -----------------------------
def get_added_variables(file_path, old_graph):
    """
    Compare old graph with current file to find newly added variables/functions.
    Returns (added_vars, added_funcs)
    """
    new_graph = build_full_graph_for_file(file_path)
    
    old_vars = set(old_graph.get("variables", {}).keys())
    new_vars = set(new_graph.get("variables", {}).keys())
    
    old_funcs = set(old_graph.get("functions", {}).keys())
    new_funcs = set(new_graph.get("functions", {}).keys())
    
    added_vars = new_vars - old_vars
    added_funcs = new_funcs - old_funcs
    
    return added_vars, added_funcs


# -----------------------------
# Track deleted variables and their downstream impact
# -----------------------------
def get_deleted_variables_impact(file_path, old_graph, full_project_graph):
    """
    Compare old graph with current file to find deleted variables/functions.
    Returns (deleted_vars, deleted_funcs, affected_by_deletion)
    """
    new_graph = build_full_graph_for_file(file_path)
    
    old_vars = set(old_graph.get("variables", {}).keys())
    new_vars = set(new_graph.get("variables", {}).keys())
    
    old_funcs = set(old_graph.get("functions", {}).keys())
    new_funcs = set(new_graph.get("functions", {}).keys())
    
    deleted_vars = old_vars - new_vars
    deleted_funcs = old_funcs - new_funcs
    
    # Find all variables/functions that depended on deleted items
    affected_by_deletion = set()
    
    def normalize(name):
        parts = name.split(".")
        if len(parts) > 2:
            return f"{parts[0]}.{parts[-1]}"
        return name
    
    # Check current graph for dependencies on deleted items
    for var, info in new_graph.get("variables", {}).items():
        for dep in info.get("depends_on", []):
            if normalize(dep) in {normalize(d) for d in deleted_vars | deleted_funcs}:
                affected_by_deletion.add(var)
    
    for func, info in new_graph.get("functions", {}).items():
        for dep in info.get("depends_on", []):
            if normalize(dep) in {normalize(d) for d in deleted_vars | deleted_funcs}:
                affected_by_deletion.add(func)
    
    # Recursively expand to find second-level impacts
    def expand_deletion_impact():
        changed = True
        normalized_affected = {normalize(a) for a in affected_by_deletion}
        
        while changed:
            changed = False
            for var, info in new_graph.get("variables", {}).items():
                deps = {normalize(d) for d in info.get("depends_on", [])}
                if any(d in normalized_affected for d in deps):
                    if var not in affected_by_deletion:
                        affected_by_deletion.add(var)
                        normalized_affected.add(normalize(var))
                        changed = True
            
            for func, info in new_graph.get("functions", {}).items():
                deps = {normalize(d) for d in info.get("depends_on", [])}
                if any(d in normalized_affected for d in deps):
                    if func not in affected_by_deletion:
                        affected_by_deletion.add(func)
                        normalized_affected.add(normalize(func))
                        changed = True
    
    expand_deletion_impact()
    
    return deleted_vars, deleted_funcs, affected_by_deletion