import json
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from typing import List, Tuple
from difflib import SequenceMatcher
import re

# Initialize OpenAI client (uses OPENAI_API_KEY from environment)
client = OpenAI()

def tokenize_conlang(text: str) -> List[str]:
    """
    Tokenize text for a constructed language at character and morpheme boundaries.
    Splits on common morpheme patterns and special characters.
    
    Args:
        text: Text to tokenize
        
    Returns:
        List of tokens
    """
    # Remove extra whitespace
    text = text.strip()
    
    # Split on spaces and hyphens (likely morpheme boundaries)
    tokens = re.split(r'[\s\-]+', text)
    
    # Further split longer tokens on capital letters (CamelCase patterns)
    final_tokens = []
    for token in tokens:
        if len(token) > 3:
            # Split on transitions to uppercase (e.g., "djudeoMahikan" -> ["djudeo", "Mahikan"])
            sub_tokens = re.findall('[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\W|$)', token)
            final_tokens.extend(sub_tokens if sub_tokens else [token])
        else:
            final_tokens.append(token)
    
    return final_tokens


def calculate_token_similarity(translation1: str, translation2: str) -> float:
    """
    Calculate similarity between two translations using token-level comparison.
    Uses sequence matching on tokenized forms.
    
    Args:
        translation1: First translation
        translation2: Second translation
        
    Returns:
        Similarity score from 0 to 1 (higher is more similar)
    """
    tokens1 = tokenize_conlang(translation1)
    tokens2 = tokenize_conlang(translation2)
    
    # Use SequenceMatcher to find matching tokens
    matcher = SequenceMatcher(None, tokens1, tokens2)
    similarity = matcher.ratio()
    
    return similarity


def calculate_translation_consistency(translation: str, all_translations: List[str]) -> float:
    """
    Calculate how consistent a translation is with all other attempts.
    Higher score means more similar to other attempts (more stable/typical).
    
    Args:
        translation: Translation to evaluate
        all_translations: List of all translation attempts
        
    Returns:
        Average similarity score to all other translations
    """
    similarities = []
    for other in all_translations:
        if other != translation:
            similarity = calculate_token_similarity(translation, other)
            similarities.append(similarity)
    
    return float(np.mean(similarities)) if similarities else 0.0


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
            {"role": "user", "content": f"Translate to Hebrew (use nikkud). Provide only the translation, no explanation:\n{text}"}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content


def calculate_distance_to_baseline(translation: str, baseline: str) -> float:
    """
    Calculate token-level distance between a translation and baseline.
    Lower score means closer to baseline.
    
    Args:
        translation: Translation to evaluate
        baseline: Baseline translation to compare against
        
    Returns:
        Distance score (lower is better, 0 = identical)
    """
    similarity = calculate_token_similarity(translation, baseline)
    distance = 1.0 - similarity
    return distance


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
            {"role": "system", "content": "You are an expert in Ur Djudeo-Mahikanítakh."},
            {"role": "user", "content": f"Translate into Ur Djudeo-Mahikanítakh. Exclude any explanation, just give the final translation. If multiple options exist for the translation, give only one. If no known word is available, take a native Hebrew word and adjust its morphology to align more closely with Algonquin. All translations must be fully in Ur Djudeo-Mahikanítakh, except for specific proper nouns, symbols, etc. that generally would not get translated:\n{text}"}
        ],
        temperature=temperature
    )
    
    return response.choices[0].message.content





def get_best_translation(text: str, n_attempts: int = 5) -> Tuple[str, float, List[Tuple[str, float]]]:
    """
    Generate multiple translation attempts and select the one closest to Hebrew baseline using token-level comparison.
    
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
    temperatures = np.linspace(0.5, 2.0, n_attempts)
    
    for temp in temperatures:
        translation = translate_to_ur_djudeo_with_temperature(text, temp)
        attempts.append(translation)
    
    # Calculate distance to baseline for each translation
    attempt_scores = []
    for translation in attempts:
        distance = calculate_distance_to_baseline(translation, baseline)
        attempt_scores.append((translation, distance))
    
    # Select the translation closest to baseline (lowest distance)
    best_translation, best_distance = min(attempt_scores, key=lambda x: x[1])
    
    return best_translation, best_distance, attempt_scores


def translate_phrases_file_advanced(input_file: str, output_file: str, 
                                   n_attempts: int = 5, max_workers: int = 4):
    """
    Read phrases from a text file and create JSONL training data with advanced translation selection.
    
    Args:
        input_file: Path to input text file (one phrase per line)
        output_file: Path to output JSONL file
        n_attempts: Number of translation attempts per phrase
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
    def process_phrase(item, include_metadata: bool = False):
        line_num, phrase = item
        
        # Get best translation from multiple attempts
        best_translation, distance_score, all_attempts = get_best_translation(phrase, n_attempts)
        
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
                    "content": best_translation
                }
            ]
        }
        if include_metadata:
            training_data["metadata"] = {
                "distance_to_baseline": distance_score,
                "n_attempts": n_attempts,
                "all_attempts": [
                    {"translation": t, "distance": d} for t, d in all_attempts
                ]
            }
        
        return line_num, training_data, distance_score
    
    # Use ThreadPoolExecutor for parallel processing
    results = {}
    scores = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_line = {executor.submit(process_phrase, phrase): phrase[0] 
                          for phrase in phrases}
        
        # Process completed tasks with progress bar
        with tqdm(total=len(phrases), desc="Translating", unit="phrase") as pbar:
            for future in as_completed(future_to_line):
                try:
                    line_num, training_data, score = future.result()
                    results[line_num] = training_data
                    scores.append(score)
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
    if scores:
        print("\n" + "=" * 60)
        print("Translation Statistics:")
        print(f"Mean distance to baseline: {np.mean(scores):.4f}")
        print(f"Median distance to baseline: {np.median(scores):.4f}")
        print(f"Min distance to baseline: {np.min(scores):.4f}")
        print(f"Max distance to baseline: {np.max(scores):.4f}")
        print(f"Std dev: {np.std(scores):.4f}")
        print("(Lower distances indicate translations closer to Hebrew baseline)")
        print("=" * 60)


def main():
    input_file = "phrases.txt"
    output_file = "phrases_translated_advanced.jsonl"
    n_attempts = 5  # Number of translation attempts per phrase
    max_workers = 50  # Number of parallel threads
    
    print(f"Starting advanced translation from {input_file} to {output_file}...")
    print(f"Using {n_attempts} attempts per phrase with {max_workers} parallel threads")
    print("=" * 60)
    
    translate_phrases_file_advanced(input_file, output_file, n_attempts, max_workers)
    
    print(f"Advanced translation complete! Output saved to {output_file}")


if __name__ == "__main__":
    main()
