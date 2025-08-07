"""Entry point for running the standard MCP server."""

import logging
import sys

from .standard_mcp import run_server

if __name__ == "__main__":
    # Configure logging for production
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(
                sys.stderr
            )  # Log to stderr to avoid interfering with stdio transport
        ],
    )

    try:
        run_server()
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Server failed: {e}")
        sys.exit(1)
