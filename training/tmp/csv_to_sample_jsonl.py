import json

def convert_csv_to_jsonl(input_file, output_file):
    """
    Convert CSV with ||| delimiters to JSONL format.
    Format: system|||user1|||assistant1|||user2|||assistant2|||...
    """
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue
            
            # Split on the delimiter
            parts = line.split('|||')
            
            if len(parts) < 3:
                print(f"Line {line_num}: Skipping - not enough parts (need at least system, user, assistant)")
                continue
            
            # First part is always system message
            system_message = parts[0].strip()
            
            # Build conversation
            conversation = {
                "messages": [
                    {"role": "system", "content": system_message}
                ]
            }
            
            # Remaining parts alternate user/assistant
            for i in range(1, len(parts)):
                content = parts[i].strip()
                if i % 2 == 1:  # Odd indices are user messages
                    role = "user"
                else:  # Even indices are assistant messages
                    role = "assistant"
                
                conversation["messages"].append({
                    "role": role,
                    "content": content
                })
            
            # Write to JSONL
            outfile.write(json.dumps(conversation, ensure_ascii=False) + '\n')
            print(f"Line {line_num}: Processed {len(parts)} parts -> {len(conversation['messages'])} messages")
    
    print(f"\nConversion complete!")

def main():
    input_file = "sample.csv"
    output_file = "sample.jsonl"
    
    print(f"Converting {input_file} to {output_file}...")
    print("=" * 60)
    
    convert_csv_to_jsonl(input_file, output_file)
    
    print("=" * 60)
    print(f"Done! Output saved to {output_file}")

if __name__ == "__main__":
    main()
