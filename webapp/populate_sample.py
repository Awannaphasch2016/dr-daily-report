#!/usr/bin/env python3
"""
Populate database with existing English audio report
"""

import os
import sys
import base64
from datetime import date
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def save_existing_report():
    """Save the existing DBS19 English report to database"""
    
    # Check if English audio file exists
    audio_file = "../report_DBS19_english.mp3"
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return False
    
    # Read audio file
    with open(audio_file, 'rb') as f:
        audio_bytes = f.read()
    
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    # Sample report text (you can replace with actual report)
    report_text = """
📖 **เรื่องราวของหุ้นตัวนี้**

บริษัท DBS Group Holdings Ltd กำลังอยู่ในช่วงที่มีความผันผวนสูง โดยมีคะแนนความไม่แน่นอนที่ 51 จาก 100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 66 เปอร์เซ็นต์ แสดงถึงความเสี่ยงที่มากกว่าปกติ

💡 **สิ่งที่คุณต้องรู้**

ราคาเคลื่อนไหวช้า แต่ราคา 22.06 เปอร์เซ็นต์ เหนือ VWAP แสดงแรงซื้อชนะ

🎯 **ควรทำอะไรตอนนี้?**

แนะนำ BUY - มีโอกาสดีในการเข้าตำแหน่ง
"""
    
    report_data = {
        'ticker': 'DBS19',
        'report_date': str(date.today()),
        'report_text': report_text,
        'audio_english_base64': audio_base64,
        'recommendation': 'BUY'
    }
    
    # Save to database
    api_url = "http://localhost:5000"
    try:
        response = requests.post(
            f"{api_url}/api/save_report",
            json=report_data,
            timeout=10
        )
        response.raise_for_status()
        print(f"✅ Report saved successfully!")
        print(f"   View at: {api_url}/report/DBS19/{report_data['report_date']}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Flask app at {api_url}")
        print("   Start Flask app first: python webapp/app.py")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    save_existing_report()
