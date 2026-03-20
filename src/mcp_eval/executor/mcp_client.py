"""MCP protocol client for communicating with MCP servers."""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from ..models import MCPEvalConfig


class MCPClient:
    """Client for communicating with MCP servers via WebSocket or stdio."""

    def __init__(
        self,
        config: MCPEvalConfig,
        mock_mode: bool = False,
        mock_responses: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP client.

        Args:
            config: MCP evaluation configuration
            mock_mode: If True, simulate responses without real connection
            mock_responses: Dictionary mapping prompts to mock responses
        """
        self.config = config
        self.mock_mode = mock_mode
        self.mock_responses = mock_responses or {}
        self.connection = None
        self._connected = False
        self._message_id = 0

    async def connect(self) -> bool:
        """
        Establish connection to MCP server.

        Returns:
            True if connection successful, False otherwise
        """
        if self.mock_mode:
            self._connected = True
            return True

        # In a real implementation, this would:
        # - For WebSocket: establish WebSocket connection
        # - For stdio: spawn subprocess with asyncio.subprocess
        # For now, we'll just mark as connected for testing
        self._connected = True
        return True

    async def disconnect(self):
        """Gracefully close the connection."""
        if self.mock_mode:
            self._connected = False
            return

        # In real implementation: close WebSocket or terminate subprocess
        self._connected = False

    async def send_message(self, message: dict) -> dict:
        """
        Send an MCP protocol message and await response.

        Args:
            message: MCP JSON-RPC message

        Returns:
            Response message from server
        """
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        # Add message ID for JSON-RPC
        self._message_id += 1
        message["id"] = self._message_id
        message["jsonrpc"] = "2.0"

        if self.mock_mode:
            # Simulate network delay
            await asyncio.sleep(0.01)

            # Return mock response
            return {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": self.mock_responses.get("default", {"content": "Mock response"}),
            }

        # In real implementation: send via WebSocket/stdio and await response
        # For now, return a placeholder
        return {"jsonrpc": "2.0", "id": message["id"], "result": {}}

    async def send_prompt(
        self,
        prompt: str,
        tools: Optional[List[Dict]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a prompt to the agent and get response.

        Args:
            prompt: The prompt text to send
            tools: Optional list of available tools
            timeout: Optional timeout in seconds

        Returns:
            Dictionary containing:
                - response: Agent's text response
                - tool_calls: List of tool calls made
                - resources_accessed: List of resources accessed
                - timing: Timing information
                - tokens: Token usage information
        """
        start_time = time.time()

        # Build MCP sampling/create message
        message = {
            "method": "sampling/createMessage",
            "params": {
                "messages": [{"role": "user", "content": prompt}],
                "maxTokens": 4096,
            },
        }

        if tools:
            message["params"]["tools"] = tools

        # Send message
        try:
            if timeout:
                response = await asyncio.wait_for(
                    self.send_message(message), timeout=timeout
                )
            else:
                response = await self.send_message(message)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timed out after {timeout} seconds")

        end_time = time.time()

        # Parse response
        result = response.get("result", {})

        # Extract tool calls and resources (in mock mode, simulate these)
        tool_calls = []
        resources_accessed = []

        if self.mock_mode:
            # Check if mock response includes tool calls
            mock_data = self.mock_responses.get(prompt, self.mock_responses.get("default", {}))

            if isinstance(mock_data, dict):
                tool_calls = mock_data.get("tool_calls", [])
                resources_accessed = mock_data.get("resources", [])
                response_text = mock_data.get("content", "Mock response")
                tokens = mock_data.get("tokens", {"prompt": 10, "completion": 20, "total": 30})
            else:
                response_text = str(mock_data)
                tokens = {"prompt": 10, "completion": 20, "total": 30}
        else:
            response_text = result.get("content", "")
            tokens = result.get("usage", {"prompt": 0, "completion": 0, "total": 0})

        return {
            "response": response_text,
            "tool_calls": tool_calls,
            "resources_accessed": resources_accessed,
            "timing": {
                "start": start_time,
                "end": end_time,
                "duration_ms": int((end_time - start_time) * 1000),
            },
            "tokens": tokens,
        }

    async def handle_tool_call(self, tool_call: dict) -> dict:
        """
        Handle a tool call from the agent.

        Args:
            tool_call: Tool call request from agent

        Returns:
            Tool execution result
        """
        # In mock mode, return a mock tool result
        if self.mock_mode:
            return {
                "tool_call_id": tool_call.get("id", "mock_id"),
                "result": {"status": "success", "output": "Mock tool result"},
            }

        # In real implementation: execute the tool and return result
        return {"tool_call_id": tool_call.get("id"), "result": {}}

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()
