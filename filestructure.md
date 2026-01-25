# File system structure

essense.md - contains sample essense statements and their translations. Essense statements come from the Astravus Collection series and may be valuable in showcasing the narrative expression power of the language.

# Main folder

judeo-algonquin.md - a general overview of Djudeo-Mahikanítakh
words.md - a basic listing of Algonquin vocabulary


## training/

This folder includes training data. It has a tmp file for scripts and raw data.

alignment.jsonl - does not exist yet but will contain pairs of attempted translations for user prompt and assistant completions which should be complex enough that they should require a decent amount of "understanding" 

validation.jsonl - doesn't exist yet but should: the validation structure should be as follows: we'll take either a subset of above or a new set like it only the system prompt will instruct to respond in English and the assistant response will be the original English completion rather than the attempted translation. If translation is working well, the system should be able to understand the user's request and respond in English appropriately