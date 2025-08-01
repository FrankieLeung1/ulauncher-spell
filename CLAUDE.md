# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Ulauncher extension called "Spell" that provides spelling assistance and word lookup functionality. It's a Python-based extension that integrates with the Ulauncher application launcher to help users find and spell words from multiple language vocabularies.

## Architecture

### Core Components

- **main.py**: Single-file architecture containing all extension logic
  - `OneDictExtension`: Main extension class that inherits from Ulauncher's Extension
  - `Word`: Simple data class representing a word and its vocabulary
  - `CustomSortedList`: Custom sorted list for fuzzy search results
  - Event listeners for handling keyword queries, preferences, and item selection

### Key Classes and Functions

- `load_words(vocabularies)`: Loads word lists from vocabulary files in ISO 8859-1 encoding
- `KeywordQueryEventListener`: Handles user queries and returns matching words
- `PreferencesEventListener`/`PreferencesUpdateEventListener`: Manage extension preferences
- `ItemEnterEventListener`: Handles word selection actions

### Vocabulary System

- Word lists stored in `vocabularies/` directory as plain text files (one word per line)
- Supported languages: deutsch, english, english_uk, espanol, francais, italiano, nederlands, norsk, swiss
- Files use ISO 8859-1 encoding
- Default active vocabularies: english_uk, english

### Search Methods

- **SymSpell matching**: Ultra-fast spell correction using Symmetric Delete algorithm (3000x faster than fuzzy)
- **Fuzzy matching**: Uses RapidFuzz with smart filtering for balanced speed/accuracy
- **Regex matching**: Simple prefix matching using regex for fastest prefix searches
- Results limited to 9 items for UI performance

### Performance Characteristics

- **SymSpell**: 0.02-0.20ms response times, one-time 4s setup cost, best for typo correction
- **Fuzzy**: 60-90ms response times, excellent for partial matches and flexibility  
- **Regex**: 50-70ms response times, best for prefix-based exact matching

## Development Commands

### Running in Development Mode

1. Start Ulauncher in development mode:
   ```bash
   ulauncher --no-extensions --dev -v
   ```

2. Run the extension directly (in separate terminal):
   ```bash
   VERBOSE=1 ULAUNCHER_WS_API=ws://127.0.0.1:5054/ulauncher-1dictionary PYTHONPATH=$HOME/src/Ulauncher /usr/bin/python3 $HOME/.local/share/ulauncher/extensions/com.github.lohenyumnam.spell/main.py
   ```

### Testing Vocabulary Files

Word list files should contain one word per line and use ISO 8859-1 encoding. Test loading with:
```python
python3 -c "
import main
words = main.load_words(['english'])
print(f'Loaded {len(words)} words')
"
```

## Configuration

Extension behavior is controlled through Ulauncher preferences:
- **keyword**: Trigger word (default: "spell")
- **matching**: Search method - "symspell", "fuzzy", or "regex" (default: "symspell")
- **vocabulary**: Comma-delimited list of active vocabularies (default: "english_uk, english")

### Matching Method Guide

- **symspell**: Ultra-fast spell correction, perfect for real-time typing, handles typos excellently
- **fuzzy**: Balanced approach, good for partial word matching and flexible searches
- **regex**: Fastest for exact prefix matching, no typo correction

## File Structure

- `main.py`: Complete extension implementation
- `manifest.json`: Ulauncher extension metadata and preferences schema
- `versions.json`: API version compatibility
- `vocabularies/`: Language-specific word list files
- `images/`: Extension icons and screenshots

## Key Implementation Details

- Uses Ulauncher API version ^2.0.0
- Word selection copies to clipboard via `CopyToClipboardAction`
- Query debounce set to 0.05 seconds for responsive typing
- SymSpell provides sub-millisecond search with one-time dictionary setup cost
- Smart filtering reduces search space by 97-99% for fuzzy/regex methods
- Result caching provides instant responses for repeated queries
- Extension name internally uses "OneDictExtension" (legacy from original "1Dictionary" name)

## Dependencies

- **symspellpy**: Ultra-fast spell correction library (pip install symspellpy)
- **rapidfuzz**: High-performance fuzzy string matching (pip install rapidfuzz)
- Both dependencies have graceful fallbacks if not installed

## Performance Optimizations Implemented

1. **SymSpell Integration**: 3000x faster than traditional fuzzy search
2. **Smart Filtering**: Length and first-character filtering reduces search space by 97-99%
3. **RapidFuzz**: 10-50x faster than original fuzzy matching
4. **Result Caching**: Instant responses for repeated queries (200-item LRU cache)
5. **Lazy Initialization**: SymSpell dictionary built only when needed