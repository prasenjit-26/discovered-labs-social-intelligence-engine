import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_relationship_extraction_and_persistence():
    print("--- Testing Level 1: Relationship Inference & Persistence ---")
    
    # 1. Analyze text to extract relationships
    # This should extract: ("Sam Altman", "announced", "GPT-5")
    text = "Sam Altman announced GPT-5 yesterday."
    print(f"\n1. Sending text for analysis: '{text}'")
    
    try:
        response = requests.post(f"{BASE_URL}/graph/analyze_text", params={"text": text})
        response.raise_for_status()
        result = response.json()
        print("✅ Extraction Success!")
        print(f"   Extracted: {result['extracted']}")
        print(f"   Current Graph Size: {result['graph_size']}")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return

    # 2. Verify Graph Data Endpoint
    # This should return the graph including the new relationship
    print("\n2. Fetching Graph Data (Visualization format)...")
    try:
        response = requests.get(f"{BASE_URL}/graph")
        response.raise_for_status()
        graph = response.json()
        
        nodes = graph.get("nodes", [])
        links = graph.get("links", [])
        
        print(f"✅ Graph Fetch Success!")
        print(f"   Nodes: {len(nodes)}")
        print(f"   Links: {len(links)}")
        
        # Verify specific link exists
        found = False
        for link in links:
            if link["source"] == "Sam Altman" and link["target"] == "GPT-5":
                found = True
                print("   Found expected link: Sam Altman -> GPT-5")
                break
        
        if not found:
            print("❌ WARNING: Did not find the expected 'Sam Altman -> GPT-5' link in graph response.")
            
    except Exception as e:
        print(f"❌ Graph fetch failed: {e}")

if __name__ == "__main__":
    # Wait a bit for server to be potentially ready if running in composed environment
    # time.sleep(2)
    test_relationship_extraction_and_persistence()
