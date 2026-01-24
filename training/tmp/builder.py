#!/usr/bin/env python3
"""
Builder script for composing translated text blocks from components.
"""

import re
from pathlib import Path


def translate_into_conlang(text: str) -> str:
    """
    Dummy translation function - returns [TRANSLATED] marker for now.
    Will be replaced with actual translation logic.
    """
    return f"[{text}]"


def audit_block(block_text: str, components: list[str]) -> list[str]:
    """
    Find all text in a block that doesn't match any component.
    Returns list of unmatched fragments.
    """
    tokens = tokenize_block(block_text, components)
    unmatched = []
    current_unmatched = ""
    
    for token in tokens:
        if token['type'] == 'literal':
            char = token['value']
            # Skip whitespace, punctuation, newlines, formatting chars
            if char in ' \n\t.,;:!?*()[]{}"\'-':
                if current_unmatched.strip():
                    unmatched.append(current_unmatched.strip())
                current_unmatched = ""
            else:
                current_unmatched += char
        else:
            if current_unmatched.strip():
                unmatched.append(current_unmatched.strip())
            current_unmatched = ""
    
    if current_unmatched.strip():
        unmatched.append(current_unmatched.strip())
    
    return unmatched


def parse_components_file(filepath: str) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """
    Parse components.txt to extract:
    1. Component phrases organized by category
    2. Example blocks
    
    Returns:
        (components_by_category, example_blocks)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into components section and examples section
    parts = content.split("# EXAMPLE COMPOSITIONS")
    components_section = parts[0]
    examples_section = parts[1] if len(parts) > 1 else ""
    
    # Parse components by category
    components_by_category = {}
    current_category = None
    
    for line in components_section.split('\n'):
        line = line.rstrip()
        if line.startswith('## '):
            current_category = line[3:].strip()
            components_by_category[current_category] = []
        elif line.startswith('- ') and current_category:
            phrase = line[2:].strip()
            components_by_category[current_category].append(phrase)
    
    # Parse example blocks
    example_blocks = []
    current_block_name = None
    current_block_lines = []
    
    for line in examples_section.split('\n'):
        if line.startswith('## Block'):
            # Save previous block if exists
            if current_block_name and current_block_lines:
                block_text = '\n'.join(current_block_lines).strip()
                example_blocks.append((current_block_name, block_text))
            # Start new block
            current_block_name = line[3:].strip()
            current_block_lines = []
        elif current_block_name:
            current_block_lines.append(line)
    
    # Don't forget last block
    if current_block_name and current_block_lines:
        block_text = '\n'.join(current_block_lines).strip()
        example_blocks.append((current_block_name, block_text))
    
    return components_by_category, example_blocks


def get_all_components(components_by_category: dict[str, list[str]]) -> list[str]:
    """
    Flatten all components into a single list, sorted by length (longest first)
    so longer phrases get matched before shorter substrings.
    """
    all_components = []
    for category, phrases in components_by_category.items():
        all_components.extend(phrases)
    
    # Sort by length descending to match longer phrases first
    all_components.sort(key=len, reverse=True)
    return all_components


def build_translation_map(components: list[str]) -> dict[str, str]:
    """
    Build a mapping from original component to translated component.
    """
    translation_map = {}
    for component in components:
        translated = translate_into_conlang(component)
        translation_map[component] = translated
    return translation_map


def tokenize_block(block_text: str, components: list[str]) -> list[dict]:
    """
    Break a block into tokens: either component matches or literal text (formatting, etc.)
    Returns list of {'type': 'component'|'literal', 'original': str, 'value': str}
    """
    tokens = []
    remaining = block_text
    
    while remaining:
        # Try to match a component at the current position
        matched = False
        for component in components:
            if remaining.startswith(component):
                tokens.append({
                    'type': 'component',
                    'original': component,
                    'value': component
                })
                remaining = remaining[len(component):]
                matched = True
                break
        
        if not matched:
            # No component match - take one character as literal
            tokens.append({
                'type': 'literal',
                'original': remaining[0],
                'value': remaining[0]
            })
            remaining = remaining[1:]
    
    return tokens


def build_block_from_tokens(tokens: list[dict], translation_map: dict[str, str]) -> str:
    """
    Rebuild a block from tokens, translating component tokens.
    """
    result = []
    for token in tokens:
        if token['type'] == 'component':
            # Use the translated version
            translated = translation_map.get(token['original'], token['original'])
            result.append(translated)
        else:
            # Literal - keep as is (formatting, punctuation, whitespace, etc.)
            result.append(token['value'])
    return ''.join(result)


def translate_block(block_text: str, translation_map: dict[str, str], components: list[str]) -> str:
    """
    Translate a block by:
    1. Tokenizing into components and literals
    2. Rebuilding from translated components
    """
    tokens = tokenize_block(block_text, components)
    return build_block_from_tokens(tokens, translation_map)


def main():
    # Path to components file
    components_path = Path(__file__).parent / "components.txt"
    
    if not components_path.exists():
        print(f"Error: {components_path} not found")
        return
    
    # Parse the components file
    print("Parsing components.txt...")
    components_by_category, example_blocks = parse_components_file(str(components_path))
    
    # Report what we found
    print(f"\nFound {len(components_by_category)} categories:")
    for cat, phrases in components_by_category.items():
        print(f"  - {cat}: {len(phrases)} phrases")
    
    print(f"\nFound {len(example_blocks)} example blocks")
    
    # Get all components and build translation map
    all_components = get_all_components(components_by_category)
    print(f"\nTotal unique components: {len(all_components)}")
    
    translation_map = build_translation_map(all_components)
    
    # Translate and display each block
    print("\n" + "="*60)
    print("TRANSLATED BLOCKS")
    print("="*60)
    
    for block_name, block_text in example_blocks:
        print(f"\n## {block_name}")
        print("-" * 40)
        translated = translate_block(block_text, translation_map, all_components)
        print(translated)


if __name__ == "__main__":
    main()
