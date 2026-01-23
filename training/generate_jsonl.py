#!/usr/bin/env python3
"""
Generate JSONL training files for Ur Djudeo-Mahikanítakh from CSV source files.

Converts:
  - prototype.csv → prototype.jsonl (English→Conlang phrase translation)
  - reverse.csv → reverse.jsonl (Conlang→English phrase translation)
  - vocabulary.csv → vocabulary.jsonl (English→Conlang vocabulary)
  - vocab-reverse.csv → vocab-reverse.jsonl (Conlang→English vocabulary)
"""

import csv
import json
from pathlib import Path

# English system prompt for forward-direction files
SYSTEM_PROMPT_EN = (
    "You are an expert in Ur Djudeo-Mahikanítakh, a constructed fusion language "
    "blending Eastern Algonquian languages (primarily Munsee/Lenape) with Hebrew. "
    "You help users translate between English and Ur Djudeo-Mahikanítakh, and "
    "explain the linguistic principles behind each translation."
)

# Ur Djudeo-Mahikanítakh system prompt for reverse-direction files
# Built entirely from existing vocabulary and grammatical structures
SYSTEM_PROMPT_CONLANG = (
    "נֶמִּינֵין עֶזְרָה לְתַרְגֵּם בֵּין אַנְגְּלִית וְאוּר דְּיוּדֵאוֹ-מָהִיקָאנִיטָאך. בַּשָּׂפָה הַזֹּאת, לָשׁוֹן אַלְגוֹנְקְוִין מִזְרָחִית—מוּנְסִי, לֶנַאפֶּה—וְעִבְרִית "
    "נֶאוֹשֵׁין בְּיַחַד. פֹּעֲלִים אַלְגוֹנְקְוִינִיִּים—מִּינֵין לָתֵת, וָאפּוּוָא לִרְאוֹת, מְנוֹקוְויֵין לָלֶכֶת יָפֶה—נוֹשְׂאִים אֶת הַפְּעֻלָּה. "
    "עִבְרִית נוֹתֶנֶת אֶת הַמִּלִּים הַקְּטַנּוֹת: ב־, ל־, וְ. נֶוָאפּוּוֵין אֶת הָעִקְרוֹנוֹת שֶׁמֵּאֲחוֹרֵי כָּל תַּרְגּוּם."
)

def create_training_example(messages: list[dict], system_prompt: str) -> dict:
    """Wrap messages in standard JSONL training format."""
    return {"messages": [{"role": "system", "content": system_prompt}] + messages}


def process_prototype(input_path: Path, output_path: Path) -> int:
    """
    prototype.csv → prototype.jsonl
    Columns: english, conlang, explanation
    """
    count = 0
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        for row in reader:
            english = row['english'].strip()
            conlang = row['conlang'].strip()
            explanation = row['explanation'].strip()
            
            messages = [
                {"role": "user", "content": f"How would I approach translating '{english}' into Ur Djudeo-Mahikanítakh?"},
                {"role": "assistant", "content": explanation},
                {"role": "user", "content": f"Now give me the full translation of '{english}' into Ur Djudeo-Mahikanítakh."},
                {"role": "assistant", "content": conlang},
            ]
            
            outfile.write(json.dumps(create_training_example(messages, SYSTEM_PROMPT_EN), ensure_ascii=False) + '\n')
            count += 1
    return count


def process_reverse(input_path: Path, output_path: Path) -> int:
    """
    reverse.csv → reverse.jsonl
    Columns: conlang, english, explanation_in_conlang
    User prompts are in Ur Djudeo-Mahikanítakh.
    """
    count = 0
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        for row in reader:
            conlang = row['conlang'].strip()
            english = row['english'].strip()
            explanation = row['explanation_in_conlang'].strip()
            
            messages = [
                {"role": "user", "content": f"אֵיךְ אֶתְרַגֵּם אֶת '{conlang}' לְאַנְגְּלִית?"},
                {"role": "assistant", "content": explanation},
                {"role": "user", "content": "תֵּן לִי אֶת הַתַּרְגּוּם הַמָּלֵא לְאַנְגְּלִית."},
                {"role": "assistant", "content": english},
            ]
            
            outfile.write(json.dumps(create_training_example(messages, SYSTEM_PROMPT_CONLANG), ensure_ascii=False) + '\n')
            count += 1
    return count


def process_vocabulary(input_path: Path, output_path: Path) -> int:
    """
    vocabulary.csv → vocabulary.jsonl
    Columns: english, conlang, etymology
    """
    count = 0
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        for row in reader:
            english = row['english'].strip()
            conlang = row['conlang'].strip()
            etymology = row['etymology'].strip()
            
            messages = [
                {"role": "user", "content": f"What is the Ur Djudeo-Mahikanítakh word for '{english}'?"},
                {"role": "assistant", "content": conlang},
                {"role": "user", "content": f"Explain the etymology of '{conlang}'."},
                {"role": "assistant", "content": etymology},
            ]
            
            outfile.write(json.dumps(create_training_example(messages, SYSTEM_PROMPT_EN), ensure_ascii=False) + '\n')
            count += 1
    return count


def process_vocab_reverse(input_path: Path, output_path: Path) -> int:
    """
    vocab-reverse.csv → vocab-reverse.jsonl
    Columns: conlang, english, etymology_in_conlang
    User prompts are in Ur Djudeo-Mahikanítakh.
    """
    count = 0
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        for row in reader:
            conlang = row['conlang'].strip()
            english = row['english'].strip()
            etymology = row['etymology_in_conlang'].strip()
            
            messages = [
                {"role": "user", "content": f"מַה הַתַּרְגּוּם לְאַנְגְּלִית שֶׁל '{conlang}'?"},
                {"role": "assistant", "content": english},
                {"role": "user", "content": f"הַסְבֵּר אֶת הָאֶטִימוֹלוֹגְיָה שֶׁל '{conlang}'."},
                {"role": "assistant", "content": etymology},
            ]
            
            outfile.write(json.dumps(create_training_example(messages, SYSTEM_PROMPT_CONLANG), ensure_ascii=False) + '\n')
            count += 1
    return count


def main():
    base_dir = Path(__file__).parent
    
    conversions = [
        ("prototype.csv", "prototype.jsonl", process_prototype),
        ("reverse.csv", "reverse.jsonl", process_reverse),
        ("vocabulary.csv", "vocabulary.jsonl", process_vocabulary),
        ("vocab-reverse.csv", "vocab-reverse.jsonl", process_vocab_reverse),
    ]
    
    print("Generating JSONL training files for Ur Djudeo-Mahikanítakh...\n")
    
    total = 0
    for csv_name, jsonl_name, processor in conversions:
        csv_path = base_dir / csv_name
        jsonl_path = base_dir / jsonl_name
        
        if not csv_path.exists():
            print(f"⚠ Skipping {csv_name} (file not found)")
            continue
        
        count = processor(csv_path, jsonl_path)
        total += count
        print(f"✓ {csv_name} → {jsonl_name}: {count} training examples")
    
    print(f"\n✓ Done! Generated {total} total training examples.")


if __name__ == "__main__":
    main()
