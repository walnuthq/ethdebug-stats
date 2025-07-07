"""
Ethdebug Statistics Tool

A tool for analyzing and evaluating the quality of Ethdebug format debug information.
"""

from .analyzer import EthdebugAnalyzer, EthdebugStats

__version__ = "0.1.0"
__all__ = ["EthdebugAnalyzer", "EthdebugStats"]