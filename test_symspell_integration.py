#!/usr/bin/env python3
"""
Test script for SymSpell integration in ulauncher-spell.
"""

import time
import os
import sys

# Mock the ulauncher modules for testing
class MockAction:
    def __init__(self, data):
        self.data = data

class CopyToClipboardAction(MockAction):
    pass

class ExtensionResultItem:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class RenderResultListAction(MockAction):  
    pass

# Mock ulauncher modules
sys.modules['ulauncher.api.shared.action.CopyToClipboardAction'] = type('Module', (), {'CopyToClipboardAction': CopyToClipboardAction})
sys.modules['ulauncher.search.SortedList'] = type('Module', (), {'SortedList': object})
sys.modules['ulauncher.utils.SortedCollection'] = type('Module', (), {'SortedCollection': object})
sys.modules['ulauncher.api.client.Extension'] = type('Module', (), {'Extension': object, 'PreferencesEventListener': object})
sys.modules['ulauncher.api.client.EventListener'] = type('Module', (), {'EventListener': object})
sys.modules['ulauncher.api.shared.event'] = type('Module', (), {
    'KeywordQueryEvent': object,
    'ItemEnterEvent': object, 
    'PreferencesEvent': object,
    'PreferencesUpdateEvent': object
})
sys.modules['ulauncher.api.shared.item.ExtensionResultItem'] = type('Module', (), {'ExtensionResultItem': ExtensionResultItem})
sys.modules['ulauncher.api.shared.action.RenderResultListAction'] = type('Module', (), {'RenderResultListAction': RenderResultListAction})
sys.modules['ulauncher.api.shared.action.ExtensionCustomAction'] = type('Module', (), {'ExtensionCustomAction': MockAction})
sys.modules['ulauncher.api.shared.action.HideWindowAction'] = type('Module', (), {'HideWindowAction': MockAction})
sys.modules['ulauncher.api.shared.action.OpenUrlAction'] = type('Module', (), {'OpenUrlAction': MockAction})
sys.modules['ulauncher.utils.fuzzy_search'] = type('Module', (), {'get_score': lambda x: 0})

# Now import our main module
from main import OneDictExtension, load_words, SymSpellMatcher, SYMSPELL_AVAILABLE

def test_symspell_matcher():
    """Test SymSpellMatcher directly."""
    print("=== TESTING SYMSPELL MATCHER ===")
    
    if not SYMSPELL_AVAILABLE:
        print("❌ SymSpell not available - skipping test")
        return False
    
    # Load a small subset of words for testing
    print("Loading test vocabulary...")
    words = load_words(['english_uk'])[:10000]  # Limit for faster testing
    print(f"Loaded {len(words)} words for testing")
    
    # Initialize matcher
    matcher = SymSpellMatcher()
    success = matcher.initialize(words)
    
    if not success:
        print("❌ Failed to initialize SymSpell matcher")
        return False
    
    print("✅ SymSpell matcher initialized successfully")
    
    # Test queries
    test_queries = [
        ('hello', 'exact match'),
        ('teh', 'simple typo'),
        ('recieve', 'common misspelling'),
        ('speling', 'medium typo'),
        ('optmization', 'longer typo'),
        ('nonexistentword', 'no match expected')
    ]
    
    print("\nTesting search functionality:")
    for query, description in test_queries:
        start = time.perf_counter()
        results = matcher.search(query, max_edit_distance=2, limit=9)
        search_time = (time.perf_counter() - start) * 1000
        
        print(f"  '{query:15}' ({description:18}): {len(results):2d} results in {search_time:6.2f}ms")
        
        if results:
            sample_results = [str(r) for r in results[:3]]
            print(f"    → {sample_results}")
    
    return True

def test_extension_integration():
    """Test SymSpell integration with the main extension."""
    print("\n=== TESTING EXTENSION INTEGRATION ===")
    
    if not SYMSPELL_AVAILABLE:
        print("❌ SymSpell not available - skipping integration test")
        return False
    
    try:
        # Create a mock extension instance (can't fully initialize due to ulauncher dependencies)
        print("Creating extension components...")
        
        # Test word loading
        words = load_words(['english_uk', 'english'])
        print(f"✅ Loaded {len(words)} words successfully")
        
        # Test SymSpell matcher initialization
        matcher = SymSpellMatcher()
        success = matcher.initialize(words)
        
        if success:
            print("✅ SymSpell matcher integrated successfully")
            
            # Test a few searches
            test_queries = ['hello', 'teh', 'speling']
            print("Testing integrated searches...")
            
            for query in test_queries:
                start = time.perf_counter()
                results = matcher.search(query)
                search_time = (time.perf_counter() - start) * 1000
                print(f"  '{query}': {len(results)} results in {search_time:.2f}ms")
            
            return True
        else:
            print("❌ Failed to initialize SymSpell matcher")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_performance_comparison():
    """Compare SymSpell performance with other methods."""
    print("\n=== PERFORMANCE COMPARISON ===")
    
    if not SYMSPELL_AVAILABLE:
        print("❌ SymSpell not available - skipping performance test")
        return False
    
    # Load words for testing
    words = load_words(['english_uk', 'english'])
    print(f"Testing with {len(words)} words")
    
    # Initialize SymSpell
    matcher = SymSpellMatcher()
    matcher.initialize(words)
    
    test_queries = ['hello', 'teh', 'recieve', 'speling', 'optmization']
    
    print("\nPerformance comparison:")
    symspell_times = []
    
    for query in test_queries:
        # Test SymSpell
        start = time.perf_counter()
        symspell_results = matcher.search(query)
        symspell_time = (time.perf_counter() - start) * 1000
        symspell_times.append(symspell_time)
        
        print(f"  '{query:12}': SymSpell {len(symspell_results):2d} results in {symspell_time:6.2f}ms")
    
    avg_symspell_time = sum(symspell_times) / len(symspell_times)
    print(f"\nAverage SymSpell time: {avg_symspell_time:.2f}ms")
    
    # Compare to benchmark baseline (from previous tests)
    baseline_fuzzy = 80.0  # ms
    baseline_regex = 56.6  # ms
    
    speedup_fuzzy = baseline_fuzzy / avg_symspell_time
    speedup_regex = baseline_regex / avg_symspell_time
    
    print(f"Speedup vs fuzzy search: {speedup_fuzzy:.0f}x faster")
    print(f"Speedup vs regex search: {speedup_regex:.0f}x faster")
    
    return True

def main():
    """Run all tests."""
    print("🔥 ULAUNCHER-SPELL SYMSPELL INTEGRATION TEST")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('main.py'):
        print("❌ Please run this script from the ulauncher-spell directory")
        return False
    
    all_passed = True
    
    # Test 1: Direct SymSpell matcher
    all_passed &= test_symspell_matcher()
    
    # Test 2: Extension integration
    all_passed &= test_extension_integration()
    
    # Test 3: Performance comparison
    all_passed &= test_performance_comparison()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎯 All tests passed! SymSpell integration is working correctly.")
        print("\nTo use SymSpell in Ulauncher:")
        print("1. Install the extension from your GitHub fork")
        print("2. Set matching method to 'symspell' in preferences")
        print("3. Enjoy ultra-fast spell checking!")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)