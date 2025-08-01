#!/usr/bin/env python3
"""
SymSpell implementation and benchmarking for ulauncher-spell.
"""

import time
import statistics
from symspellpy import SymSpell, Verbosity
from main import load_words

class SymSpellOptimizer:
    def __init__(self):
        self.symspell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        self.words = None
        self.word_dict = {}  # Map word strings to Word objects
        
    def build_dictionary(self, vocabularies=['english_uk', 'english']):
        """Build SymSpell dictionary from vocabulary files."""
        print("Loading vocabularies...")
        start = time.perf_counter()
        self.words = load_words(vocabularies)
        load_time = time.perf_counter() - start
        print(f"Loaded {len(self.words)} words in {load_time:.2f}s")
        
        print("Building SymSpell dictionary...")
        start = time.perf_counter()
        
        # Build dictionary and word mapping
        for word_obj in self.words:
            word_str = word_obj.get_search_name()
            if word_str:  # Skip empty words
                # Add to SymSpell dictionary (frequency = 1 for all words)
                self.symspell.create_dictionary_entry(word_str, 1)
                
                # Map word string to original Word object
                if word_str not in self.word_dict:
                    self.word_dict[word_str] = []
                self.word_dict[word_str].append(word_obj)
        
        build_time = time.perf_counter() - start
        print(f"Built SymSpell dictionary in {build_time:.2f}s")
        print(f"Dictionary contains {len(self.symspell._words)} unique words")
        
        return load_time + build_time
    
    def search(self, query, max_edit_distance=2, limit=9):
        """Search using SymSpell with configurable parameters."""
        if not query:
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
    
    def search_compound(self, query, max_edit_distance=2, limit=9):
        """Search using SymSpell compound word support."""
        if not query:
            return []
        
        # Try compound word segmentation first
        segmentation = self.symspell.word_segmentation(query, max_edit_distance=max_edit_distance)
        
        if segmentation and segmentation.corrected_string != query:
            # If compound segmentation found something, use it
            suggestions = self.symspell.lookup(
                segmentation.corrected_string,
                Verbosity.CLOSEST,
                max_edit_distance=max_edit_distance
            )
        else:
            # Fall back to regular lookup
            suggestions = self.symspell.lookup(
                query,
                Verbosity.CLOSEST,
                max_edit_distance=max_edit_distance
            )
        
        # Convert to Word objects
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

