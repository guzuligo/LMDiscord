"""
Math Calculator Tool

This module implements a mathematical calculation tool that supports
basic arithmetic operations: add, subtract, multiply, divide.

Key Responsibilities:
- Perform mathematical calculations when called by LM Studio
- Support operations: add, subtract, multiply, divide
- Return formatted calculation results
- Handle division by zero and invalid input errors

Tool Definition:
- name: "math_calc"
- description: "Perform mathematical calculations"
- operations: add, subtract, multiply, divide
"""

from ..base import BaseTool, ToolResult


class MathCalcTool(BaseTool):
    """Tool for performing mathematical calculations.
    
    Supports basic arithmetic operations: add, subtract, multiply, divide.
    Handles division by zero and invalid operation errors gracefully.
    """

    @property
    def name(self) -> str:
        return "math_calc"

    @property
    def description(self) -> str:
        return (
            "Perform mathematical calculations. Supports operations: add, subtract, multiply, divide. "
            "Pass the operation type and two numbers (a and b) to get the result."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The arithmetic operation to perform",
                    "enum": ["add", "subtract", "multiply", "divide"]
                },
                "a": {
                    "type": "number",
                    "description": "The first number (operand)"
                },
                "b": {
                    "type": "number",
                    "description": "The second number (operand)"
                }
            },
            "required": ["operation", "a", "b"]
        }

    def execute(self, operation: str, a: float, b: float, **kwargs) -> ToolResult:
        """Execute a mathematical calculation.
        
        Args:
            operation: The arithmetic operation (add, subtract, multiply, divide)
            a: First operand
            b: Second operand
            **kwargs: Additional arguments (ignored)
            
        Returns:
            ToolResult with content as the calculation result
        """
        try:
            if operation == "add":
                result = a + b
                operator = "+"
            elif operation == "subtract":
                result = a - b
                operator = "-"
            elif operation == "multiply":
                result = a * b
                operator = "*"
            elif operation == "divide":
                if b == 0:
                    return ToolResult(
                        status="error",
                        message="Division by zero is not allowed. Please provide a non-zero divisor.",
                        error="Division by zero",
                        success=False,
                        content=""
                    )
                result = a / b
                operator = "/"
            else:
                return ToolResult(
                    status="error",
                    message=f"Unknown operation: {operation}. Valid operations: add, subtract, multiply, divide",
                    error=f"Unknown operation: {operation}",
                    success=False,
                    content=""
                )

            formatted_result = f"{a} {operator} {b} = {result}"
            return ToolResult(
                status="success",
                message=f"Calculation result: {formatted_result}",
                data=formatted_result,
                success=True,
                content=f"Calculation result: {formatted_result}"
            )

        except Exception as exc:
            return ToolResult(
                status="error",
                message=f"Calculation failed: {str(exc)}",
                error=f"Calculation failed: {str(exc)}",
                success=False,
                content=""
            )