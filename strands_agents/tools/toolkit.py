"""
Common mixin for Strands toolkits to make them iterable.
This allows toolkits to be passed directly to agents without calling get_tools().
"""

from strands import tool

class Toolkit:
    """Class that provides iterable and register functionality for Strands toolkits."""

    def __init__(self, tools = []):
        self._tools = []
    
    def __iter__(self):
        """Make the toolkit iterable so it can be passed directly to Agent."""
        if hasattr(self, '_tools'):
            return iter(self._tools)
        else:
            raise AttributeError("Toolkit must have a '_tools' attribute")
    
    def register(self, tool_function, name: str = None, description: str = None):
        """
        Register a tool function with optional custom name and description.
        Automatically adds the @tool decorator to the function.
        
        Args:
            tool_function: The function to register as a tool
            name: Custom name for the tool (optional)
            description: Custom description for the tool (optional)
        """
        
        # Apply @tool decorator with custom name and description if provided
        if name and description:
            decorated_function = tool(name=name, description=description)(tool_function)
        elif name:
            decorated_function = tool(name=name)(tool_function)
        else:
            decorated_function = tool(tool_function)
        
        # Add the decorated function to the list
        self._tools.append(decorated_function)
        
        return decorated_function