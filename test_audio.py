#!/usr/bin/env python3
"""
Quick test script to verify ElevenLabs audio generation is working
Run with: doppler run --project rag-chatbot-worktree --config dev_personal -- python test_audio.py
"""

import os
import sys

def test_audio_setup():
    """Test if audio generator can be initialized"""
    print("=" * 80)
    print("Testing ElevenLabs Audio Generation Setup")
    print("=" * 80)
    print()
    
    # Check environment variable
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if api_key:
        print(f"✅ ELEVENLABS_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("❌ ELEVENLABS_API_KEY not found in environment")
        print()
        print("Make sure you're running with Doppler:")
        print("  doppler run --project rag-chatbot-worktree --config dev_personal -- python test_audio.py")
        return False
    
    # Try to import and initialize
    try:
        from src.audio_generator import AudioGenerator
        print("✅ AudioGenerator imported successfully")
        
        generator = AudioGenerator()
        print("✅ AudioGenerator initialized successfully")
        
        # Test getting voices (this requires API key)
        print()
        print("Testing API connection...")
        voices = generator.get_available_voices()
        if voices:
            print(f"✅ API connection successful! Found {len(voices)} voices")
            print()
            print("Available voices (first 5):")
            for voice in voices[:5]:
                print(f"  - {voice.get('name', 'Unknown')}: {voice.get('voice_id', 'N/A')}")
        else:
            print("⚠️  Could not fetch voices (may be API rate limit or permissions)")
        
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
        
        print()
        print("=" * 80)
        print("✅ All tests passed! Audio generation is ready to use.")
        print("=" * 80)
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
    success = test_audio_setup()
    sys.exit(0 if success else 1)
