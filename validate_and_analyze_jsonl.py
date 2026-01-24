#!/usr/bin/env python3
"""
JSONL Fine-Tune File Validator and Token Counter

Validates OpenAI-style fine-tune JSONL files and provides:
- Format validation
- Token count analysis (system, user, assistant)
- Percentage breakdown
- Additional useful statistics
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import re

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class TokenCounter:
    """Count tokens using tiktoken (OpenAI's tokenizer)"""
    
    _encoder = None
    
    @classmethod
    def _get_encoder(cls):
        """Lazily initialize tiktoken encoder for GPT-4"""
        if cls._encoder is None and TIKTOKEN_AVAILABLE:
            try:
                cls._encoder = tiktoken.encoding_for_model("gpt-4")
            except Exception:
                # Fallback to cl100k_base encoding if gpt-4 not available
                try:
                    cls._encoder = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    pass
        return cls._encoder
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Count tokens using tiktoken (accurate OpenAI tokenization).
        Falls back to character-based heuristic if tiktoken unavailable.
        """
        if not text:
            return 0
        
        encoder = TokenCounter._get_encoder()
        
        if encoder is not None:
            try:
                return len(encoder.encode(text))
            except Exception:
                pass
        
        # Fallback: character-based approximation
        # (1 token ≈ 4 characters for English, adjusted for other scripts)
        token_count = len(text) // 4
        token_count += len(re.findall(r'[.,!?;:\-]', text)) // 2
        return max(1, token_count)


class JSONLValidator:
    """Validates and analyzes OpenAI-style fine-tune JSONL files"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.messages_list: List[List[Dict]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.token_stats = defaultdict(int)
        self.role_counts = defaultdict(int)
        
    def load_file(self) -> bool:
        """Load and parse JSONL file"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        self.messages_list.append(obj)
                    except json.JSONDecodeError as e:
                        self.errors.append(f"Line {line_num}: Invalid JSON - {e}")
                        return False
            return True
        except FileNotFoundError:
            self.errors.append(f"File not found: {self.filepath}")
            return False
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return False
    
    def validate_structure(self) -> bool:
        """Validate JSONL structure against OpenAI fine-tune format"""
        valid = True
        
        if not self.messages_list:
            self.errors.append("File is empty")
            return False
        
        for idx, item in enumerate(self.messages_list):
            # Check for required 'messages' key
            if 'messages' not in item:
                self.errors.append(f"Entry {idx}: Missing 'messages' key")
                valid = False
                continue
            
            messages = item['messages']
            
            # Validate messages is a list
            if not isinstance(messages, list):
                self.errors.append(f"Entry {idx}: 'messages' must be a list")
                valid = False
                continue
            
            if len(messages) == 0:
                self.errors.append(f"Entry {idx}: 'messages' is empty")
                valid = False
                continue
            
            # Validate each message object
            for msg_idx, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    self.errors.append(f"Entry {idx}, message {msg_idx}: Message must be a dict")
                    valid = False
                    continue
                
                if 'role' not in msg:
                    self.errors.append(f"Entry {idx}, message {msg_idx}: Missing 'role' field")
                    valid = False
                    continue
                
                if 'content' not in msg:
                    self.errors.append(f"Entry {idx}, message {msg_idx}: Missing 'content' field")
                    valid = False
                    continue
                
                role = msg['role']
                content = msg['content']
                
                # Validate role
                if role not in ['system', 'user', 'assistant']:
                    self.warnings.append(f"Entry {idx}, message {msg_idx}: Unknown role '{role}'")
                
                # Validate content is string
                if not isinstance(content, str):
                    self.errors.append(f"Entry {idx}, message {msg_idx}: 'content' must be a string")
                    valid = False
                    continue
                
                if len(content) == 0:
                    self.warnings.append(f"Entry {idx}, message {msg_idx}: Empty content in {role} message")
            
            # Check conversation pattern
            if len(messages) > 0:
                roles = [msg['role'] for msg in messages]
                
                # Should ideally end with 'assistant'
                if roles[-1] != 'assistant':
                    self.warnings.append(f"Entry {idx}: Conversation should end with 'assistant' role, ends with '{roles[-1]}'")
        
        return valid
    
    def analyze_tokens(self):
        """Analyze token distribution across roles"""
        for entry in self.messages_list:
            messages = entry.get('messages', [])
            for msg in messages:
                role = msg.get('role')
                content = msg.get('content', '')
                tokens = TokenCounter.count_tokens(content)
                
                self.token_stats[role] += tokens
                self.token_stats['total'] += tokens
                self.role_counts[role] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive statistics"""
        self.analyze_tokens()
        
        total_tokens = self.token_stats.get('total', 0)
        
        # Calculate max tokens in any single example
        max_tokens_in_example = 0
        if self.messages_list:
            for entry in self.messages_list:
                example_tokens = 0
                for msg in entry.get('messages', []):
                    content = msg.get('content', '')
                    example_tokens += TokenCounter.count_tokens(content)
                max_tokens_in_example = max(max_tokens_in_example, example_tokens)
        
        stats = {
            'file': str(self.filepath),
            'valid': len(self.errors) == 0,
            'num_entries': len(self.messages_list),
            'num_errors': len(self.errors),
            'num_warnings': len(self.warnings),
            'tokens': {
                'system': self.token_stats.get('system', 0),
                'user': self.token_stats.get('user', 0),
                'assistant': self.token_stats.get('assistant', 0),
                'total': total_tokens,
                'max_in_example': max_tokens_in_example,
            },
            'percentages': {},
            'message_counts': dict(self.role_counts),
            'avg_tokens_per_entry': total_tokens // len(self.messages_list) if self.messages_list else 0,
        }
        
        # Calculate percentages
        if total_tokens > 0:
            for role in ['system', 'user', 'assistant']:
                pct = (self.token_stats.get(role, 0) / total_tokens) * 100
                stats['percentages'][role] = round(pct, 2)
        
        return stats
    
    def print_report(self):
        """Print validation and analysis report"""
        stats = self.get_statistics()
        
        print("\n" + "="*70)
        print("JSONL FINE-TUNE FILE VALIDATION REPORT")
        print("="*70)
        if TIKTOKEN_AVAILABLE:
            print("[Using tiktoken (OpenAI GPT-4 tokenizer) for accurate token counts]")
        else:
            print("[⚠ Using character-based approximation - tiktoken not available]")
        print(f"\nFile: {stats['file']}")
        print(f"Valid: {'✓ YES' if stats['valid'] else '✗ NO'}")
        print(f"Total Entries: {stats['num_entries']}")
        
        if stats['num_errors'] > 0:
            print(f"\n⚠ ERRORS: {stats['num_errors']}")
            for error in self.errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
        
        if stats['num_warnings'] > 0:
            print(f"\n⚠ WARNINGS: {stats['num_warnings']}")
            for warning in self.warnings[:5]:  # Show first 5
                print(f"  - {warning}")
            if len(self.warnings) > 5:
                print(f"  ... and {len(self.warnings) - 5} more warnings")
        
        print("\n" + "-"*70)
        print("TOKEN ANALYSIS")
        print("-"*70)
        
        tokens = stats['tokens']
        percentages = stats['percentages']
        
        print(f"\nTotal Tokens: {tokens['total']}")
        print(f"Maximum Tokens in Any Example: {tokens['max_in_example']}")
        print(f"\nBreakdown by Role:")
        print(f"  System:    {tokens['system']:6d} tokens ({percentages.get('system', 0):5.2f}%)")
        print(f"  User:      {tokens['user']:6d} tokens ({percentages.get('user', 0):5.2f}%)")
        print(f"  Assistant: {tokens['assistant']:6d} tokens ({percentages.get('assistant', 0):5.2f}%)")
        
        print(f"\nMessage Counts by Role:")
        for role in ['system', 'user', 'assistant']:
            count = stats['message_counts'].get(role, 0)
            print(f"  {role.capitalize():10s}: {count} messages")
        
        print(f"\nAverage Tokens per Entry: {stats['avg_tokens_per_entry']}")
        
        print("\n" + "-"*70)
        print("ADDITIONAL STATISTICS")
        print("-"*70)
        
        if self.messages_list:
            message_lengths = []
            for entry in self.messages_list:
                messages = entry.get('messages', [])
                message_lengths.append(len(messages))
            
            avg_msgs = sum(message_lengths) / len(message_lengths)
            min_msgs = min(message_lengths)
            max_msgs = max(message_lengths)
            
            print(f"\nMessages per Entry:")
            print(f"  Average: {avg_msgs:.2f}")
            print(f"  Minimum: {min_msgs}")
            print(f"  Maximum: {max_msgs}")
        
        print("\n" + "="*70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_and_analyze_jsonl.py <file.jsonl>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    validator = JSONLValidator(filepath)
    
    if not validator.load_file():
        print("\n❌ Failed to load file:")
        for error in validator.errors:
            print(f"  - {error}")
        sys.exit(1)
    
    if not validator.validate_structure():
        print("\n❌ File validation failed:")
        for error in validator.errors:
            print(f"  - {error}")
        sys.exit(1)
    
    validator.print_report()
    
    if validator.errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
