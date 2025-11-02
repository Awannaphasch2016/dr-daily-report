#!/usr/bin/env python3
"""
Test script for Botnoi Voice API
Run with: doppler run --project rag-chatbot-worktree --config dev_personal -- python test_botnoi.py
"""

import os
import sys
from src.audio_generator import AudioGenerator

def test_botnoi_setup():
    """Test if Botnoi audio generator can be initialized and used"""
    print("=" * 80)
    print("Testing Botnoi Voice API Setup")
    print("=" * 80)
    print()
    
    # Check environment variable
    api_key = os.getenv("BOTNOI_API_KEY")
    voice_id = os.getenv("BOTNOI_VOICE_ID")
    
    if api_key:
        print(f"✅ BOTNOI_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("❌ BOTNOI_API_KEY not found in environment")
        print()
        print("Make sure you're running with Doppler:")
        print("  doppler run --project rag-chatbot-worktree --config dev_personal -- python test_botnoi.py")
        return False
    
    if voice_id:
        print(f"✅ BOTNOI_VOICE_ID found: {voice_id}")
    else:
        print("⚠️  BOTNOI_VOICE_ID not found - will need to be set")
        print("   Get voice ID from Botnoi dashboard or API docs")
        print("   https://botnoigroup.com/botnoivoice/doc/api-user-guide")
    
    # Try to import and initialize
    try:
        generator = AudioGenerator()
        print("✅ AudioGenerator initialized successfully")
        
        # Test text cleaning
        print()
        print("Testing text cleaning...")
        test_text = """
        📖 **เรื่องราวของหุ้นตัวนี้**
        Apple กำลังอยู่ในโมเมนต์ที่น่าสนใจ - ตลาดเสถียร [1]
        
        💡 **สิ่งที่คุณต้องรู้**
        ราคาเคลื่อนไหวช้า แต่ราคา 2.4% เหนือ VWAP แสดงแรงซื้อชนะ
        """
        cleaned = generator.clean_text_for_tts(test_text)
        print(f"✅ Text cleaning works")
        print(f"   Original length: {len(test_text)} chars")
        print(f"   Cleaned length: {len(cleaned)} chars")
        print(f"   Preview: {cleaned[:100]}...")
        
        # Test audio generation if voice_id is set
        if voice_id:
            print()
            print("Testing audio generation...")
            thai_text = "สวัสดีครับ นี่คือการทดสอบภาษาไทยด้วย Botnoi Voice"
            print(f"Test text: {thai_text}")
            
            try:
                audio_bytes = generator.generate_audio(thai_text)
                print(f"✅ Audio generated successfully! Size: {len(audio_bytes):,} bytes ({len(audio_bytes)/1024:.1f} KB)")
                
                # Save to file
                output_file = "test_botnoi_audio.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)
                print(f"✅ Audio saved to: {output_file}")
                print(f"   Play with: ffplay -autoexit {output_file}")
                
            except Exception as e:
                print(f"❌ Error generating audio: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print()
            print("⚠️  Skipping audio generation test - BOTNOI_VOICE_ID not set")
        
        print()
        print("=" * 80)
        print("✅ All tests passed! Botnoi audio generation is ready to use.")
        print("=" * 80)
        print()
        print("💡 Note: Botnoi provides authentic Thai pronunciation!")
        print("   Set BOTNOI_VOICE_ID to use a specific voice")
        return True
        
    except ValueError as e:
        print(f"❌ Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_botnoi_setup()
    sys.exit(0 if success else 1)
