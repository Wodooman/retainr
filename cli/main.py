"""CLI client for the retainr MCP Server."""

import json
import sys
from pathlib import Path
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# Default server configuration
DEFAULT_SERVER_URL = "http://localhost:8000"


def get_server_url() -> str:
    """Get server URL from environment or use default."""
    import os
    return os.getenv("RETAINR_SERVER_URL", DEFAULT_SERVER_URL)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """retainr CLI - Manage AI agent memories."""
    pass


@click.command()
@click.argument("memory_file", type=click.Path(exists=True, path_type=Path))
@click.option("--server", default=None, help="Server URL")
def save(memory_file: Path, server: Optional[str]):
    """Save a memory from JSON file to the server."""
    server_url = server or get_server_url()
    
    try:
        # Load memory from file
        with open(memory_file, 'r') as f:
            memory_data = json.load(f)
        
        # Validate required fields
        required_fields = ["project", "category", "content"]
        for field in required_fields:
            if field not in memory_data:
                console.print(f"[red]Error: Missing required field '{field}' in memory file[/red]")
                sys.exit(1)
        
        # Send to server
        with httpx.Client() as client:
            response = client.post(
                f"{server_url}/memory/",
                json=memory_data,
                timeout=30.0
            )
            response.raise_for_status()
            
            result = response.json()
            
            console.print(Panel.fit(
                f"[green]✓ Memory saved successfully![/green]\n\n"
                f"ID: {result['id']}\n"
                f"File: {result['file_path']}\n"
                f"Message: {result['message']}",
                title="Memory Saved"
            ))
            
    except FileNotFoundError:
        console.print(f"[red]Error: File '{memory_file}' not found[/red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in '{memory_file}': {e}[/red]")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error: Server returned {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]Error: Failed to connect to server at {server_url}: {e}[/red]")
        sys.exit(1)


