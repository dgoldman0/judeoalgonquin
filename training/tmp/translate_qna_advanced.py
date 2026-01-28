import json
import csv
import random
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from typing import List, Tuple
from rapidfuzz import distance
import re

# Initialize OpenAI client (uses OPENAI_API_KEY from environment)
client = OpenAI()

# Set random seed for reproducibility (optional, remove for true randomness)
random.seed(42)


def get_hebrew_baseline(text: str) -> str:
    """
    Get a standard Hebrew translation using a standard model as baseline.
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {"role": "system", "content": "You are an expert Hebrew translator."},
            {"role": "user", "content": f"Translate to Hebrew (use nikkud). Provide only the translation, no explanation:\n{text}"}
        ]
    )
    return response.choices[0].message.content


def calculate_distance_to_baseline(translation: str, baseline: str) -> float:
    """
    Calculate character-level distance between a translation and baseline.
    Uses Levenshtein distance to handle morphological mutations in the conlang.
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
    """
    response = client.chat.completions.create(
        model="ft:gpt-4.1-mini-2025-04-14:personal:ur-djudeo-mahikanitakh-2:D32J6g9b",
        messages=[
            {"role": "system", "content": "You are an expert in Ur Djudeo-Mahikanítakh."},
            {"role": "user", "content": f"Translate into Ur Djudeo-Mahikanítakh. Exclude any explanation, just give the final translation. If multiple options exist for the translation, give only one. If no known word is available, take a native Hebrew word and adjust its morphology to align more closely with Algonquin. All translations must be fully in Ur Djudeo-Mahikanítakh, except for specific proper nouns, symbols, etc. that generally would not get translated:\n{text}"}
        ],
        temperature=temperature,
        max_tokens=500
    )
    
    return response.choices[0].message.content


def get_best_translation(text: str, n_attempts: int = 5) -> Tuple[str, float]:
    """
    Generate multiple translation attempts and select the one closest to Hebrew baseline.
    
    Returns:
        Tuple of (best_translation, distance_to_baseline)
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
    
    return best_translation, best_distance


def process_qna_file(input_file: str, training_file: str, validation_file: str,
                     n_attempts: int = 5, max_workers: int = 4):
    """
    Process Q&A CSV file and create training and validation JSONL files.
    
    For each Q&A pair:
    - Translate both question and answer to conlang
    - Randomly assign English/conlang direction for training
    - Use opposite direction for validation
    """
    # Read CSV file
    print("Reading input file...")
    qna_pairs = []
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row_num, row in enumerate(reader, 1):
            qna_pairs.append((row_num, row['question'], row['answer']))
    
    print(f"Found {len(qna_pairs)} Q&A pairs to process\n")
    
    # Collect all distances for statistics
    all_distances = []
    
    # Process Q&A pairs
    def process_qna(item):
        row_num, question_en, answer_en = item
        
        # Get best translations for both question and answer
        question_conlang, q_dist = get_best_translation(question_en, n_attempts)
        answer_conlang, a_dist = get_best_translation(answer_en, n_attempts)
        
        # Randomly decide direction: True = English Q, Conlang A; False = Conlang Q, English A
        english_question = random.choice([True, False])
        
        if english_question:
            # Training: English question -> Conlang answer
            training_data = {
                "messages": [
                    {"role": "system", "content": "The user is writing in English. Respond in Ur Djudeo-Mahikanítakh."},
                    {"role": "user", "content": question_en},
                    {"role": "assistant", "content": answer_conlang}
                ]
            }
            # Validation: Conlang question -> English answer
            validation_data = {
                "messages": [
                    {"role": "system", "content": "The user is writing in Ur Djudeo-Mahikanítakh. Respond in English."},
                    {"role": "user", "content": question_conlang},
                    {"role": "assistant", "content": answer_en}
                ]
            }
        else:
            # Training: Conlang question -> English answer
            training_data = {
                "messages": [
                    {"role": "system", "content": "The user is writing in Ur Djudeo-Mahikanítakh. Respond in English."},
                    {"role": "user", "content": question_conlang},
                    {"role": "assistant", "content": answer_en}
                ]
            }
            # Validation: English question -> Conlang answer
            validation_data = {
                "messages": [
                    {"role": "system", "content": "The user is writing in English. Respond in Ur Djudeo-Mahikanítakh."},
                    {"role": "user", "content": question_en},
                    {"role": "assistant", "content": answer_conlang}
                ]
            }
        
        return row_num, training_data, validation_data, [q_dist, a_dist]
    
    # Use ThreadPoolExecutor for parallel processing
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_row = {executor.submit(process_qna, pair): pair[0] 
                         for pair in qna_pairs}
        
        # Process completed tasks with progress bar
        with tqdm(total=len(qna_pairs), desc="Processing Q&A", unit="pair") as pbar:
            for future in as_completed(future_to_row):
                try:
                    row_num, training_data, validation_data, distances = future.result()
                    results[row_num] = (training_data, validation_data)
                    all_distances.extend(distances)
                    pbar.update(1)
                except Exception as e:
                    row_num = future_to_row[future]
                    print(f"\nError processing row {row_num}: {e}")
                    pbar.update(1)
    
    # Write results in order
    print("\nWriting output files...")
    with open(training_file, 'w', encoding='utf-8') as train_out, \
         open(validation_file, 'w', encoding='utf-8') as val_out:
        for row_num in sorted(results.keys()):
            training_data, validation_data = results[row_num]
            train_out.write(json.dumps(training_data, ensure_ascii=False) + '\n')
            val_out.write(json.dumps(validation_data, ensure_ascii=False) + '\n')
    
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
    input_file = "qna.csv"
    training_file = "qna_training.jsonl"
    validation_file = "qna_validation.jsonl"
    n_attempts = 5  # Number of translation attempts per text
    max_workers = 25  # Number of parallel threads
    
    print(f"Starting Q&A processing from {input_file}...")
    print(f"Training output: {training_file}")
    print(f"Validation output: {validation_file}")
    print(f"Using {n_attempts} attempts per translation with {max_workers} parallel threads")
    print("=" * 60)
    
    process_qna_file(input_file, training_file, validation_file, n_attempts, max_workers)
    
    print("=" * 60)
    print(f"Processing complete!")
    print(f"Training data saved to {training_file}")
    print(f"Validation data saved to {validation_file}")


if __name__ == "__main__":
    main()
