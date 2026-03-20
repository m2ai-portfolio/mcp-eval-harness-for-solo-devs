"""Custom Python evaluation using AST-validated expressions."""

import ast
import logging
from ..models import ComparisonResult, Expectation, ExpectationType

logger = logging.getLogger(__name__)

# Maximum input size (1MB)
MAX_INPUT_SIZE = 1_000_000

# Allowed AST node types for safe expression evaluation
SAFE_NODES = {
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp,
    ast.Compare, ast.Call, ast.Constant, ast.Name, ast.Load,
    ast.And, ast.Or, ast.Not,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.FloorDiv,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.IfExp,  # ternary: x if condition else y
    ast.Subscript, ast.Index, ast.Slice,
    ast.List, ast.Tuple, ast.Set, ast.Dict,
    ast.Starred,
    ast.FormattedValue, ast.JoinedStr,  # f-strings
}


class UnsafeExpressionError(Exception):
    """Raised when an expression contains unsafe operations."""
    pass


def validate_ast(node, depth=0):
    """Walk AST tree and reject unsafe node types."""
    if depth > 20:
        raise UnsafeExpressionError("Expression too deeply nested (max depth: 20)")

    node_type = type(node)

    # Check for attribute access - only allow safe attributes
    if isinstance(node, ast.Attribute):
        # Block ALL dunder attributes (starting with _)
        if isinstance(node.attr, str) and node.attr.startswith('_'):
            raise UnsafeExpressionError(f"Access to private/dunder attribute '{node.attr}' is not allowed")
        # Recursively validate the value part
        validate_ast(node.value, depth + 1)
        return

    # Check for Name nodes - block dangerous names
    if isinstance(node, ast.Name):
        blocked_names = {
            '__import__', 'exec', 'eval', 'compile', 'open',
            'getattr', 'setattr', 'delattr', 'globals', 'locals',
            'vars', 'dir', '__builtins__', 'breakpoint',
            'input', 'print',  # No I/O in expressions
        }
        if node.id in blocked_names:
            raise UnsafeExpressionError(f"Use of '{node.id}' is not allowed in custom expressions")
        return

    # Check for Call nodes - validate function being called
    if isinstance(node, ast.Call):
        # Validate the function reference
        validate_ast(node.func, depth + 1)
        # Validate arguments
        for arg in node.args:
            validate_ast(arg, depth + 1)
        for kw in node.keywords:
            validate_ast(kw.value, depth + 1)
        return

    if node_type not in SAFE_NODES:
        raise UnsafeExpressionError(
            f"Unsafe expression element: {node_type.__name__}. "
            f"Only simple comparisons, arithmetic, and safe function calls are allowed."
        )

    # Recursively check children
    for child in ast.iter_child_nodes(node):
        validate_ast(child, depth + 1)


class CustomComparator:
    """Custom Python evaluation using AST-validated expressions."""

    def compare(self, actual: str, expectation: Expectation) -> ComparisonResult:
        """
        Execute custom evaluation function with security hardening.

        - AST-based validation before execution
        - Blocks all dunder attribute access
        - Blocks dangerous builtins (exec, eval, __import__, getattr, etc.)
        - Maximum expression nesting depth (20)
        - Empty __builtins__ namespace
        - Input size limit (1MB)

        Args:
            actual: The actual output to evaluate
            expectation: The expectation with custom function code

        Returns:
            ComparisonResult with evaluation result
        """
        expected = expectation.value
        custom_function = expectation.custom_function

        # Check input size limits
        if len(actual) > MAX_INPUT_SIZE or len(expected) > MAX_INPUT_SIZE:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.CUSTOM,
                expected=expected,
                actual=actual,
                score=0.0,
                details=f"Input exceeds maximum size of {MAX_INPUT_SIZE} characters"
            )

        if not custom_function:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.CUSTOM,
                expected=expected,
                actual=actual,
                score=0.0,
                details="No custom function provided"
            )

        # Step 1: Parse expression into AST
        try:
            tree = ast.parse(custom_function, mode='eval')
        except SyntaxError as e:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.CUSTOM,
                expected=expected,
                actual=actual,
                score=0.0,
                details=f"Invalid expression syntax: {e}"
            )

        # Step 2: Validate AST is safe
        try:
            validate_ast(tree)
        except UnsafeExpressionError as e:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.CUSTOM,
                expected=expected,
                actual=actual,
                score=0.0,
                details=f"Unsafe expression: {e}"
            )

        # Step 3: Compile and evaluate with minimal namespace
        try:
            code = compile(tree, '<custom_expression>', 'eval')

            # Minimal safe namespace - empty __builtins__
            namespace = {
                '__builtins__': {},  # CRITICAL: Empty dict, not restricted dict
                'actual': actual,
                'expected': expected,
                # Only add explicitly safe functions
                'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                'abs': abs, 'min': min, 'max': max, 'sum': sum,
                'sorted': sorted, 'list': list, 'set': set, 'dict': dict, 'tuple': tuple,
                'any': any, 'all': all, 'isinstance': isinstance, 'round': round,
                'True': True, 'False': False, 'None': None,
            }

            result = eval(code, namespace)

            # Convert result to passed/score
            if isinstance(result, bool):
                passed = result
                score = 1.0 if result else 0.0
                details = f"Custom function returned: {result}"
            elif isinstance(result, (int, float)):
                score = float(result)
                threshold = expectation.threshold if expectation.threshold is not None else 0.5
                passed = score >= threshold
                details = f"Custom function returned score: {score:.2f} (threshold: {threshold:.2f})"
            else:
                # Unexpected return type, try to convert to bool
                passed = bool(result)
                score = 1.0 if passed else 0.0
                details = f"Custom function returned: {result!r} (converted to {passed})"

            return ComparisonResult(
                passed=passed,
                expectation_type=ExpectationType.CUSTOM,
                expected=expected,
                actual=actual,
                score=score,
                details=details
            )

        except Exception as e:
            return ComparisonResult(
                passed=False,
                expectation_type=ExpectationType.CUSTOM,
                expected=expected,
                actual=actual,
                score=0.0,
                details=f"Expression evaluation error: {type(e).__name__}: {e}"
            )
