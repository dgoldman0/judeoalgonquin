import json
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from typing import List, Tuple
from rapidfuzz import distance
import re

# Initialize OpenAI client (uses OPENAI_API_KEY from environment)
client = OpenAI()


def get_hebrew_baseline(text: str) -> str:
    """
    Get a standard Hebrew translation using a standard model as baseline.
    
    Args:
        text: English text to translate
        
    Returns:
        Hebrew translation
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {"role": "system", "content": "You are an expert Hebrew translator."},
            {"role": "user", "content": f"Translate to Hebrew. Provide only the translation, no explanation:\n{text}"}
        ]
    )
    return response.choices[0].message.content


def calculate_distance_to_baseline(translation: str, baseline: str) -> float:
    """
    Calculate character-level distance between a translation and baseline.
    Uses Levenshtein distance to handle morphological mutations in the conlang.
    Lower score means closer to baseline, accounting for character transformations.
    
    Args:
        translation: Translation to evaluate
        baseline: Baseline translation to compare against
        
    Returns:
        Normalized distance score from 0 to 1 (lower is better)
    """
    # Remove diacritics/nikkud for comparison to focus on root/structure similarity
    trans_clean = re.sub(r'[\u0591-\u05C7]', '', translation)
    base_clean = re.sub(r'[\u0591-\u05C7]', '', baseline)
    
    # Calculate Levenshtein distance (normalized by max length)
    lev_distance = distance.Levenshtein.distance(trans_clean, base_clean)
    max_len = max(len(trans_clean), len(base_clean))
    
    # Normalize to 0-1 range
    normalized_distance = lev_distance / max_len if max_len > 0 else 0
    
    return min(normalized_distance, 1.0)


def translate_to_ur_djudeo_with_temperature(text: str, temperature: float) -> str:
    """
    Translate English text to Ur Djudeo-Mahikanítakh using a specific temperature.
    
    Args:
        text: English text to translate
        temperature: Temperature for sampling diversity
        
    Returns:
        Translated text in Ur Djudeo-Mahikanítakh
    """
    response = client.chat.completions.create(
        model="ft:gpt-4.1-mini-2025-04-14:personal:ur-djudeo-mahikanitakh-2:D32J6g9b",
        messages=[
            {"role": "system", "content": "Translate between English and Ur Djudeo-Mahikanítakh."},
            {"role": "user", "content": f"Translate into Ur Djudeo-Mahikanítakh. Exclude any explanation, just give the final translation. If multiple options exist for the translation, give only one. If no known word is available, take a native Hebrew word and adjust its morphology to align more closely with Algonquin. All translations must be fully in Ur Djudeo-Mahikanítakh, except for specific proper nouns, symbols, etc. that generally would not get translated:\n{text}"}
        ],
        temperature=temperature,
        max_tokens=500
    )
    
    return response.choices[0].message.content


def get_best_translation(text: str, n_attempts: int = 5) -> Tuple[str, float, List[Tuple[str, float]]]:
    """
    Generate multiple translation attempts and select the one closest to Hebrew baseline using Levenshtein distance.
    
    Args:
        text: English text to translate
        n_attempts: Number of translation attempts (default: 5)
        
    Returns:
        Tuple of (best_translation, distance_to_baseline, list_of_all_attempts_with_distances)
    """
    # Get Hebrew baseline
    baseline = get_hebrew_baseline(text)
    
    # Generate multiple attempts with varying temperatures
    attempts = []
    temperatures = np.linspace(0.9, 1.1, n_attempts)
    
    for temp in temperatures:
        translation = translate_to_ur_djudeo_with_temperature(text, temp)
        attempts.append(translation)
    
    # Calculate distance to baseline for each translation
    attempt_scores = []
    for translation in attempts:
        dist = calculate_distance_to_baseline(translation, baseline)
        attempt_scores.append((translation, dist))
    
    # Select the translation closest to baseline (lowest distance)
    best_translation, best_distance = min(attempt_scores, key=lambda x: x[1])
    
    return best_translation, best_distance, attempt_scores


def translate_jsonl_file_advanced(input_file: str, output_file: str, 
                                  n_attempts: int = 5, max_workers: int = 4):
    """
    Translate all user and assistant messages in a JSONL file using advanced selection,
    leaving system messages in English.
    
    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSONL file
        n_attempts: Number of translation attempts per message
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
    
    # Collect all distances for statistics
    all_distances = []
    
    # Process conversations in parallel
    def process_conversation(item):
        line_num, data = item
        translated_data = {"messages": []}
        conversation_distances = []
        
        # Process each message in the conversation
        for message in data["messages"]:
            role = message["role"]
            content = message["content"]
            
            # Only translate user and assistant messages, keep system in English
            if role in ["user", "assistant"]:
                best_translation, dist, _ = get_best_translation(content, n_attempts)
                conversation_distances.append(dist)
                translated_data["messages"].append({
                    "role": role,
                    "content": best_translation
                })
            else:  # system message
                # Append the language assumption note to system messages
                system_content = content + " The user is assumed to be writing in Ur Djudeo-Mahikanítakh unless it is otherwise clear."
                translated_data["messages"].append({
                    "role": role,
                    "content": system_content
                })
        
        return line_num, translated_data, conversation_distances
    
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
                    line_num, translated_data, distances = future.result()
                    results[line_num] = translated_data
                    all_distances.extend(distances)
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
    
    # Print statistics
    if all_distances:
        print("\n" + "=" * 60)
        print("Translation Statistics:")
        print(f"Mean distance to baseline: {np.mean(all_distances):.4f}")
        print(f"Median distance to baseline: {np.median(all_distances):.4f}")
        print(f"Min distance to baseline: {np.min(all_distances):.4f}")
        print(f"Max distance to baseline: {np.max(all_distances):.4f}")
        print(f"Std dev: {np.std(all_distances):.4f}")
        print("(Lower distances indicate translations closer to Hebrew baseline)")
        print("=" * 60)


def main():
    input_file = "sample_shortlist.jsonl"
    output_file = "sample_translated_advanced_shortlist.jsonl"
    n_attempts = 5  # Number of translation attempts per message
    max_workers = 25  # Number of parallel threads
    
    print(f"Starting advanced translation from {input_file} to {output_file}...")
    print(f"Using {n_attempts} attempts per message with {max_workers} parallel threads")
    print("=" * 60)
    
    translate_jsonl_file_advanced(input_file, output_file, n_attempts, max_workers)
    
    print("=" * 60)
    print(f"Advanced translation complete! Output saved to {output_file}")


if __name__ == "__main__":
    main()
