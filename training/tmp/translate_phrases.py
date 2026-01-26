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
            {"role": "system", "content": "You are an expert in Ur Djudeo-Mahikanítakh."},
            {"role": "user", "content": f"Translate into Ur Djudeo-Mahikanítakh (exclude any explanation, just give the final translation):\n{text}"}
        ]
    )
    
    return response.choices[0].message.content


def translate_phrases_file(input_file, output_file, max_workers=4):
    """
    Read phrases from a text file and create JSONL training data with translations.
    
    Args:
        input_file: Path to input text file (one phrase per line)
        output_file: Path to output JSONL file
        max_workers: Number of parallel threads for translation (default: 4)
    """
    # Read all phrases from the file
    print("Reading input file...")
    phrases = []
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue
            phrases.append((line_num, line))
    
    print(f"Found {len(phrases)} phrases to translate\n")
    
    # Process phrases in parallel
    def process_phrase(item):
        line_num, phrase = item
        
        # Get translation
        translation = translate_to_ur_djudeo(phrase)
        
        # Create training format
        training_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "Translate between English and Ur Djudeo-Mahikanítakh."
                },
                {
                    "role": "user",
                    "content": f"Translate to Ur Djudeo-Mahikanítakh:\n{phrase}"
                },
                {
                    "role": "assistant",
                    "content": translation
                }
            ]
        }
        
        return line_num, training_data
    
    # Use ThreadPoolExecutor for parallel processing
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_line = {executor.submit(process_phrase, phrase): phrase[0] 
                          for phrase in phrases}
        
        # Process completed tasks with progress bar
        with tqdm(total=len(phrases), desc="Translating", unit="phrase") as pbar:
            for future in as_completed(future_to_line):
                try:
                    line_num, training_data = future.result()
                    results[line_num] = training_data
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
    input_file = "phrases.txt"
    output_file = "phrases_translated.jsonl"
    max_workers = 10  # Number of parallel threads
    
    print(f"Starting translation from {input_file} to {output_file}...")
    print(f"Using {max_workers} parallel threads")
    print("=" * 60)
    
    translate_phrases_file(input_file, output_file, max_workers=max_workers)
    
    print("=" * 60)
    print(f"Translation complete! Output saved to {output_file}")


if __name__ == "__main__":
    main()
