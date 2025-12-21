#!/usr/bin/env python3
"""Test API search endpoint with various queries."""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1/research/sources/search"

test_queries = [
    ("IPC", "Should find Indian Penal Code results"),
    ("Contract Act", "Should find Indian Contract Act results"),
    ("Supreme Court", "Should find Supreme Court resources"),
    ("Article 21", "Should find Constitutional law results"),
    ("CrPC", "Should find Criminal Procedure Code results"),
    ("divorce", "Should find family law results"),
    ("", "Empty query - should show catalog"),
]

print("=" * 60)
print("API SEARCH TESTS")
print("=" * 60)

for query, description in test_queries:
    print(f"\n{description}")
    print(f"Query: '{query}'")
    
    try:
        response = requests.post(
            BASE_URL,
            json={"query": query, "limit": 5},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   Results: {len(results)}")
            
            if results:
                for i, result in enumerate(results[:3], 1):
                    print(f"   {i}. {result.get('title', 'N/A')[:60]}...")
            else:
                print("   ⚠️ No results returned!")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 60)