def time_function(func, *args, **kwargs):
    """Time a function call and return (result, time_ms)."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start) * 1000

def run_multiple_times(func, times=10, *args, **kwargs):
    """Run function multiple times and return statistics."""
    results = []
    times_ms = []
    
    for _ in range(times):
        result, time_ms = time_function(func, *args, **kwargs)
        results.append(result)
        times_ms.append(time_ms)
    
    return {
        'results': results,
        'times_ms': times_ms,
        'mean_ms': statistics.mean(times_ms),
        'median_ms': statistics.median(times_ms),
        'min_ms': min(times_ms),
        'max_ms': max(times_ms),
        'std_ms': statistics.stdev(times_ms) if len(times_ms) > 1 else 0
    }

def benchmark_symspell():
    """Comprehensive SymSpell benchmark."""
    print("🔥 SYMSPELL PERFORMANCE BENCHMARK")
    print("=" * 50)
    
    # Initialize SymSpell
    optimizer = SymSpellOptimizer()
    setup_time = optimizer.build_dictionary()
    
    # Test queries (same as main benchmark)
    test_queries = {
        'short_exact': ['cat', 'dog', 'run', 'big'],
        'short_typo': ['teh', 'recieve', 'seperate', 'occured'],
        'medium_exact': ['hello', 'world', 'python', 'computer'],
        'medium_typo': ['speling', 'definitly', 'occassion', 'neccessary'],
        'long_exact': ['optimization', 'performance', 'implementation', 'architecture'],
        'long_typo': ['optmization', 'perfomance', 'implmentation', 'architecure'],
        'prefix_match': ['spel', 'comput', 'optim', 'perform'],
        'no_match': ['zxqwerty', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm']
    }
    
    print(f"\n=== SYMSPELL SEARCH BENCHMARK ===")
    print(f"Setup time: {setup_time:.2f}s")
    print()
    
    all_times = []
    all_times_ed1 = []
    all_times_compound = []
    
    for category, queries in test_queries.items():
        print(f"{category.upper()}:")
        
        for query in queries:
            # Method 1: Standard SymSpell (edit distance 2)
            stats = run_multiple_times(optimizer.search, 10, query, 2, 9)
            result_count = len(stats['results'][0])
            mean_time = stats['mean_ms']
            all_times.append(mean_time)
            
            print(f"  '{query:12}': {result_count:2d} results in {mean_time:5.2f}ms (±{stats['std_ms']:.2f})")
            
            # Method 2: Lower edit distance (edit distance 1) for speed comparison
            stats_ed1 = run_multiple_times(optimizer.search, 10, query, 1, 9)
            result_count_ed1 = len(stats_ed1['results'][0])
            mean_time_ed1 = stats_ed1['mean_ms']
            all_times_ed1.append(mean_time_ed1)
            
            print(f"    {'(ed=1)':12}: {result_count_ed1:2d} results in {mean_time_ed1:5.2f}ms")
            
            # Method 3: Compound word search
            stats_compound = run_multiple_times(optimizer.search_compound, 5, query, 2, 9)
            result_count_compound = len(stats_compound['results'][0])
            mean_time_compound = stats_compound['mean_ms']
            all_times_compound.append(mean_time_compound)
            
            print(f"    {'(compound)':12}: {result_count_compound:2d} results in {mean_time_compound:5.2f}ms")
            
            # Show sample results for interesting queries
            if query in ['teh', 'recieve', 'speling', 'optmization'] and result_count > 0:
                sample_results = [str(r) for r in stats['results'][0][:3]]
                print(f"      → {sample_results}")
        
        print()
    
    # Overall statistics
    print("=== OVERALL SYMSPELL PERFORMANCE ===")
    print(f"Edit Distance 2: {statistics.mean(all_times):5.2f}ms avg ({min(all_times):4.2f}-{max(all_times):5.2f}ms range)")
    print(f"Edit Distance 1: {statistics.mean(all_times_ed1):5.2f}ms avg ({min(all_times_ed1):4.2f}-{max(all_times_ed1):5.2f}ms range)")
    print(f"Compound Search: {statistics.mean(all_times_compound):5.2f}ms avg ({min(all_times_compound):4.2f}-{max(all_times_compound):5.2f}ms range)")
    
    # Compare to baseline (from original benchmark)
    baseline_fuzzy = 80.0  # ms from previous benchmark
    baseline_regex = 56.6  # ms from previous benchmark
    
    symspell_speedup_fuzzy = baseline_fuzzy / statistics.mean(all_times)
    symspell_speedup_regex = baseline_regex / statistics.mean(all_times)
    
    print(f"\nSpeedup vs baseline:")
    print(f"  vs Fuzzy (80.0ms): {symspell_speedup_fuzzy:4.1f}x faster")
    print(f"  vs Regex (56.6ms): {symspell_speedup_regex:4.1f}x faster")
    
    return {
        'setup_time': setup_time,
        'avg_search_time': statistics.mean(all_times),
        'avg_search_time_ed1': statistics.mean(all_times_ed1),
        'avg_search_time_compound': statistics.mean(all_times_compound),
        'speedup_vs_fuzzy': symspell_speedup_fuzzy,
        'speedup_vs_regex': symspell_speedup_regex
    }

if __name__ == "__main__":
    results = benchmark_symspell()
    print(f"\n{'='*50}")
    print("🎯 SymSpell benchmark complete!")
    print(f"Average search time: {results['avg_search_time']:.2f}ms")
    print(f"Setup overhead: {results['setup_time']:.2f}s (one-time cost)")
    print(f"Speedup: {results['speedup_vs_fuzzy']:.1f}x faster than current fuzzy search")