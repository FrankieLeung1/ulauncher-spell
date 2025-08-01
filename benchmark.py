#!/usr/bin/env python3
"""
Comprehensive benchmark suite for ulauncher-spell performance optimization.
"""

import time
import statistics
import random
from collections import defaultdict
from main import (
    load_words, filter_words_by_length, filter_words_by_first_char, 
    rapidfuzz_search, RAPIDFUZZ_AVAILABLE, CustomSortedList
)
import re

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

class SpellBenchmark:
    def __init__(self):
        print("Loading vocabularies...")
        start = time.perf_counter()
        self.words = load_words(['english_uk', 'english'])
        load_time = time.perf_counter() - start
        print(f"Loaded {len(self.words)} words in {load_time:.2f}s")
        
        # Test queries of different types
        self.test_queries = {
            'short_exact': ['cat', 'dog', 'run', 'big'],
            'short_typo': ['teh', 'recieve', 'seperate', 'occured'],
            'medium_exact': ['hello', 'world', 'python', 'computer'],
            'medium_typo': ['speling', 'definitly', 'occassion', 'neccessary'],
            'long_exact': ['optimization', 'performance', 'implementation', 'architecture'],
            'long_typo': ['optmization', 'perfomance', 'implmentation', 'architecure'],
            'prefix_match': ['spel', 'comput', 'optim', 'perform'],
            'no_match': ['zxqwerty', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm']
        }
        
        # Flatten all queries for overall testing
        self.all_queries = []
        for category_queries in self.test_queries.values():
            self.all_queries.extend(category_queries)
    
    def benchmark_loading(self):
        """Benchmark vocabulary loading performance."""
        print("\n=== VOCABULARY LOADING BENCHMARK ===")
        
        def load_single_vocab(vocab):
            return load_words([vocab])
        
        vocabs = ['english_uk', 'english', 'deutsch', 'francais']
        
        for vocab in vocabs:
            stats = run_multiple_times(load_single_vocab, 3, vocab)
            word_count = len(stats['results'][0])
            print(f"{vocab:12}: {word_count:6d} words, {stats['mean_ms']:6.1f}ms avg")
        
        # Test loading all vocabularies
        def load_all_vocabs():
            return load_words(['english_uk', 'english'])
        
        stats = run_multiple_times(load_all_vocabs, 3)
        word_count = len(stats['results'][0])
        print(f"{'combined':12}: {word_count:6d} words, {stats['mean_ms']:6.1f}ms avg")
    
    def benchmark_filters(self):
        """Benchmark filtering performance."""
        print("\n=== FILTERING BENCHMARK ===")
        
        for query in ['hello', 'optimization', 'teh', 'zxqwerty']:
            print(f"\nQuery: '{query}'")
            
            # Length filtering
            def length_filter():
                return filter_words_by_length(self.words, query)
            
            stats = run_multiple_times(length_filter, 5)
            filtered_count = len(stats['results'][0])
            reduction = (1 - filtered_count / len(self.words)) * 100
            print(f"  Length filter:    {filtered_count:6d} words ({reduction:5.1f}% reduction) in {stats['mean_ms']:6.2f}ms")
            
            # First-char filtering
            def char_filter():
                return filter_words_by_first_char(self.words, query)
            
            stats = run_multiple_times(char_filter, 5)
            filtered_count = len(stats['results'][0])
            reduction = (1 - filtered_count / len(self.words)) * 100
            print(f"  First-char filter: {filtered_count:6d} words ({reduction:5.1f}% reduction) in {stats['mean_ms']:6.2f}ms")
            
            # Combined filtering
            def combined_filter():
                filtered = filter_words_by_length(self.words, query)
                return filter_words_by_first_char(filtered, query)
            
            stats = run_multiple_times(combined_filter, 5)
            filtered_count = len(stats['results'][0])
            reduction = (1 - filtered_count / len(self.words)) * 100
            print(f"  Combined filter:   {filtered_count:6d} words ({reduction:5.1f}% reduction) in {stats['mean_ms']:6.2f}ms")
    
    def benchmark_search_methods(self):
        """Benchmark different search methods."""
        print("\n=== SEARCH METHOD BENCHMARK ===")
        
        results = defaultdict(list)
        
        for category, queries in self.test_queries.items():
            print(f"\n{category.upper()}:")
            
            for query in queries:
                print(f"  Query: '{query}'")
                
                # Method 1: Regex (no filtering)
                def regex_unfiltered():
                    return [w for w in self.words if re.search(r'^{}'.format(query), w.get_search_name())]
                
                stats = run_multiple_times(regex_unfiltered, 3)
                regex_unfiltered_count = len(stats['results'][0])
                regex_unfiltered_time = stats['mean_ms']
                results['regex_unfiltered'].append(stats['mean_ms'])
                print(f"    Regex (no filter): {regex_unfiltered_count:3d} results in {regex_unfiltered_time:6.1f}ms")
                
                # Method 2: Regex (with filtering)
                def regex_filtered():
                    filtered = filter_words_by_first_char(self.words, query)
                    return [w for w in filtered if re.search(r'^{}'.format(query), w.get_search_name())]
                
                stats = run_multiple_times(regex_filtered, 5)
                regex_filtered_count = len(stats['results'][0])
                regex_filtered_time = stats['mean_ms']
                results['regex_filtered'].append(stats['mean_ms'])
                print(f"    Regex (filtered):  {regex_filtered_count:3d} results in {regex_filtered_time:6.1f}ms (speedup: {regex_unfiltered_time/regex_filtered_time:.1f}x)")
                
                # Method 3: Fuzzy (original)
                def fuzzy_original():
                    fuzzy_list = CustomSortedList(query, min_score=65)
                    # Use subset to avoid timeout on large queries
                    subset = self.words[:20000] if len(self.words) > 20000 else self.words
                    fuzzy_list.extend(subset)
                    return list(fuzzy_list)[:9]
                
                stats = run_multiple_times(fuzzy_original, 3)
                fuzzy_original_count = len(stats['results'][0])
                fuzzy_original_time = stats['mean_ms']
                results['fuzzy_original'].append(stats['mean_ms'])
                print(f"    Fuzzy (20k subset): {fuzzy_original_count:3d} results in {fuzzy_original_time:6.1f}ms")
                
                # Method 4: Fuzzy (optimized)
                def fuzzy_optimized():
                    filtered = filter_words_by_length(self.words, query)
                    filtered = filter_words_by_first_char(filtered, query)
                    if RAPIDFUZZ_AVAILABLE:
                        return rapidfuzz_search(filtered, query, limit=9, score_cutoff=65)
                    else:
                        fuzzy_list = CustomSortedList(query, min_score=65)
                        fuzzy_list.extend(filtered)
                        return list(fuzzy_list)[:9]
                
                stats = run_multiple_times(fuzzy_optimized, 5)
                fuzzy_optimized_count = len(stats['results'][0])
                fuzzy_optimized_time = stats['mean_ms']
                results['fuzzy_optimized'].append(stats['mean_ms'])
                
                # Calculate estimated speedup vs unfiltered fuzzy
                estimated_full_fuzzy_time = fuzzy_original_time * (len(self.words) / 20000)
                speedup = estimated_full_fuzzy_time / fuzzy_optimized_time
                print(f"    Fuzzy (optimized): {fuzzy_optimized_count:3d} results in {fuzzy_optimized_time:6.1f}ms (est. speedup: {speedup:.1f}x)")
        
        # Summary statistics
        print(f"\n=== OVERALL PERFORMANCE SUMMARY ===")
        for method, times in results.items():
            mean_time = statistics.mean(times)
            print(f"{method:18}: {mean_time:6.1f}ms avg ({min(times):5.1f}-{max(times):5.1f}ms range)")
    
    def benchmark_cache_effectiveness(self):
        """Benchmark cache effectiveness."""
        print("\n=== CACHE EFFECTIVENESS BENCHMARK ===")
        
        # Simulate cache with simple dict
        cache = {}
        
        def cached_search(query, method='fuzzy'):
            cache_key = (query, method)
            if cache_key in cache:
                return cache[cache_key], True  # True = cache hit
            
            # Simulate search
            if method == 'fuzzy':
                filtered = filter_words_by_length(self.words, query)
                filtered = filter_words_by_first_char(filtered, query)
                result = rapidfuzz_search(filtered, query, limit=9, score_cutoff=65)
            else:
                filtered = filter_words_by_first_char(self.words, query)
                result = [w for w in filtered if re.search(r'^{}'.format(query), w.get_search_name())]
            
            cache[cache_key] = result
            return result, False  # False = computed
        
        # Test with repeated queries
        test_sequence = ['hello', 'world', 'python', 'hello', 'spell', 'world', 'hello', 'test', 'python']
        
        print("Query sequence simulation:")
        total_time = 0
        cache_hits = 0
        
        for i, query in enumerate(test_sequence):
            start = time.perf_counter()
            result, was_cached = cached_search(query, 'fuzzy')
            end = time.perf_counter()
            
            query_time = (end - start) * 1000
            total_time += query_time
            
            if was_cached:
                cache_hits += 1
            
            status = "CACHED" if was_cached else "COMPUTED"
            print(f"  {i+1:2d}. '{query:8}': {query_time:6.1f}ms ({status:8}) - {len(result)} results")
        
        print(f"\nCache statistics:")
        print(f"  Total queries: {len(test_sequence)}")
        print(f"  Cache hits: {cache_hits} ({cache_hits/len(test_sequence)*100:.1f}%)")
        print(f"  Total time: {total_time:.1f}ms")
        print(f"  Average time: {total_time/len(test_sequence):.1f}ms per query")
    
    def run_all_benchmarks(self):
        """Run all benchmark suites."""
        print("🚀 ULAUNCHER-SPELL PERFORMANCE BENCHMARK")
        print("=" * 50)
        
        self.benchmark_loading()
        self.benchmark_filters()
        self.benchmark_search_methods()
        self.benchmark_cache_effectiveness()
        
        print("\n" + "=" * 50)
        print("Benchmark complete! 🎯")

if __name__ == "__main__":
    benchmark = SpellBenchmark()
    benchmark.run_all_benchmarks()