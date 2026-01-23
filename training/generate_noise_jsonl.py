#!/usr/bin/env python3
"""
Generate noise.jsonl by sampling from all four training files
and stripping nikud (vowel points) for noise variation.
"""

import json
import random
from pathlib import Path
import unicodedata

# Hebrew diacritical marks to strip
HEBREW_DIACRITICS = {
    '\u05B0',  # HEBREW SHWA
    '\u05B1',  # HEBREW HATAF SEGOL
    '\u05B2',  # HEBREW HATAF PATAH
    '\u05B3',  # HEBREW HATAF QAMATS
    '\u05B4',  # HEBREW HIRIQ
    '\u05B5',  # HEBREW TSERE
    '\u05B6',  # HEBREW SEGOL
    '\u05B7',  # HEBREW PATAH
    '\u05B8',  # HEBREW QAMATS
    '\u05B9',  # HEBREW HOLAM
    '\u05BA',  # HEBREW HOLAM HASER FOR VAV
    '\u05BB',  # HEBREW QUBUTS
    '\u05BC',  # HEBREW DAGESH
    '\u05BD',  # HEBREW HEBREW POINT METEG
    '\u05BF',  # HEBREW RAFE
    '\u05C1',  # HEBREW POINT SHIN DOT
    '\u05C2',  # HEBREW POINT SIN DOT
    '\u05C4',  # HEBREW MARK UPPER DOT
    '\u05C5',  # HEBREW MARK LOWER DOT
}

def strip_nikud(text: str) -> str:
    """Remove all Hebrew diacritical marks from text."""
    return ''.join(c for c in text if c not in HEBREW_DIACRITICS)

def remove_nikud_from_example(example: dict) -> dict:
    """Strip nikud from all message contents in an example."""
    result = {"messages": []}
    for msg in example["messages"]:
        new_msg = msg.copy()
        new_msg["content"] = strip_nikud(msg["content"])
        result["messages"].append(new_msg)
    return result

def main():
    base_dir = Path(__file__).parent
    
    source_files = [
        "prototype.jsonl",
        "reverse.jsonl",
        "vocabulary.jsonl",
        "vocab-reverse.jsonl",
    ]
    
    output_path = base_dir / "noise.jsonl"
    
    # Sample size per file
    SAMPLE_PER_FILE = 25
    
    print(f"Generating noise.jsonl with {SAMPLE_PER_FILE} samples from each file...\n")
    
    all_examples = []
    
    # Load and sample from each file
    for source_file in source_files:
        source_path = base_dir / source_file
        if not source_path.exists():
            print(f"⚠ Skipping {source_file} (not found)")
            continue
        
        with open(source_path, 'r', encoding='utf-8') as f:
            examples = [json.loads(line) for line in f]
            sampled = random.sample(examples, min(SAMPLE_PER_FILE, len(examples)))
            all_examples.extend(sampled)
            print(f"✓ Sampled {len(sampled)} examples from {source_file}")
    
    print(f"\nTotal examples in noise.jsonl: {len(all_examples)}")
    
    # Shuffle and write with nikud stripped
    random.shuffle(all_examples)
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for example in all_examples:
            noisy_example = remove_nikud_from_example(example)
            outfile.write(json.dumps(noisy_example, ensure_ascii=False) + '\n')
    
    print(f"✓ Generated noise.jsonl with {len(all_examples)} examples (nikud stripped)")

if __name__ == "__main__":
    main()
