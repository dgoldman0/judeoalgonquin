#!/usr/bin/env python3
"""
Convert CSV conversations to JSONL training data format.
Applies a conlang translation function to each message.
"""

import json
import csv
from pathlib import Path
import openai

model = "ur-djudeo-mahikanitakh"

client = openai.Client()

def translate_into_conlang(text: str) -> str:
    """
    Translate given text into Ur Djudeo-Mahikanítakh using OpenAI API.
    """

    system_prompt = "Translate between English and Ur Djudeo-Mahikanítakh."
    user = "Translate the following text into Ur Djudeo-Mahikanítakh:\n\n" + text

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user}
        ],
        temperature=0.7,
        max_tokens=1000,
    )
    translation = response.choices[0].message.content.strip()
    return translation
    
def parse_csv_to_conversations(csv_file: str, test_mode: bool) -> list[dict]:
    """
    Parse CSV file where each line is a conversation delimited by |||
    Returns list of conversation dictionaries.
    """
    conversations = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Split by ||| delimiter
            parts = line.split('|||')
            
            if len(parts) < 3:
                continue  # Need at least system, user, agent
            
            # Build messages list
            messages = []
            
            # Add system message
            system_msg = parts[0].strip()
            messages.append({
                "role": "system",
                "content": translate_into_conlang(system_msg)
            })
            
            # Add alternating user/assistant messages
            try:
                for i in range(1, len(parts)):
                    content = parts[i].strip()
                    if i % 2 == 1:  # Odd indices are user messages
                        role = "user"
                    else:  # Even indices are assistant messages
                        role = "assistant"
                    
                    messages.append({
                        "role": role,
                        "content": translate_into_conlang(content)
                    })
            except Exception as e:
                print(f"Error translating message: {e}")
            
            conversations.append({"messages": messages})

            if test_mode:
                break  # Process only first conversation in test mode
    
    return conversations


def write_jsonl(conversations: list[dict], output_file: str) -> None:
    """
    Write conversations to JSONL file (one JSON object per line).
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for conv in conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + '\n')


def main():
    script_dir = Path(__file__).parent
    csv_file = script_dir / "sample.csv"
    output_file = script_dir / "conversations.jsonl"
    
    print(f"Reading from: {csv_file}")
    if not csv_file.exists():
        print(f"Error: {csv_file} not found")
        return
    
    # Parse conversations
    conversations = parse_csv_to_conversations(str(csv_file), True)
    print(f"Parsed {len(conversations)} conversations")
    
    # Write to JSONL
    write_jsonl(conversations, str(output_file))
    print(f"Wrote to: {output_file}")
    
    # Print first conversation as example
    if conversations:
        print("\nExample first conversation:")
        print(json.dumps(conversations[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
