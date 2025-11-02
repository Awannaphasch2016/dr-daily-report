#!/usr/bin/env python3
"""
Quick script to generate and play Botnoi Thai audio
Usage: doppler run --project rag-chatbot-worktree --config dev_personal -- python quick_botnoi_test.py [voice_id]
"""

import os
import sys
from src.audio_generator import AudioGenerator

def main():
    # Get voice ID from command line or environment
    voice_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv("BOTNOI_VOICE_ID")
    
    if not voice_id:
        print("❌ Voice ID required!")
        print("Usage: python quick_botnoi_test.py <voice_id>")
        print("Or set BOTNOI_VOICE_ID environment variable")
        print()
        print("Get voice ID from Botnoi dashboard:")
        print("https://botnoigroup.com/botnoivoice/doc/api-user-guide")
        return 1
    
    try:
        generator = AudioGenerator(voice_id=voice_id)
        
        # Test Thai text
        thai_text = "สวัสดีครับ นี่คือการทดสอบภาษาไทยด้วย Botnoi Voice สำหรับรายงานการวิเคราะห์หุ้น"
        print(f"Generating audio for: {thai_text}")
        print(f"Using voice ID: {voice_id}")
        
        audio_bytes = generator.generate_audio(thai_text)
        
        output_file = "test_botnoi_thai.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        
        print(f"✅ Audio generated! Saved to: {output_file}")
        print(f"   Size: {len(audio_bytes):,} bytes ({len(audio_bytes)/1024:.1f} KB)")
        print()
        print("Playing audio...")
        
        # Play with ffplay
        import subprocess
        subprocess.run(["ffplay", "-autoexit", "-nodisp", output_file], check=True)
        
        print("✅ Audio playback complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
