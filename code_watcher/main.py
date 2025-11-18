# main.py
import os
from analyzer import (
    analyze_project, 
    analyze_file_changes, 
    build_full_graph_for_file,
    get_added_variables,
    get_deleted_variables_impact
)
from watcher import watch_folder
from cache_manager import CacheManager
from claude_analyzer import ClaudeImpactAnalyzer
import sys
from dotenv import load_dotenv

# 🔧 Set your project path
if len(sys.argv) < 1:
    print("Please provide the project path as a command-line argument.")
    sys.exit(1)
PROJECT_PATH = sys.argv[1]
OUTPUT_PATH = PROJECT_PATH+r"\output.txt"

# 🔧 Set your Claude API key
load_dotenv()  # Load environment variables from .env file
CLAUDE_API_KEY = os.getenv("CLAUD_API_KEY") # Replace with your actual API key

# Initialize Claude analyzer (set to None to disable)
claude_analyzer = ClaudeImpactAnalyzer(CLAUDE_API_KEY) if CLAUDE_API_KEY else None


def handle_change(file_path, cache):
    output_file=open(OUTPUT_PATH,"a")
    print(f"\nDetected change in: {file_path}")
    output_file.write(f"\nDetected change in: {file_path}\n")
    # Step 1: Get old graph before changes
    old_graph = cache.get_file_graph(file_path)
    full_project_graph = cache.load_graph()

    # Step 2: Get changed lines
    changed_lines, new_file_lines, is_reorder_only, reorder_scope = cache.get_changed_lines(file_path)
    if not changed_lines:
        print("No changes detected.")
        output_file.write("No changes detected.\n")
        return
    
    # Step 2a: If only line order changed, just report that
    if is_reorder_only:
        from analyzer import get_functions_at_lines
        affected_functions = get_functions_at_lines(file_path, changed_lines)
        
        if reorder_scope == "file":
            print(" Line order changed (no content modification)")
            output_file.write(" Line order changed (no content modification)\n")
        else:
            print(" Lines reordered within function(s)")
            output_file.write(" Lines reordered within function(s)\n")
        if affected_functions:
            print(f"   In functions: {affected_functions}")
            output_file.write(f"   In functions: {affected_functions}\n")
        
        # Update baseline and exit
        cache.update_file_baseline(file_path, new_file_lines)
        return
    
    print(f"Changed lines: {changed_lines}")
    output_file.write(f"Changed lines: {changed_lines}\n")
    # Step 3: Check for ADDED variables/functions
    added_vars, added_funcs = get_added_variables(file_path, old_graph)
    
    if added_vars or added_funcs:
        print(f"\n ADDED:")
        output_file.write(f"\n ADDED:\n")
        if added_vars:
            print(f"   Variables: {added_vars}")
            output_file.write(f"   Variables: {added_vars}\n")
        if added_funcs:
            print(f"   Functions: {added_funcs}")
            output_file.write(f"   Functions: {added_funcs}\n")

    # Step 4: Check for DELETED variables/functions and their impact
    deleted_vars, deleted_funcs, affected_by_deletion = get_deleted_variables_impact(
        file_path, old_graph, full_project_graph
    )
    
    # Initialize these early so they're available later
    affected_vars_del = set()
    affected_funcs_del = set()
    
    if deleted_vars or deleted_funcs:
        print(f"\n  DELETED:")
        output_file.write(f"\n  DELETED:\n")
        if deleted_vars:
            print(f"   Variables: {deleted_vars}")
            output_file.write(f"   Variables: {deleted_vars}\n")
        if deleted_funcs:
            print(f"   Functions: {deleted_funcs}")
            output_file.write(f"   Functions: {deleted_funcs}\n")
        
        if affected_by_deletion:
            # Build the current graph to check types
            new_graph = build_full_graph_for_file(file_path)
            
            for item in affected_by_deletion:
                # Check if it's in variables or functions
                if item in new_graph.get("variables", {}):
                    affected_vars_del.add(item)
                elif item in new_graph.get("functions", {}):
                    affected_funcs_del.add(item)
                else:
                    # Fallback: check across all files in project
                    for fpath, content in full_project_graph.items():
                        if item in content.get("variables", {}):
                            affected_vars_del.add(item)
                            break
                        elif item in content.get("functions", {}):
                            affected_funcs_del.add(item)
                            break
            
            print(f"\n  AFFECTED BY DELETION (downstream impacts):")
            output_file.write(f"\n  AFFECTED BY DELETION (downstream impacts):\n")    
            if affected_vars_del:
                print(f"   Variables: {affected_vars_del}")
                output_file.write(f"   Variables: {affected_vars_del}\n")
            if affected_funcs_del:
                print(f"   Functions: {affected_funcs_del}")
                output_file.write(f"   Functions: {affected_funcs_del}\n")

    # Step 5: Analyze changed lines in the file (for modified items)
    affected_vars, affected_funcs = analyze_file_changes(file_path, changed_lines)
    
    # Remove added items from affected (they're new, not modified)
    affected_vars = affected_vars - added_vars
    affected_funcs = affected_funcs - added_funcs
    
    if affected_vars or affected_funcs:
        print(f"\n MODIFIED (and downstream impacts):")
        output_file.write(f"\n MODIFIED (and downstream impacts):\n")
        if affected_vars:
            print(f"   Variables: {affected_vars}")
            output_file.write(f"   Variables: {affected_vars}\n")
        if affected_funcs:
            print(f"   Functions: {affected_funcs}")
            output_file.write(f"   Functions: {affected_funcs}\n")

    # Step 6: Build the full dependency graph for the file
    full_graph = build_full_graph_for_file(file_path)

    # Step 7: Combine all affected items for ordered list generation
    # Include deleted impacts in the ordering
    all_affected_vars = affected_vars | affected_vars_del if affected_by_deletion else affected_vars
    all_affected_funcs = affected_funcs | affected_funcs_del if affected_by_deletion else affected_funcs
    
    # Update cache and propagate dependencies recursively
    cache.update_partial_graph(file_path, all_affected_vars, all_affected_funcs, full_graph)

    # Step 8: Generate Claude Impact Analysis
    if claude_analyzer:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            print("\n" + "="*60)
            print("🤖 GENERATING CLAUDE IMPACT ANALYSIS...")
            print("="*60)
            
            claude_analyzer.generate_impact_analysis(
                file_path=file_path,
                changed_lines=changed_lines,
                affected_vars=affected_vars,
                affected_funcs=affected_funcs,
                added_vars=added_vars,
                added_funcs=added_funcs,
                deleted_vars=deleted_vars,
                deleted_funcs=deleted_funcs,
                affected_by_deletion=affected_by_deletion,
                code_content=code_content
            )
        except Exception as e:
            print(f"⚠️  Claude analysis failed: {e}")
    
    # Step 9: Update the baseline
    cache.update_file_baseline(file_path, new_file_lines)


def main():
    print("Scanning project folder...")
    cache = CacheManager(PROJECT_PATH)

    # Step 0: make sure project path exists
    if not os.path.exists(PROJECT_PATH):
        print(f"Project path does not exist: {PROJECT_PATH}")
        return
    if not os.path.exists(OUTPUT_PATH):
        print("The file does not exist, creating a new one.")
        open(OUTPUT_PATH, 'w', encoding='utf-8').close()


    # Step 1: full project analysis on startup
    graph = analyze_project(PROJECT_PATH)
    cache.save_graph(graph)
    print(" Initial analysis complete.")

    # Step 2: preload files (optional, for line cache)
    for root, _, files in os.walk(PROJECT_PATH):
        for f in files:
            if f.endswith('.py'):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                    cache.update_file_baseline(file_path, lines)
                except Exception as e:
                    print(f"  Could not preload {file_path}: {e}")

    print(" Watching for changes...\nPress Ctrl+C to stop.")
    watch_folder(PROJECT_PATH, lambda f: handle_change(f, cache))

if __name__ == "__main__":
    main()