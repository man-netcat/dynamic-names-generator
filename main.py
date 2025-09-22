#!/usr/bin/env python3
"""
EU4 Dynamic Names Generator - Main Entry Point

This module provides the main entry point for the EU4 Dynamic Names Generator.
All the actual implementation is in the src/ folder for better organization.
"""

from src.generator import build_modules, generate_on_actions, generate_decision
from src.defines.paths import MODULES_ROOT


def main():
    """Main entry point for the EU4 Dynamic Names Generator."""
    build_modules(MODULES_ROOT)
    generate_on_actions()
    generate_decision()


if __name__ == "__main__":
    main()
