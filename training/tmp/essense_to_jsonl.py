#!/usr/bin/env python3
"""
Convert essense.txt to essense.jsonl format for fine-tuning.
Format: English (user) -> Ur Djudeo-Mahikanítakh (assistant)
System message left blank to fill in manually.

Usage: python essense_to_jsonl.py
Note: Make sure essense.txt is saved before running.
"""

import json
from pathlib import Path

def main():
    input_file = Path(__file__).parent / "essense.txt"
    output_file = Path(__file__).parent / "essense.jsonl"
    
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    if not content:
        print("Error: essense.txt is empty. Please save the file first.")
        return
    
    # Split by the separator (dash on its own line)
    pairs = content.split("\n\n-\n\n")
    
    conversations = []
    
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        
        # Split into English and translation (two paragraphs separated by blank line)
        parts = pair.split("\n\n")
        
        if len(parts) >= 2:
            english = parts[0].strip()
            translation = parts[1].strip()
            
            conversation = {
                "messages": [
                    {"role": "system", "content": ""},
                    {"role": "user", "content": english},
                    {"role": "assistant", "content": translation}
                ]
            }
            conversations.append(conversation)
            print(f"  Added pair {len(conversations)}: {len(english)} chars -> {len(translation)} chars")
    
    # Write JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        for conv in conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + "\n")
    
    print(f"\nCreated {output_file} with {len(conversations)} conversations")

if __name__ == "__main__":
    main()
