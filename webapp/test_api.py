#!/usr/bin/env python3
"""
Quick test script to check API endpoint response
"""
import requests
import json

def test_api():
    url = 'http://127.0.0.1:5000/api/tiles-data'
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nTotal records: {len(data)}")
            
            if len(data) > 0:
                print(f"\nFirst record:")
                print(json.dumps(data[0], indent=2))
                
                print(f"\nRecords with price data: {sum(1 for d in data if d.get('price') is not None)}")
                print(f"Records with DBS19 ticker: {sum(1 for d in data if 'DBS19' in d.get('ticker', '').upper())}")
                
                # Check for DBS19
                dbs19_records = [d for d in data if 'DBS19' in d.get('ticker', '').upper()]
                if dbs19_records:
                    print(f"\nDBS19 records found: {len(dbs19_records)}")
                    print(json.dumps(dbs19_records[0], indent=2))
                else:
                    print("\nNo DBS19 records found!")
            else:
                print("\nNo data returned!")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_api()
