import requests

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("🚀 BULK RECOMMENDATIONS SCREENSHOT CAPTURE TEST")
print("=" * 60)
print("\nThis will capture recommendations screenshots for all leads")
print("that have speed test data but no recommendations screenshot yet.\n")

# Test capturing recommendations for all leads
print("📸 Starting bulk recommendations screenshot capture...")
print(f"📡 Making request to: {BASE_URL}/capture-recommendations-all\n")

try:
    response = requests.post(f"{BASE_URL}/capture-recommendations-all", timeout=600)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS! Bulk capture completed")
        print("=" * 60)
        print("\n📊 RESULTS:")
        print(f"   Message: {result.get('message', 'N/A')}")
        
        if 'result' in result:
            res = result['result']
            print(f"\n   ✅ Successful: {res.get('success', 0)}")
            print(f"   ❌ Failed: {res.get('failed', 0)}")
            print(f"   📋 Total Processed: {res.get('total', 0)}")
        
        print("\n" + "=" * 60)
    else:
        print(f"❌ ERROR: Received status code {response.status_code}")
        print(f"Response: {response.text}")

except requests.exceptions.Timeout:
    print("⏱️  Request timed out (this is normal for large batches)")
    print("✅ The process is still running in the background.")
    print("💡 Check your FastAPI server terminal for progress updates!")
    
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Could not connect to the server")
    print("💡 Make sure your FastAPI server is running:")
    print("   uvicorn main:app --reload")
    
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print("\n" + "=" * 60)
print("💡 TIP: Check the FastAPI terminal for detailed progress logs!")
print("=" * 60)
