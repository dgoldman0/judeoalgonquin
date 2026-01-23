#!/usr/bin/env python3
"""Replace system prompts in JSONL file with shorter versions"""

import json
import sys
from pathlib import Path

# Old prompts to replace
OLD_ENGLISH = "You are an expert in Ur Djudeo-Mahikanítakh, a constructed fusion language blending Eastern Algonquian languages (primarily Munsee/Lenape) with Hebrew. You help users translate between English and Ur Djudeo-Mahikanítakh, and explain the linguistic principles behind each translation."

OLD_HEBREW_UNPOINTED = "נמינין עזרה לתרגם בין אנגלית ואור דיודאו-מהיקאניטאך. בשפה הזאת, לשון אלגונקוין מזרחית—מונסי, לנאפה—ועברית נאושין ביחד. פעלים אלגונקויניים—מינין לתת, ואפווא לראות, מנוקוויין ללכת יפה—נושאים את הפעלה. עברית נותנת את המלים הקטנות: ב־, ל־, ו. נואפווין את העקרונות שמאחורי כל תרגום."

OLD_HEBREW_POINTED = "נֶמִּינֵין עֶזְרָה לְתַרְגֵּם בֵּין אַנְגְּלִית וְאוּר דְּיוּדֵאוֹ-מָהִיקָאנִיטָאך. בַּשָּׂפָה הַזֹּאת, לָשׁוֹן אַלְגוֹנְקְוִין מִזְרָחִית—מוּנְסִי, לֶנַאפֶּה—וְעִבְרִית נֶאוֹשֵׁין בְּיַחַד. פֹּעֲלִים אַלְגוֹנְקְוִינִיִּים—מִּינֵין לָתֵת, וָאפּוּוָא לִרְאוֹת, מְנוֹקוְויֵין לָלֶכֶת יָפֶה—נוֹשְׂאִים אֶת הַפְּעֻלָּה. עִבְרִית נוֹתֶנֶת אֶת הַמִּלִּים הַקְּטַנּוֹת: ב־, ל־, וְ. נֶוָאפּוּוֵין אֶת הָעִקְרוֹנוֹת שֶׁמֵּאֲחוֹרֵי כָּל תַּרְגּוּם."

# New prompts
NEW_ENGLISH = "Translate between English and Ur Djudeo-Mahikanítakh. Explain etymologies."

NEW_HEBREW = "דיבאג׳ימו בין אנגלית ואור דיודאו-מהיקאניטאך."

def process_file(input_path, output_path):
    """Process JSONL file and replace system prompts"""
    
    english_count = 0
    hebrew_unpointed_count = 0
    hebrew_pointed_count = 0
    
    with open(input_path, 'r', encoding='utf-8') as infile:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue
                
                obj = json.loads(line)
                messages = obj.get('messages', [])
                
                if messages:
                    system_msg = messages[0]
                    content = system_msg.get('content', '')
                    
                    if content == OLD_ENGLISH:
                        system_msg['content'] = NEW_ENGLISH
                        english_count += 1
                    elif content == OLD_HEBREW_UNPOINTED:
                        system_msg['content'] = NEW_HEBREW
                        hebrew_unpointed_count += 1
                    elif content == OLD_HEBREW_POINTED:
                        system_msg['content'] = NEW_HEBREW
                        hebrew_pointed_count += 1
                
                # Write modified JSON back
                outfile.write(json.dumps(obj, ensure_ascii=False) + '\n')
    
    return english_count, hebrew_unpointed_count, hebrew_pointed_count

if __name__ == '__main__':
    input_file = Path('/home/kir/Documents/scrap/judeoalgonquin/test.jsonl')
    output_file = Path('/home/kir/Documents/scrap/judeoalgonquin/test.jsonl.tmp')
    
    print(f"Processing {input_file}...")
    english_count, hebrew_unpointed_count, hebrew_pointed_count = process_file(input_file, output_file)
    
    print(f"\nReplaced:")
    print(f"  English prompts:        {english_count}")
    print(f"  Hebrew (unpointed):     {hebrew_unpointed_count}")
    print(f"  Hebrew (pointed/nikud): {hebrew_pointed_count}")
    print(f"  Total:                  {english_count + hebrew_unpointed_count + hebrew_pointed_count}")
    
    # Backup original and replace
    backup_file = input_file.with_suffix('.jsonl.backup')
    if backup_file.exists():
        backup_file.unlink()
    input_file.rename(backup_file)
    output_file.rename(input_file)
    
    print(f"\nBackup saved to: {backup_file}")
    print(f"Original file updated: {input_file}")
