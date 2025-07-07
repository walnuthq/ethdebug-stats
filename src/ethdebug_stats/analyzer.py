"""
Ethdebug Statistics Tool

Calculates quality metrics for Ethdebug format debug information,
similar to LLVM's dwarfdump --statistics.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class EthdebugStats:
    """Container for Ethdebug debug info quality statistics."""
    
    # File metadata
    version: int = 1
    file: str = ""
    format: str = "ethdebug"
    environment: str = ""
    contract_name: str = ""
    
    # === DEBUG INFO QUALITY METRICS ===
    
    # Source mapping coverage
    total_instructions: int = 0
    instructions_with_source: int = 0
    instructions_without_source: int = 0
    source_coverage_percent: float = 0.0
    
    # Source file information
    unique_source_files: int = 0
    source_files: List[int] = field(default_factory=list)
    
    # Context completeness
    instructions_with_context: int = 0
    instructions_with_code_context: int = 0
    instructions_with_variables: int = 0
    instructions_with_frame: int = 0
    
    # Variable debug info (for future when compiler supports it)
    total_variables: int = 0
    variables_with_location: int = 0
    variables_with_type: int = 0
    state_variables: int = 0
    local_variables: int = 0
    function_parameters: int = 0
    
    # Function-level statistics (derived from source ranges)
    estimated_functions: int = 0
    
    # Source location coverage distribution (like DWARF stats)
    # Buckets: 0%, (0-10%), [10-20%), ..., [90-100%), 100%
    coverage_distribution: Dict[str, int] = field(default_factory=dict)


class EthdebugAnalyzer:
    """Analyzes Ethdebug JSON files and generates debug info quality statistics."""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = None
        self.stats = EthdebugStats(file=str(filepath))
        
    def load(self) -> bool:
        """Load and validate Ethdebug JSON file."""
        try:
            with open(self.filepath, 'r') as f:
                self.data = json.load(f)
            return True
        except (json.JSONDecodeError, FileNotFoundError) as e:
            import sys
            print(f"Error loading file: {e}", file=sys.stderr)
            return False
            
    def analyze(self) -> EthdebugStats:
        """Analyze debug info quality in Ethdebug data."""
        if not self.data:
            return self.stats
            
        # Basic metadata
        self.stats.environment = self.data.get('environment', 'unknown')
        if 'contract' in self.data:
            self.stats.contract_name = self.data['contract'].get('name', 'unknown')
            
        # Analyze instructions and their debug info
        instructions = self.data.get('instructions', [])
        self.stats.total_instructions = len(instructions)
        
        # Track source coverage
        source_files: Set[int] = set()
        
        # Coverage calculation helpers
        instruction_ranges = []  # List of (has_source, range_size) for coverage distribution
        
        for instr in instructions:
            has_source = False
            has_context = False
            has_code_context = False
            
            # Analyze context information
            if 'context' in instr and instr['context']:
                has_context = True
                self.stats.instructions_with_context += 1
                
                context = instr['context']
                
                # Check for code context (source mapping)
                if 'code' in context:
                    has_code_context = True
                    self.stats.instructions_with_code_context += 1
                    
                    code = context['code']
                    if 'source' in code:
                        source_id = code['source'].get('id')
                        if source_id is not None:
                            has_source = True
                            source_files.add(source_id)
                            instruction_ranges.append((True, 0))
                
                # Check for variable context (future enhancement)
                if 'variables' in context:
                    self.stats.instructions_with_variables += 1
                    # Process variables when compiler supports it
                    self._analyze_variables(context['variables'])
                
                # Check for frame context
                if 'frame' in context:
                    self.stats.instructions_with_frame += 1
            
            if has_source:
                self.stats.instructions_with_source += 1
            else:
                self.stats.instructions_without_source += 1
                instruction_ranges.append((False, 0))
                
        
        # Calculate source coverage metrics
        self.stats.unique_source_files = len(source_files)
        self.stats.source_files = sorted(list(source_files))
        
        # Calculate coverage percentage
        if self.stats.total_instructions > 0:
            self.stats.source_coverage_percent = (
                self.stats.instructions_with_source / self.stats.total_instructions * 100
            )
        
        # Calculate coverage distribution
        self._calculate_coverage_distribution(instruction_ranges)
        
        # Estimate number of functions (simplified for now)
        # TODO: Improve this when we have better source range data
        self.stats.estimated_functions = 1 if source_files else 0
        
        return self.stats
    
    def _analyze_variables(self, variables):
        """Analyze variable debug information when available."""
        if isinstance(variables, list):
            for var in variables:
                self.stats.total_variables += 1
                
                if 'pointer' in var:
                    self.stats.variables_with_location += 1
                    # Check if it's a state variable (storage location)
                    if isinstance(var['pointer'], dict):
                        location = var['pointer'].get('location')
                        if location == 'storage':
                            self.stats.state_variables += 1
                        elif location in ('memory', 'stack', 'calldata'):
                            self.stats.local_variables += 1
                
                if 'type' in var:
                    self.stats.variables_with_type += 1
    
    def _calculate_coverage_distribution(self, instruction_ranges):
        """Calculate distribution of source coverage like DWARF statistics."""
        # Initialize buckets
        buckets = {
            "0%": 0,
            "(0-10%)": 0,
            "[10-20%)": 0,
            "[20-30%)": 0,
            "[30-40%)": 0,
            "[40-50%)": 0,
            "[50-60%)": 0,
            "[60-70%)": 0,
            "[70-80%)": 0,
            "[80-90%)": 0,
            "[90-100%)": 0,
            "100%": 0
        }
        
        # For now, simple binary classification since we don't have partial coverage
        # In future, could calculate based on source range sizes
        for has_source, _ in instruction_ranges:
            if has_source:
                buckets["100%"] += 1
            else:
                buckets["0%"] += 1
        
        self.stats.coverage_distribution = buckets
    
    
    def format_output(self, format_type: str = 'json') -> str:
        """Format statistics for output."""
        if format_type == 'json':
            return self._format_json()
        elif format_type == 'text':
            return self._format_text()
        else:
            raise ValueError(f"Unknown format type: {format_type}")
    
    def _format_json(self) -> str:
        """Format statistics as JSON with focus on debug info quality."""
        output = {
            "version": self.stats.version,
            "file": self.stats.file,
            "format": self.stats.format,
            "environment": self.stats.environment,
            "contract_name": self.stats.contract_name,
            
            # Core debug info metrics
            "#instructions": self.stats.total_instructions,
            "#instructions_with_source": self.stats.instructions_with_source,
            "#instructions_without_source": self.stats.instructions_without_source,
            "source_coverage_percent": round(self.stats.source_coverage_percent, 2),
            
            # Source information
            "#unique_source_files": self.stats.unique_source_files,
            
            # Context completeness
            "#instructions_with_context": self.stats.instructions_with_context,
            "#instructions_with_code_context": self.stats.instructions_with_code_context,
            "#instructions_with_variables": self.stats.instructions_with_variables,
            "#instructions_with_frame": self.stats.instructions_with_frame,
            
            # Variable debug info (when available)
            "#variables": self.stats.total_variables,
            "#variables_with_location": self.stats.variables_with_location,
            "#variables_with_type": self.stats.variables_with_type,
            "#state_variables": self.stats.state_variables,
            "#local_variables": self.stats.local_variables,
            "#function_parameters": self.stats.function_parameters,
            
            # Function estimation
            "#estimated_functions": self.stats.estimated_functions,
            
            # Coverage distribution
            "coverage_distribution": self.stats.coverage_distribution
        }
        
        return json.dumps(output, indent=2)
    
    def _format_text(self) -> str:
        """Format statistics as human-readable text focused on debug quality."""
        lines = []
        lines.append(f"Ethdebug Statistics for {self.stats.file}")
        lines.append("=" * 60)
        lines.append(f"Environment: {self.stats.environment}")
        lines.append(f"Contract: {self.stats.contract_name}")
        lines.append("")
        
        lines.append("DEBUG INFO QUALITY METRICS:")
        lines.append("-" * 30)
        
        lines.append("\nSource Mapping Coverage:")
        lines.append(f"  Total instructions: {self.stats.total_instructions}")
        lines.append(f"  With source mapping: {self.stats.instructions_with_source}")
        lines.append(f"  Without source mapping: {self.stats.instructions_without_source}")
        lines.append(f"  Coverage: {self.stats.source_coverage_percent:.1f}%")
        lines.append("")
        
        lines.append("Source Information:")
        lines.append(f"  Unique source files: {self.stats.unique_source_files}")
        lines.append(f"  Estimated functions: {self.stats.estimated_functions}")
        lines.append("")
        
        lines.append("Context Completeness:")
        lines.append(f"  Instructions with context: {self.stats.instructions_with_context}")
        lines.append(f"  With code context: {self.stats.instructions_with_code_context}")
        lines.append(f"  With variables: {self.stats.instructions_with_variables}")
        lines.append(f"  With frame info: {self.stats.instructions_with_frame}")
        lines.append("")
        
        if self.stats.total_variables > 0:
            lines.append("Variable Debug Info:")
            lines.append(f"  Total variables: {self.stats.total_variables}")
            lines.append(f"  With location: {self.stats.variables_with_location}")
            lines.append(f"  With type info: {self.stats.variables_with_type}")
            lines.append(f"  State variables: {self.stats.state_variables}")
            lines.append(f"  Local variables: {self.stats.local_variables}")
            lines.append(f"  Function parameters: {self.stats.function_parameters}")
            lines.append("")
        
        lines.append("Coverage Distribution:")
        for bucket, count in self.stats.coverage_distribution.items():
            if count > 0:
                lines.append(f"  {bucket}: {count} instructions")
        
        return "\n".join(lines)