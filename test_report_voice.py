#!/usr/bin/env python3
"""Test Botnoi voice-over with a sample ticker report"""
import os
import sys
from src.audio_generator import AudioGenerator

os.environ['BOTNOI_VOICE_ID'] = '8'

sample_report = """
เรื่องราวของหุ้นตัวนี้

บริษัท DBS Group Holdings Ltd กำลังอยู่ในช่วงที่มีความผันผวนสูง โดยมีคะแนนความไม่แน่นอนที่ 51 จาก 100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 66 เปอร์เซ็นต์ แสดงถึงความเสี่ยงที่มากกว่าปกติ

ในขณะที่ ATR อยู่ที่ 1.30 เปอร์เซ็นต์ ซึ่งอยู่ในเปอร์เซ็นไทล์ 69.8 เปอร์เซ็นต์ บ่งบอกถึงการเคลื่อนไหวของราคาที่ค่อนข้างมั่นคง

ราคา 22.06 เปอร์เซ็นต์ เหนือ VWAP ชี้ให้เห็นว่าแรงซื้อยังคงมีความแรงเป็นพิเศษ และปริมาณการซื้อขายที่ 0.87 เท่าของเฉลี่ย เป็นการแสดงว่านักลงทุนยังคงระมัดระวัง

สิ่งที่คุณต้องรู้

ราคาเคลื่อนไหวช้า แต่ราคา 2.4 เปอร์เซ็นต์ เหนือ VWAP แสดงแรงซื้อชนะ ควรทำอะไรตอนนี้ แนะนำ BUY มีโอกาสดีในการเข้าตำแหน่ง
"""

try:
    generator = AudioGenerator(voice_id='8')
    cleaned_text = generator.clean_text_for_tts(sample_report)
    print(f"Generating audio for {len(cleaned_text)} characters...")
    audio_bytes = generator.generate_audio(cleaned_text)
    output_file = "report_voice_test.mp3"
    with open(output_file, "wb") as f:
        f.write(audio_bytes)
    print(f"✅ Audio saved to {output_file} ({len(audio_bytes)/1024:.1f} KB)")
    print("Playing audio...")
    import subprocess
    subprocess.run(["ffplay", "-autoexit", "-nodisp", output_file], check=True)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
