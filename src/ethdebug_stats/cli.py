#!/usr/bin/env python3
"""
CLI entry point for ethdebug-stats tool.
"""

import argparse
import sys
from pathlib import Path

from .analyzer import EthdebugAnalyzer


def main():
    """Main entry point for the Ethdebug statistics tool."""
    parser = argparse.ArgumentParser(
        description="Calculate statistics for Ethdebug format debug information"
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to Ethdebug JSON file"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not args.file.exists():
        print(f"Error: File '{args.file}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Analyze the file
    analyzer = EthdebugAnalyzer(args.file)
    if not analyzer.load():
        sys.exit(1)
    
    analyzer.analyze()
    output = analyzer.format_output(args.format)
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()