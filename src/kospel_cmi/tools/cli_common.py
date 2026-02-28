"""
Shared CLI argument parsing and backend creation for register scanner tools.

Used by register_scanner and live_scanner to avoid duplication of
--url/--yaml validation, backend instantiation, and cleanup logic.
"""

import argparse
import sys
from pathlib import Path
import aiohttp

from ..kospel.backend import (
    HttpRegisterBackend,
    RegisterBackend,
    YamlRegisterBackend,
)


def add_backend_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add --url and --yaml arguments to the parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--url",
        type=str,
        help="HTTP mode: base URL (e.g. http://192.168.1.1/api/dev/65)",
    )
    parser.add_argument(
        "--yaml",
        dest="yaml_path",
        type=str,
        metavar="PATH",
        help="YAML mode: path to state file (for offline/dev)",
    )


def add_scan_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add start_register and count positional arguments to the parser.

    Args:
        parser: ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "start_register",
        nargs="?",
        default="0b00",
        help="Starting register address (default: 0b00)",
    )
    parser.add_argument(
        "count",
        nargs="?",
        type=int,
        default=256,
        help="Number of registers to read (default: 256)",
    )


def create_backend_from_args(
    args: argparse.Namespace,
) -> RegisterBackend | None:
    """
    Validate url/yaml args and create backend.

    Args:
        args: Parsed arguments with url and yaml_path attributes.

    Returns:
        Backend on success. Caller must call backend.aclose() when done.
        None on validation failure (error printed to stderr).
    """
    if args.url and args.yaml_path:
        print("Error: Use either --url or --yaml, not both.", file=sys.stderr)
        return None
    if not args.url and not args.yaml_path:
        print(
            "Error: Specify --url for HTTP mode or --yaml for YAML (offline) mode.",
            file=sys.stderr,
        )
        return None

    if args.yaml_path:
        yaml_path = Path(args.yaml_path)
        if not yaml_path.is_absolute():
            yaml_path = Path.cwd() / yaml_path
        return YamlRegisterBackend(str(yaml_path.resolve()))

    session = aiohttp.ClientSession()
    return HttpRegisterBackend(session, args.url)
