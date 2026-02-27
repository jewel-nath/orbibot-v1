"""Terminal Chat CLI for OrbiBot Agent."""

import argparse
import logging
import sys
from typing import Optional

import rclpy
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ..agent_node import AgentNode

try:
    from rich import print
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)

console = Console()


class ChatCli:
    """Terminal chat interface."""

    def __init__(self):
        self._node: Optional[AgentNode] = None

    def initialize(self, provider: Optional[str] = None) -> bool:
        """Initialize ROS and agent.

        Args:
            provider: Optional provider name to use

        Returns:
            True if successful
        """
        rclpy.init()

        self._node = AgentNode()
        self._node.get_logger().info('Chat CLI initialized')

        # Set provider
        if provider:
            if not self._node.set_provider(provider):
                available = self._node.get_available_providers()
                console.print(f"[red]Provider '{provider}' not available. Available: {available}[/red]")
                return False
        else:
            # Try default
            available = self._node.get_available_providers()
            if available:
                self._node.set_provider(available[0])
            else:
                console.print("[red]No LLM providers available. Set an API key.[/red]")
                return False

        return True

    def print_header(self):
        """Print chat header."""
        if RICH_AVAILABLE:
            console.print(Panel.fit(
                "[bold blue]OrbiBot Agent CLI[/bold blue]\n"
                "[dim]Type 'exit' to quit, 'help' for commands[/dim]",
                title="🤖",
                border_style="blue"
            ))
        else:
            print("=== OrbiBot Agent CLI ===")
            print("Type 'exit' to quit, 'help' for commands")
            print("=" * 40)

    def print_help(self):
        """Print help message."""
        help_text = """
Commands:
  /help          Show this help message
  /providers     List available LLM providers
  /provider <n>  Switch to provider (gemini, anthropic, moonshot, ollama)
  /reset         Reset chat session
  /tools         List available tools
  exit, quit     Exit the CLI
        """
        if RICH_AVAILABLE:
            console.print(Panel(help_text, title="Commands", border_style="green"))
        else:
            print(help_text)

    def print_providers(self):
        """Print available providers."""
        available = self._node.get_available_providers()
        current = self._node._current_provider.name if self._node._current_provider else None

        if RICH_AVAILABLE:
            table = Table(title="LLM Providers")
            table.add_column("Provider", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Current", style="yellow")

            for provider in ['gemini', 'anthropic', 'moonshot', 'ollama']:
                status = "✓ available" if provider in available else "✗ unavailable"
                is_current = "←" if provider == current else ""
                table.add_row(provider, status, is_current)

            console.print(table)
        else:
            print("Available providers:")
            for provider in available:
                marker = " (current)" if provider == current else ""
                print(f"  - {provider}{marker}")

    def print_tools(self):
        """Print available tools."""
        tools = self._node._tool_registry.get_tool_schemas()

        if RICH_AVAILABLE:
            table = Table(title="Available Tools")
            table.add_column("Tool", style="cyan")
            table.add_column("Description", style="dim")

            for tool in tools:
                func = tool.get('function', {})
                table.add_row(func.get('name', 'unknown'), func.get('description', '')[:50])

            console.print(table)
        else:
            print("Available tools:")
            for tool in tools:
                func = tool.get('function', {})
                print(f"  - {func.get('name')}: {func.get('description', '')[:50]}")

    def run(self):
        """Run CLI loop."""
        self.print_header()

        while rclpy.ok():
            try:
                if RICH_AVAILABLE:
                    user_input = Prompt.ask("[bold green]You[/bold green]")
                else:
                    user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            user_input = user_input.strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                break

            if user_input == '/help':
                self.print_help()
                continue

            if user_input == '/providers':
                self.print_providers()
                continue

            if user_input.startswith('/provider '):
                provider = user_input.split(maxsplit=1)[1].strip()
                if self._node.set_provider(provider):
                    console.print(f"[green]Switched to provider: {provider}[/green]")
                else:
                    console.print(f"[red]Failed to switch to provider: {provider}[/red]")
                continue

            if user_input == '/reset':
                if self._node._current_provider:
                    self._node._current_provider.start_chat(self._node._system_prompt)
                console.print("[dim]Chat session reset[/dim]")
                continue

            if user_input == '/tools':
                self.print_tools()
                continue

            # Process message
            try:
                response = self._node.process_message(user_input)

                # Display tool calls
                for tool_call in response.get('tool_calls', []):
                    tool_name = tool_call.get('name', 'unknown')
                    args = tool_call.get('arguments', {})
                    if RICH_AVAILABLE:
                        console.print(f"[dim]→ {tool_name}({args})[/dim]")
                    else:
                        print(f"[tool] {tool_name}({args})")

                # Display response
                text = response.get('text', 'No response')
                if RICH_AVAILABLE:
                    console.print(Panel(
                        text,
                        title="[bold blue]OrbiBot[/bold blue]",
                        border_style="blue"
                    ))
                else:
                    print(f"OrbiBot: {text}")

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        # Cleanup
        if self._node:
            self._node.destroy_node()
        rclpy.shutdown()
        console.print("[dim]Goodbye![/dim]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='OrbiBot Agent CLI')
    parser.add_argument('--provider', '-p', help='LLM provider to use (gemini, anthropic, moonshot, ollama)')
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)

    cli = ChatCli()
    if not cli.initialize(args.provider):
        sys.exit(1)

    try:
        cli.run()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()