@click.command()
@click.argument("query")
@click.option("--project", help="Filter by project name")
@click.option("--tags", help="Filter by tags (comma-separated)")
@click.option("--top", default=3, help="Number of results to return")
@click.option("--server", default=None, help="Server URL")
@click.option("--format", "output_format", default="rich", type=click.Choice(["rich", "json", "plain"]), help="Output format")
def recall(query: str, project: Optional[str], tags: Optional[str], top: int, server: Optional[str], output_format: str):
    """Search and recall memories using semantic similarity."""
    server_url = server or get_server_url()
    
    try:
        # Build query parameters
        params = {
            "query": query,
            "top": top
        }
        if project:
            params["project"] = project
        if tags:
            params["tags"] = tags
        
        # Search memories
        with httpx.Client() as client:
            response = client.get(
                f"{server_url}/memory/search",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            
            result = response.json()
            
            if output_format == "json":
                console.print(json.dumps(result, indent=2))
                return
            
            # Display results
            if not result["results"]:
                console.print(Panel.fit(
                    f"[yellow]No memories found for query: '{query}'[/yellow]",
                    title="Search Results"
                ))
                return
            
            if output_format == "rich":
                console.print(Panel.fit(
                    f"[blue]Query:[/blue] {query}\n"
                    f"[blue]Results:[/blue] {result['total']} memories found",
                    title="Memory Search"
                ))
                
                for i, memory in enumerate(result["results"], 1):
                    score_color = "green" if memory["score"] > 0.8 else "yellow" if memory["score"] > 0.6 else "red"
                    
                    console.print(f"\n[bold]{i}. Memory ID: {memory['id']}[/bold]")
                    console.print(f"[{score_color}]Relevance: {memory['score']:.3f}[/{score_color}]")
                    console.print(f"Project: {memory['entry']['project']}")
                    console.print(f"Category: {memory['entry']['category']}")
                    if memory['entry']['tags']:
                        console.print(f"Tags: {', '.join(memory['entry']['tags'])}")
                    
                    # Display content with markdown rendering
                    content = memory['entry']['content']
                    if len(content) > 300:
                        content = content[:300] + "..."
                    
                    console.print(Panel(
                        Markdown(content),
                        title=f"Content (Score: {memory['score']:.3f})",
                        border_style=score_color
                    ))
            
            elif output_format == "plain":
                console.print(f"Query: {query}")
                console.print(f"Found {result['total']} memories:")
                console.print("-" * 50)
                
                for i, memory in enumerate(result["results"], 1):
                    console.print(f"{i}. ID: {memory['id']} (Score: {memory['score']:.3f})")
                    console.print(f"   Project: {memory['entry']['project']}")
                    console.print(f"   Category: {memory['entry']['category']}")
                    console.print(f"   Content: {memory['entry']['content'][:200]}...")
                    console.print()
            
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error: Server returned {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]Error: Failed to connect to server at {server_url}: {e}[/red]")
        sys.exit(1)


@click.command()
@click.argument("memory_id")
@click.option("--outdated/--active", default=True, help="Mark as outdated or active")
@click.option("--server", default=None, help="Server URL")
def update(memory_id: str, outdated: bool, server: Optional[str]):
    """Update a memory entry (mark as outdated/active)."""
    server_url = server or get_server_url()
    
    try:
        with httpx.Client() as client:
            response = client.patch(
                f"{server_url}/memory/{memory_id}",
                json={"outdated": outdated},
                timeout=30.0
            )
            response.raise_for_status()
            
            result = response.json()
            status = "outdated" if outdated else "active"
            
            console.print(Panel.fit(
                f"[green]✓ Memory updated successfully![/green]\n\n"
                f"ID: {memory_id}\n"
                f"Status: {status}\n"
                f"Message: {result['message']}",
                title="Memory Updated"
            ))
            
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error: Server returned {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]Error: Failed to connect to server at {server_url}: {e}[/red]")
        sys.exit(1)


@click.command()
@click.option("--project", help="Filter by project name")
@click.option("--limit", default=10, help="Number of memories to list")
@click.option("--server", default=None, help="Server URL")
def list_memories(project: Optional[str], limit: int, server: Optional[str]):
    """List recent memories."""
    server_url = server or get_server_url()
    
    try:
        params = {"limit": limit}
        if project:
            params["project"] = project
        
        with httpx.Client() as client:
            response = client.get(
                f"{server_url}/memory/",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result["memories"]:
                filter_text = f" for project '{project}'" if project else ""
                console.print(f"[yellow]No memories found{filter_text}[/yellow]")
                return
            
            table = Table(title="Recent Memories")
            table.add_column("ID", style="cyan")
            table.add_column("Project", style="green")
            table.add_column("Category", style="blue")
            table.add_column("Tags", style="yellow")
            table.add_column("Status", style="red")
            table.add_column("Timestamp", style="dim")
            
            for memory in result["memories"]:
                status = "outdated" if memory["outdated"] else "active"
                status_style = "[red]outdated[/red]" if memory["outdated"] else "[green]active[/green]"
                tags = ", ".join(memory["tags"]) if memory["tags"] else "-"
                timestamp = memory["timestamp"][:19] if memory["timestamp"] else "-"
                
                table.add_row(
                    memory["id"][:8] + "...",
                    memory["project"],
                    memory["category"],
                    tags,
                    status_style,
                    timestamp
                )
            
            console.print(table)
            console.print(f"\nShowing {len(result['memories'])} of {result['total']} memories")
            
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error: Server returned {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]Error: Failed to connect to server at {server_url}: {e}[/red]")
        sys.exit(1)


@click.command()
@click.option("--server", default=None, help="Server URL")
def status(server: Optional[str]):
    """Check server status and statistics."""
    server_url = server or get_server_url()
    
    try:
        with httpx.Client() as client:
            # Check basic health
            response = client.get(f"{server_url}/health", timeout=10.0)
            response.raise_for_status()
            health = response.json()
            
            # Get collection stats
            stats_response = client.get(f"{server_url}/memory/stats/collection", timeout=10.0)
            stats_response.raise_for_status()
            stats = stats_response.json()
            
            console.print(Panel.fit(
                f"[green]✓ Server is healthy[/green]\n\n"
                f"URL: {server_url}\n"
                f"Memory Directory: {health['memory_dir']}\n"
                f"ChromaDB URL: {health['chroma_url']}\n"
                f"Embedding Model: {health['embedding_model']}\n"
                f"Total Memories: {stats.get('total_memories', 'N/A')}\n"
                f"Collection: {stats.get('collection_name', 'N/A')}",
                title="Server Status"
            ))
            
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error: Server returned {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)
    except httpx.RequestError as e:
        console.print(f"[red]Error: Failed to connect to server at {server_url}: {e}[/red]")
        sys.exit(1)


# Add commands to CLI group
cli.add_command(save)
cli.add_command(recall)
cli.add_command(update)
cli.add_command(list_memories, name="list")
cli.add_command(status)

if __name__ == "__main__":
    cli()