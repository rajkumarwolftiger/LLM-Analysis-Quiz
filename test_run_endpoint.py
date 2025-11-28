import requests
import sys
import time

def test_endpoint(url="http://localhost:8020/run"):
    payload = {
        "email": "24f1002577@ds.study.iitm.ac.in",
        "secret": "rajkumar_goud",
        "url": "https://tds-llm-analysis.s-anand.net/demo"
    }
    
    print(f"Sending POST request to {url} with payload: {payload}")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("\n✅ Request accepted! The server is now processing the quiz in the background.")
            print("Check the server terminal for logs to see the progress.")
        else:
            print("\n❌ Request failed.")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to {url}. Is the server running?")

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8020/run"
    test_endpoint(target_url)
