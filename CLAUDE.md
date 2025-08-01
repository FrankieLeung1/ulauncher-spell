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

- **Fuzzy matching**: Uses Ulauncher's built-in fuzzy search with configurable minimum score (65)
- **Regex matching**: Simple prefix matching using regex for faster performance
- Results limited to 9 items for UI performance

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
- **matching**: Search method - "fuzzy" or "regex" (default: "fuzzy")
- **vocabulary**: Comma-delimited list of active vocabularies (default: "english_uk, english")

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
- Fuzzy search scoring considers both relevance and word length similarity
- Extension name internally uses "OneDictExtension" (legacy from original "1Dictionary" name)