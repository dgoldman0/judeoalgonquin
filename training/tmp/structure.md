# JSONL Scaffold for Ur Djudeo-Mahikanítakh Training Data

**Language**: Ur Djudeo-Mahikanítakh (using "ur" to reference the prototype nature of the conlang). General details in `/judeo-algonquin.md`; most detailed info now lives in the four CSV files described below.

## Standard JSONL Format

Each line of training data follows this structure:
```jsonl
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]}
```

## System Prompts

**Forward-direction files** (prototype.jsonl, vocabulary.jsonl) use an English system prompt:
> You are an expert in Ur Djudeo-Mahikanítakh, a constructed fusion language blending Eastern Algonquian languages (primarily Munsee/Lenape) with Hebrew. You help users translate between English and Ur Djudeo-Mahikanítakh, and explain the linguistic principles behind each translation.

**Reverse-direction files** (reverse.jsonl, vocab-reverse.jsonl) use an Ur Djudeo-Mahikanítakh system prompt:
> אַתָּה מֻמְחֶה בְּאוּר דְּיוּדֵאוֹ-מָהִיקָאנִיטָאך, שְׂפַת מִזּוּג שֶׁל לְשׁוֹנוֹת אַלְגוֹנְקְוִין מִזְרָחִיּוֹת (בְּעִקָּר מוּנְסִי/לֶנַאפֶּה) וְעִבְרִית. נֶמִּינֵין עֶזְרָה לְתַרְגֵּם בֵּין אַנְגְּלִית לְאוּר דְּיוּדֵאוֹ-מָהִיקָאנִיטָאך, וּנֶוָאפּוּוֵין אֶת הָעִקְרוֹנוֹת הַלְּשׁוֹנִיִּים שֶׁמֵּאֲחוֹרֵי כָּל תַּרְגּוּם.

---

## 1. prototype.csv → prototype.jsonl

**Source CSV columns**: `english`, `conlang`, `explanation`

**Conversation structure** (4 messages per training example):

1. **User (English)**: "How would I approach translating '{english}' into Ur Djudeo-Mahikanítakh?"
2. **Assistant**: `{explanation}`
3. **User (English)**: "Now give me the full translation of '{english}' into Ur Djudeo-Mahikanítakh."
4. **Assistant**: `{conlang}`

---

## 2. reverse.csv → reverse.jsonl

**Source CSV columns**: `conlang`, `english`, `explanation_in_conlang`

**Conversation structure** (4 messages per training example):

1. **User (Ur Djudeo-Mahikanítakh)**: "אֵיךְ אֶתְרַגֵּם אֶת '{conlang}' לְאַנְגְּלִית?" *(How would I translate '{conlang}' into English?)*
2. **Assistant**: `{explanation_in_conlang}`
3. **User (Ur Djudeo-Mahikanítakh)**: "תֵּן לִי אֶת הַתַּרְגּוּם הַמָּלֵא לְאַנְגְּלִית." *(Give me the full translation into English.)*
4. **Assistant**: `{english}`

---

## 3. vocabulary.csv → vocabulary.jsonl

**Source CSV columns**: `english`, `conlang`, `etymology`

**Conversation structure** (4 messages per training example):

1. **User (English)**: "What is the Ur Djudeo-Mahikanítakh word for '{english}'?"
2. **Assistant**: `{conlang}`
3. **User (English)**: "Explain the etymology of '{conlang}'."
4. **Assistant**: `{etymology}`

---

## 4. vocab-reverse.csv → vocab-reverse.jsonl

**Source CSV columns**: `conlang`, `english`, `etymology_in_conlang`

**Conversation structure** (4 messages per training example):

1. **User (Ur Djudeo-Mahikanítakh)**: "מַה הַתַּרְגּוּם לְאַנְגְּלִית שֶׁל '{conlang}'?" *(What is the English translation of '{conlang}'?)*
2. **Assistant**: `{english}`
3. **User (Ur Djudeo-Mahikanítakh)**: "הַסְבֵּר אֶת הָאֶטִימוֹלוֹגְיָה שֶׁל '{conlang}'." *(Explain the etymology of '{conlang}'.)*
4. **Assistant**: `{etymology_in_conlang}`