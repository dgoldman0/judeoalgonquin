import json
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize OpenAI client (uses OPENAI_API_KEY from environment)
client = OpenAI()

def translate_to_ur_djudeo(text):
    """
    Translate English text to Ur Djudeo-Mahikanítakh using the fine-tuned model.
    
    Args:
        text: English text to translate
        
    Returns:
        Translated text in Ur Djudeo-Mahikanítakh
    """
    response = client.chat.completions.create(
        model="ft:gpt-4.1-mini-2025-04-14:personal:ur-djudeo-mahikanitakh-extended-finetune:D2FRzjR0",
        messages=[
            {"role": "system", "content": "Translate between English and Ur Djudeo-Mahikanítakh."},
            {"role": "user", "content": f"Translate into Ur Djudeo-Mahikanítakh. Exclude any explanation, just give the final translation. If multiple options exist for the translation, give only one. If no known word is available, take a native Hebrew word and adjust its morphology to align more closely with Algonquin. All translations must be fully in Ur Djudeo-Mahikanítakh, except for specific proper nouns, symbols, etc. that generally would not get translated:\n{text}"}
        ],
        temperature=0.1
    )
    
    return response.choices[0].message.content


def translate_jsonl_file(input_file, output_file, max_workers=4):
    """
    Translate all user and assistant messages in a JSONL file,
    leaving system messages in English.
    
    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSONL file
        max_workers: Number of parallel threads for translation (default: 4)
    """
    # First, read all lines and parse them
    print("Reading input file...")
    conversations = []
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                conversations.append((line_num, data))
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
    
    print(f"Found {len(conversations)} conversations to translate\n")
    
    # Process conversations in parallel
    def process_conversation(item):
        line_num, data = item
        translated_data = {"messages": []}
        
        # Process each message in the conversation
        for message in data["messages"]:
            role = message["role"]
            content = message["content"]
            
            # Only translate user and assistant messages, keep system in English
            if role in ["user", "assistant"]:
                translated_content = translate_to_ur_djudeo(content)
                translated_data["messages"].append({
                    "role": role,
                    "content": translated_content
                })
            else:  # system message
                # Append the language assumption note to system messages
                system_content = content + " The user is assumed to be writing in Ur Djudeo-Mahikanítakh unless it is otherwise clear."
                translated_data["messages"].append({
                    "role": role,
                    "content": system_content
                })
        
        return line_num, translated_data
    
    # Use ThreadPoolExecutor for parallel processing
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_line = {executor.submit(process_conversation, conv): conv[0] 
                          for conv in conversations}
        
        # Process completed tasks with progress bar
        with tqdm(total=len(conversations), desc="Translating", unit="conv") as pbar:
            for future in as_completed(future_to_line):
                try:
                    line_num, translated_data = future.result()
                    results[line_num] = translated_data
                    pbar.update(1)
                except Exception as e:
                    line_num = future_to_line[future]
                    print(f"\nError processing line {line_num}: {e}")
                    pbar.update(1)
    
    # Write results in order
    print("\nWriting output file...")
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for line_num in sorted(results.keys()):
            outfile.write(json.dumps(results[line_num], ensure_ascii=False) + '\n')


def main():
    input_file = "sample.jsonl"
    output_file = "sample_translated.jsonl"
    max_workers = 10  # Number of parallel threads
    
    print(f"Starting translation from {input_file} to {output_file}...")
    print(f"Using {max_workers} parallel threads")
    print("=" * 60)
    
    translate_jsonl_file(input_file, output_file, max_workers=max_workers)
    
    print("=" * 60)
    print(f"Translation complete! Output saved to {output_file}")


if __name__ == "__main__":
    main()
