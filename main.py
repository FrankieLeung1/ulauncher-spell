import re
import os
import json
import glob
import logging
import time
from time import sleep
from functools import lru_cache
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.search.SortedList import SortedList
from ulauncher.utils.SortedCollection import SortedCollection
from ulauncher.api.client.Extension import Extension, PreferencesEventListener
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import (
    KeywordQueryEvent,
    ItemEnterEvent,
    PreferencesEvent,
    PreferencesUpdateEvent,
)

from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction

from ulauncher.utils.fuzzy_search import get_score

try:
    from rapidfuzz import process as rapidfuzz_process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

try:
    from symspellpy import SymSpell, Verbosity
    SYMSPELL_AVAILABLE = True
except ImportError:
    SYMSPELL_AVAILABLE = False


logging.basicConfig()
logger = logging.getLogger(__name__)


DEFAULT_VOCABURARIES = [
    "english",
    "english_uk",
]
DEFAULT_DICTIONARY = (
    "https://translate.google.com/#view=home&op=translate&sl=auto&tl=en&text=%s"
)


class Word:
    def __init__(self, word, vocabulary):
        self._word = word
        self._vocabulary = vocabulary

    def __repr__(self):
        return "{}/{}".format(self._word, self._vocabulary)

    def get_search_name(self):
        return self._word


def load_words(vocabularies):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    words = []
    for vocabulary in vocabularies:
        filename = os.path.join(base_dir, "vocabularies", "{}.txt".format(vocabulary))
        with open(filename, "r", encoding="ISO 8859-1") as dict_file:
            words += [Word(word.strip(), vocabulary) for word in dict_file.readlines()]
    return words


def filter_words_by_length(words, query, length_tolerance=2):
    """Filter words by length to reduce search space before fuzzy matching."""
    if not query:
        return words
    
    query_len = len(query)
    min_len = max(1, query_len - length_tolerance)
    max_len = query_len + length_tolerance
    
    return [w for w in words if w.get_search_name() and min_len <= len(w.get_search_name()) <= max_len]


def filter_words_by_first_char(words, query):
    """Filter words by first character similarity to reduce search space."""
    if not query or len(query) < 1:
        return words
    
    query_first = query[0].lower()
    return [w for w in words if w.get_search_name() and w.get_search_name()[0].lower() == query_first]


@lru_cache(maxsize=200)
def cached_search_results(query, matching_method, vocabulary_hash):
    """Cache search results for frequently queried terms."""
    return None  # Cache key only, actual implementation in search functions


def rapidfuzz_search(words, query, limit=9, score_cutoff=65):
    """Use RapidFuzz for fast fuzzy matching."""
    if not RAPIDFUZZ_AVAILABLE or not words:
        return []
    
    # Extract word strings for RapidFuzz matching
    word_strings = [w.get_search_name() for w in words]
    
    # Use RapidFuzz to get matches with scores
    matches = rapidfuzz_process.extract(
        query, 
        word_strings, 
        limit=limit, 
        score_cutoff=score_cutoff
    )
    
    # Convert back to Word objects by finding original words
    word_dict = {w.get_search_name(): w for w in words}
    result_words = []
    
    for match_string, score, index in matches:
        if match_string in word_dict:
            result_words.append(word_dict[match_string])
    
    return result_words


class SymSpellMatcher:
    """SymSpell-based ultra-fast spell checker."""
    
    def __init__(self):
        self.symspell = None
        self.word_dict = {}
        self.is_initialized = False
    
    def initialize(self, words):
        """Initialize SymSpell dictionary from word list."""
        if not SYMSPELL_AVAILABLE:
            logger.warning("SymSpell not available, falling back to other methods")
            return False
        
        logger.info("Initializing SymSpell dictionary...")
        start_time = time.time()
        
        # Create SymSpell instance with optimized parameters
        self.symspell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        self.word_dict = {}
        
        # Build dictionary and word mapping
        word_count = 0
        for word_obj in words:
            word_str = word_obj.get_search_name()
            if word_str and len(word_str.strip()) > 0:  # Skip empty words
                # Add to SymSpell dictionary (frequency = 1 for all words)
                self.symspell.create_dictionary_entry(word_str, 1)
                
                # Map word string to original Word object
                if word_str not in self.word_dict:
                    self.word_dict[word_str] = []
                self.word_dict[word_str].append(word_obj)
                word_count += 1
        
        init_time = time.time() - start_time
        logger.info(f"SymSpell dictionary initialized with {word_count} words in {init_time:.2f}s")
        
        self.is_initialized = True
        return True
    
    def search(self, query, max_edit_distance=2, limit=9):
        """Search using SymSpell for ultra-fast spell checking."""
        if not self.is_initialized or not query:
            return []
        
        # Get suggestions from SymSpell
        suggestions = self.symspell.lookup(
            query, 
            Verbosity.CLOSEST, 
            max_edit_distance=max_edit_distance
        )
        
        # Convert back to Word objects
        result_words = []
        seen_words = set()
        
        for suggestion in suggestions:
            word_str = suggestion.term
            if word_str in self.word_dict and word_str not in seen_words:
                # Add first Word object for this string (could have multiple from different vocabs)
                result_words.append(self.word_dict[word_str][0])
                seen_words.add(word_str)
                
                if len(result_words) >= limit:
                    break
        
        return result_words


