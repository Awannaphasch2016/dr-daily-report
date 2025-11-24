"""Quick test script for API endpoints"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_health():
    """Test health endpoint"""
    print("Testing /api/v1/health...")
    response = client.get("/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    assert response.status_code == 200


def test_search():
    """Test search endpoint"""
    print("Testing /api/v1/search...")

    # Test search for NVIDIA
    response = client.get("/api/v1/search?q=NVDA")
    print(f"Status: {response.status_code}")
    print(f"Query: q=NVDA")
    print(f"Results count: {len(response.json()['results'])}")
    print(f"First result: {response.json()['results'][0] if response.json()['results'] else 'None'}\n")
    assert response.status_code == 200

    # Test search for company name
    response = client.get("/api/v1/search?q=nvidia")
    print(f"Query: q=nvidia (lowercase company name)")
    print(f"Results count: {len(response.json()['results'])}")
    print(f"Results: {response.json()['results']}\n")
    assert response.status_code == 200

    # Test search for DBS
    response = client.get("/api/v1/search?q=DBS")
    print(f"Query: q=DBS")
    print(f"Results count: {len(response.json()['results'])}")
    print(f"Results: {response.json()['results']}\n")
    assert response.status_code == 200


def test_report_validation():
    """Test report endpoint validation (not full generation)"""
    print("Testing /api/v1/report validation...")

    # Test unsupported ticker
    response = client.get("/api/v1/report/INVALID")
    print(f"Status for INVALID ticker: {response.status_code}")
    print(f"Error response: {response.json()}\n")
    assert response.status_code == 400

    # Test supported ticker (note: this will actually run the agent if you have API keys set)
    # Uncomment to test full report generation (requires API keys and takes time)
    # print("Testing full report generation for NVDA19...")
    # response = client.get("/api/v1/report/NVDA19")
    # print(f"Status: {response.status_code}")
    # if response.status_code == 200:
    #     data = response.json()
    #     print(f"Ticker: {data['ticker']}")
    #     print(f"Company: {data['company_name']}")
    #     print(f"Stance: {data['stance']}")
    #     print(f"Technical metrics count: {len(data['technical_metrics'])}")
    # else:
    #     print(f"Error: {response.json()}")


if __name__ == "__main__":
    print("=" * 60)
    print("API Test Suite")
    print("=" * 60 + "\n")

    test_health()
    test_search()
    test_report_validation()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)
