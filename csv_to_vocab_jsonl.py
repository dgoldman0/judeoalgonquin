#!/usr/bin/env python3
"""
Convert algonquin_vocab_900plus.csv to JSONL training format.
Creates conversations where the model learns to guess Algonquin words
and identify their language group.
"""

import csv
import json
import sys

def parse_region_info(region_str):
    """Parse region string into language group and subgroup."""
    if ';' in region_str:
        parts = [p.strip() for p in region_str.split(';')]
        return parts[0], parts[1] if len(parts) > 1 else "Unknown"
    return region_str.strip(), "Unknown"

def create_training_message(english_word, algonquin_word, language_group, subgroup):
    """Create a single training message in the required format."""
    return {
        "messages": [
            {
                "role": "system",
                "content": "You have an approximate working understanding of Algonquin languages."
            },
            {
                "role": "user",
                "content": f"Guess what word or words are the closest Algonquin word for '{english_word}'. Be brief."
            },
            {
                "role": "assistant",
                "content": algonquin_word
            },
            {
                "role": "user",
                "content": "Which Algonquin language group is that from?"
            },
            {
                "role": "assistant",
                "content": f"{language_group}" + (f" - {subgroup}" if subgroup and subgroup != "Unknown" else "")
            }
        ]
    }

def main():
    input_file = "algonquin_vocab_900plus.csv"
    output_file = "training/algonquin-vocab.jsonl"
    
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            
            with open(output_file, 'w', encoding='utf-8') as outfile:
                for row_num, row in enumerate(reader, 1):
                    english = row['English'].strip()
                    algonquin = row['Algonquin'].strip()
                    region_info = row['region; subregion'].strip()
                    
                    language_group, subgroup = parse_region_info(region_info)
                    
                    message = create_training_message(english, algonquin, language_group, subgroup)
                    outfile.write(json.dumps(message) + '\n')
                    
                print(f"✓ Successfully created {output_file}")
                print(f"  Total entries: {row_num}")
                
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