class OneDictExtension(Extension):
    def __init__(self):
        super(OneDictExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

        self.word_list = []
        self.search_cache = {}
        self.symspell_matcher = SymSpellMatcher()

    def run(self):
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self._client.connect()


class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        extension.preferences.update(event.preferences)

        vocabularies = [
            voc.rstrip().lstrip().lower()
            for voc in extension.preferences["vocabulary"].split(",")
        ]
        extension.word_list = load_words(vocabularies)
        
        # Initialize SymSpell if using symspell matching method
        if extension.preferences.get("matching") == "symspell":
            extension.symspell_matcher.initialize(extension.word_list)


class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        extension.preferences[event.id] = event.new_value

        vocabularies = [
            voc.rstrip().lstrip()
            for voc in extension.preferences["vocabulary"].split(",")
        ]
        extension.word_list = load_words(vocabularies)
        
        # Clear cache when vocabularies change
        extension.search_cache.clear()
        
        # Re-initialize SymSpell if using symspell matching method
        if extension.preferences.get("matching") == "symspell":
            extension.symspell_matcher.initialize(extension.word_list)


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        items = [] 
        query = event.get_argument() 
        if query:
            # Create cache key based on query, matching method, and active vocabularies
            cache_key = (query, extension.preferences["matching"], extension.preferences["vocabulary"])
            
            # Check cache first
            if cache_key in extension.search_cache:
                result_list = extension.search_cache[cache_key]
            else:
                # Perform search and cache results
                dictionaries = get_dictionaries(extension.preferences)

                if extension.preferences["matching"] == "regex":
                    # Apply first-character filtering for regex search
                    filtered_words = filter_words_by_first_char(extension.word_list, query)
                    result_list = [
                        w
                        for w in filtered_words
                        if re.search(r"^{}".format(query), w.get_search_name())
                    ]
                elif extension.preferences["matching"] == "symspell":
                    # Use SymSpell for ultra-fast spell checking
                    result_list = extension.symspell_matcher.search(query, max_edit_distance=2, limit=9)
                else:
                    # Apply both length and first-character filtering for fuzzy search
                    filtered_words = filter_words_by_length(extension.word_list, query)
                    filtered_words = filter_words_by_first_char(filtered_words, query)
                    
                    # Use RapidFuzz if available, otherwise fall back to original implementation
                    if RAPIDFUZZ_AVAILABLE:
                        result_list = rapidfuzz_search(filtered_words, query, limit=9, score_cutoff=65)
                    else:
                        result_list = CustomSortedList(query, min_score=65)
                        result_list.extend(filtered_words)
                
                # Cache results (limit cache size to prevent memory bloat)
                if len(extension.search_cache) >= 200:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(extension.search_cache))
                    del extension.search_cache[oldest_key]
                extension.search_cache[cache_key] = result_list

            for result in result_list[:9]:
                word, language = str(result).split("/")

                items.append(
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name=word,
                        description="Language: {}".format(language),
                        on_enter=CopyToClipboardAction(word),
                    )
                )

        else:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="Type in the word...",
                    description="",
                )
            )

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        return RenderResultListAction(
            [
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=data["new_name"],
                    on_enter=HideWindowAction(),
                )
            ]
        )


class CustomSortedList(SortedList):
    def __init__(self, query, min_score):
        super(CustomSortedList, self).__init__(query, min_score, limit=9)
        self._items = SortedCollection(
            key=lambda i: (i.score, abs(len(self._query) - len(i.get_search_name())))
        )


def get_dictionaries(preferences):
    dictionaries = {}
    for voc in DEFAULT_VOCABURARIES:
        dictionaries[voc] = preferences.get(voc, DEFAULT_DICTIONARY)
    return dictionaries


if __name__ == "__main__":
    OneDictExtension().run()
