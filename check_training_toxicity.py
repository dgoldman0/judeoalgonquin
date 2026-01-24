#!/usr/bin/env python3
"""
Check training JSONL files for toxic Unicode/control characters that can crash trainers.

Detects:
- Invalid UTF-8 bytes
- Lone UTF-16 surrogate codepoints
- Invisible control chars (bidi controls, null bytes, etc.)
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Unicode ranges and specific characters to flag
BIDI_CONTROLS = {
    '\u202A': 'LEFT-TO-RIGHT EMBEDDING',
    '\u202B': 'RIGHT-TO-LEFT EMBEDDING',
    '\u202C': 'POP DIRECTIONAL FORMATTING',
    '\u202D': 'LEFT-TO-RIGHT OVERRIDE',
    '\u202E': 'RIGHT-TO-LEFT OVERRIDE',
    '\u2066': 'LEFT-TO-RIGHT ISOLATE',
    '\u2067': 'RIGHT-TO-LEFT ISOLATE',
    '\u2068': 'FIRST STRONG ISOLATE',
    '\u2069': 'POP DIRECTIONAL ISOLATE',
}

OTHER_CONTROL_CHARS = {
    '\u0000': 'NULL',
    '\u200E': 'LEFT-TO-RIGHT MARK',
    '\u200F': 'RIGHT-TO-LEFT MARK',
    '\u200B': 'ZERO WIDTH SPACE',
    '\u200C': 'ZERO WIDTH NON-JOINER',
    '\u200D': 'ZERO WIDTH JOINER',
    '\uFEFF': 'ZERO WIDTH NO-BREAK SPACE',
}

# Combine all control chars
ALL_CONTROL_CHARS = {**BIDI_CONTROLS, **OTHER_CONTROL_CHARS}

def is_surrogate(codepoint: int) -> bool:
    """Check if codepoint is a lone UTF-16 surrogate."""
    return 0xD800 <= codepoint <= 0xDFFF

def check_string_for_issues(text: str) -> List[str]:
    """Check a string for toxic Unicode issues."""
    issues = []
    
    # Check for invalid UTF-8 (as much as we can after Python decoding)
    try:
        text.encode('utf-8')
    except UnicodeEncodeError as e:
        issues.append(f"UTF-8 encoding error: {e}")
    
    # Check for lone surrogates
    for i, char in enumerate(text):
        codepoint = ord(char)
        if is_surrogate(codepoint):
            issues.append(f"Lone UTF-16 surrogate at position {i}: U+{codepoint:04X}")
        
        # Check for control characters
        if char in ALL_CONTROL_CHARS:
            issues.append(f"Control char at position {i}: {ALL_CONTROL_CHARS[char]} (U+{codepoint:04X})")
    
    return issues

def check_jsonl_file(filepath: Path) -> Tuple[int, List[Tuple[int, dict]]]:
    """
    Check a JSONL file for toxic content.
    Returns (total_lines, [(line_num, issues_dict), ...])
    """
    problems = []
    total_lines = 0
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                total_lines = line_num
                line = line.rstrip('\n\r')
                
                if not line or line.isspace():
                    continue
                
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    problems.append((line_num, {'error': f'JSON decode error: {e}'}))
                    continue
                
                # Check all string values in the JSON object
                line_issues = check_json_object(obj)
                if line_issues:
                    problems.append((line_num, line_issues))
    
    except UnicodeDecodeError as e:
        problems.append((0, {'error': f'File decoding error: {e}'}))
    
    return total_lines, problems

def check_json_object(obj, path='') -> dict:
    """Recursively check JSON object for toxic strings."""
    issues = {}
    
    if isinstance(obj, str):
        string_issues = check_string_for_issues(obj)
        if string_issues:
            issues[path or 'root'] = string_issues
    elif isinstance(obj, dict):
        for key, value in obj.items():
            nested_issues = check_json_object(value, f'{path}.{key}' if path else key)
            issues.update(nested_issues)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            nested_issues = check_json_object(item, f'{path}[{i}]')
            issues.update(nested_issues)
    
    return issues

def main():
    training_dir = Path(__file__).parent / 'training'
    
    if not training_dir.exists():
        print(f"Training directory not found: {training_dir}")
        return
    
    jsonl_files = sorted(training_dir.glob('*.jsonl'))
    
    if not jsonl_files:
        print(f"No JSONL files found in {training_dir}")
        return
    
    print(f"Checking {len(jsonl_files)} JSONL files in {training_dir}\n")
    
    total_problems = 0
    
    for filepath in jsonl_files:
        print(f"Checking: {filepath.name}")
        total_lines, problems = check_jsonl_file(filepath)
        
        if problems:
            print(f"  ⚠️  Found {len(problems)} lines with issues (out of {total_lines})")
            total_problems += len(problems)
            
            # Show first few issues
            for line_num, issues_dict in problems[:5]:
                print(f"    Line {line_num}:")
                for key, issue_list in issues_dict.items():
                    for issue in issue_list:
                        print(f"      [{key}] {issue}")
            
            if len(problems) > 5:
                print(f"    ... and {len(problems) - 5} more issues")
        else:
            print(f"  ✓ All {total_lines} lines OK")
        print()
    
    print(f"\n{'='*60}")
    print(f"Summary: {total_problems} problematic lines found")
    if total_problems == 0:
        print("✓ Training set looks clean!")
    else:
        print(f"⚠️  Found issues that could crash training")

if __name__ == '__main__':
    main()
