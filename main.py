import re
import os
import logging
import time
from functools import lru_cache

from ulauncher.api import Extension, ExtensionResult
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

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


logger = logging.getLogger(__name__)


DEFAULT_VOCABURARIES = [
    "english",
    "english_uk",
]


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


def fuzzy_search_fallback(words, query, limit=9, min_score=65):
    """Fallback fuzzy search using Ulauncher's built-in fuzzy search."""
    from ulauncher.utils.fuzzy_search import get_score

    scored = []
    for w in words:
        name = w.get_search_name()
        if name:
            score = get_score(query, name)
            if score >= min_score:
                scored.append((score, w))

    scored.sort(key=lambda x: (-x[0], abs(len(query) - len(x[1].get_search_name()))))
    return [w for _, w in scored[:limit]]


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
            if word_str and len(word_str.strip()) > 0:
                self.symspell.create_dictionary_entry(word_str, 1)
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

        suggestions = self.symspell.lookup(
            query,
            Verbosity.CLOSEST,
            max_edit_distance=max_edit_distance
        )

        result_words = []
        seen_words = set()

        for suggestion in suggestions:
            word_str = suggestion.term
            if word_str in self.word_dict and word_str not in seen_words:
                result_words.append(self.word_dict[word_str][0])
                seen_words.add(word_str)

                if len(result_words) >= limit:
                    break

        return result_words


class SpellExtension(Extension):
    def __init__(self):
        self.word_list = []
        self.search_cache = {}
        self.symspell_matcher = SymSpellMatcher()
        super().__init__()
        self._load_vocabularies()

    def _load_vocabularies(self):
        """Load word lists based on current vocabulary preference."""
        vocabularies = [
            voc.strip().lower()
            for voc in self.preferences.get("vocabulary", "english_uk, english").split(",")
        ]
        self.word_list = load_words(vocabularies)
        self.search_cache.clear()

        if self.preferences.get("matching") == "symspell":
            self.symspell_matcher.initialize(self.word_list)

    def on_input(self, input_text, trigger_id):
        if not input_text:
            return [
                ExtensionResult(
                    icon="images/icon.png",
                    name="Type in the word...",
                    description="",
                )
            ]

        query = input_text.strip()
        if not query:
            return []

        # Create cache key
        cache_key = (query, self.preferences.get("matching", "symspell"), self.preferences.get("vocabulary", ""))

        # Check cache first
        if cache_key in self.search_cache:
            result_list = self.search_cache[cache_key]
        else:
            matching = self.preferences.get("matching", "symspell")

            if matching == "regex":
                filtered_words = filter_words_by_first_char(self.word_list, query)
                result_list = [
                    w
                    for w in filtered_words
                    if re.search(r"^{}".format(query), w.get_search_name())
                ]
            elif matching == "symspell":
                result_list = self.symspell_matcher.search(query, max_edit_distance=2, limit=9)
            else:
                filtered_words = filter_words_by_length(self.word_list, query)
                filtered_words = filter_words_by_first_char(filtered_words, query)

                if RAPIDFUZZ_AVAILABLE:
                    result_list = rapidfuzz_search(filtered_words, query, limit=9, score_cutoff=65)
                else:
                    result_list = fuzzy_search_fallback(filtered_words, query, limit=9, min_score=65)

            # Cache results (limit cache size)
            if len(self.search_cache) >= 200:
                oldest_key = next(iter(self.search_cache))
                del self.search_cache[oldest_key]
            self.search_cache[cache_key] = result_list

        items = []
        for result in result_list[:9]:
            word, language = str(result).split("/")
            items.append(
                ExtensionResult(
                    icon="images/icon.png",
                    name=word,
                    description="Language: {}".format(language),
                    on_enter=CopyToClipboardAction(word),
                )
            )

        return items

    def on_preferences_update(self, pref_id, value, previous_value):
        if pref_id in ("vocabulary", "matching"):
            self._load_vocabularies()


if __name__ == "__main__":
    SpellExtension().run()
