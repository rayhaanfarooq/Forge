"""AST parsing utilities for Python code analysis"""

import ast
from typing import Dict, List, Set, Tuple


class FunctionInfo:
    """Information about a function extracted from AST"""
    def __init__(self, name: str, start_line: int, end_line: int, is_method: bool = False, class_name: str = None):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.is_method = is_method
        self.class_name = class_name
    
    def __repr__(self):
        return f"FunctionInfo(name={self.name}, lines={self.start_line}-{self.end_line}, method={self.is_method})"


def extract_public_functions(code: str) -> List[FunctionInfo]:
    """
    Extract public function definitions from Python code.
    
    Args:
        code: Python source code
        
    Returns:
        List of FunctionInfo objects for public functions and methods
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    
    functions = []
    
    class FunctionVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_class = None
        
        def visit_ClassDef(self, node):
            old_class = self.current_class
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = old_class
        
        def visit_FunctionDef(self, node):
            # Only include public functions (not starting with _)
            if not node.name.startswith('_'):
                is_method = self.current_class is not None
                func_info = FunctionInfo(
                    name=node.name,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    is_method=is_method,
                    class_name=self.current_class
                )
                functions.append(func_info)
            self.generic_visit(node)
    
    visitor = FunctionVisitor()
    visitor.visit(tree)
    
    return functions


def extract_tested_functions(test_code: str) -> Set[str]:
    """
    Extract function names that are being tested from a test file.
    
    This parses the test file to find what functions are being imported/called
    in test functions. It looks for patterns like:
    - from module import function_name
    - from module import function_name as alias
    - module.function_name()
    - function_name()
    
    Args:
        test_code: Test file source code
        
    Returns:
        Set of function names that appear to be tested
    """
    try:
        tree = ast.parse(test_code)
    except SyntaxError:
        return set()
    
    tested_functions = set()
    
    class TestVisitor(ast.NodeVisitor):
        def visit_ImportFrom(self, node):
            # Handle: from module import function_name
            if node.module:
                for alias in node.names:
                    tested_functions.add(alias.name)
            self.generic_visit(node)
        
        def visit_Call(self, node):
            # Handle: function_name() or module.function_name()
            if isinstance(node.func, ast.Name):
                tested_functions.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # Handle module.function_name() - get the attribute name
                if isinstance(node.func.value, ast.Name):
                    tested_functions.add(node.func.attr)
            self.generic_visit(node)
        
        def visit_Import(self, node):
            # Handle: import module
            for alias in node.names:
                tested_functions.add(alias.name)
            self.generic_visit(node)
    
    visitor = TestVisitor()
    visitor.visit(tree)
    
    return tested_functions


def extract_function_code(code: str, function_info: FunctionInfo) -> str:
    """
    Extract the code for a specific function from source code.
    
    Args:
        code: Full source code
        function_info: FunctionInfo object describing the function to extract
        
    Returns:
        Code snippet containing just the function definition and body
    """
    lines = code.split('\n')
    # Extract lines (AST line numbers are 1-indexed)
    function_lines = lines[function_info.start_line - 1:function_info.end_line]
    return '\n'.join(function_lines)


def extract_code_for_functions(code: str, function_names: List[str]) -> str:
    """
    Extract code snippets for multiple functions from source code.
    
    Args:
        code: Full source code
        function_names: List of function names to extract
        
    Returns:
        Combined code snippets for all requested functions
    """
    functions = extract_public_functions(code)
    function_dict = {f.name: f for f in functions}
    
    extracted = []
    for func_name in function_names:
        if func_name in function_dict:
            func_info = function_dict[func_name]
            func_code = extract_function_code(code, func_info)
            extracted.append(func_code)
    
    return '\n\n'.join(extracted)


def get_untested_functions(source_code: str, test_code: str) -> List[str]:
    """
    Compare source code and test code to find untested public functions.
    
    Args:
        source_code: Source file code
        test_code: Test file code (if exists)
        
    Returns:
        List of function names that are in source but not in tests
    """
    source_functions = extract_public_functions(source_code)
    if not test_code:
        # No test file, all functions are untested
        return [f.name for f in source_functions]
    
    tested_functions = extract_tested_functions(test_code)
    source_function_names = {f.name for f in source_functions}
    
    # Functions in source but not tested
    untested = source_function_names - tested_functions
    
    return sorted(list(untested))


def get_untested_functions_with_info(source_code: str, test_code: str) -> List[FunctionInfo]:
    """
    Get untested functions with full FunctionInfo.
    
    Args:
        source_code: Source file code
        test_code: Test file code (if exists)
        
    Returns:
        List of FunctionInfo objects for untested functions
    """
    source_functions = extract_public_functions(source_code)
    if not test_code:
        return source_functions
    
    tested_functions = extract_tested_functions(test_code)
    source_function_dict = {f.name: f for f in source_functions}
    
    untested = []
    for func_name, func_info in source_function_dict.items():
        if func_name not in tested_functions:
            untested.append(func_info)
    
    return sorted(untested, key=lambda f: f.start_line)

