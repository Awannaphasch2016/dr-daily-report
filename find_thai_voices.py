#!/usr/bin/env python3
"""
Script to find ElevenLabs voices that work well with Thai language
Run with: doppler run --project rag-chatbot-worktree --config dev_personal -- python find_thai_voices.py
"""

import os
import sys
from src.audio_generator import AudioGenerator

def find_and_test_thai_voices():
    """Find and test voices for Thai language support"""
    print("=" * 80)
    print("Finding Thai-Optimized Voices")
    print("=" * 80)
    print()
    
    try:
        generator = AudioGenerator()
        
        # Get all voices
        print("Fetching available voices...")
        all_voices = generator.get_available_voices()
        print(f"Found {len(all_voices)} total voices\n")
        
        # Find Thai voices
        thai_voices = generator.find_thai_voices()
        print(f"Found {len(thai_voices)} voices that might support Thai:")
        for voice in thai_voices:
            print(f"  - {voice.get('name', 'Unknown')}: {voice.get('voice_id', 'N/A')}")
        print()
        
        # Show all voices with their details, highlighting potential Thai voices
        print("All available voices:")
        print("-" * 80)
        print("💡 Look for voices with 'multilingual', 'asian', or language indicators")
        print()
        
        for i, voice in enumerate(all_voices[:30], 1):  # Show first 30
            voice_id = voice.get('voice_id', 'N/A')
            name = voice.get('name', 'Unknown')
            description = voice.get('description', '')
            labels = voice.get('labels', {})
            category = voice.get('category', '')
            
            # Check if this might be a Thai-friendly voice
            is_multilingual = any(keyword in str(name + description + str(labels)).lower() 
                                 for keyword in ['multilingual', 'asian', 'thai', 'thailand', 'international'])
            
            prefix = "🌟" if is_multilingual else "  "
            
            print(f"{prefix} {i}. {name}")
            print(f"      ID: {voice_id}")
            if description:
                print(f"      Description: {description}")
            if category:
                print(f"      Category: {category}")
            if labels:
                print(f"      Labels: {labels}")
            if is_multilingual:
                print(f"      ⚠️  Potentially better for Thai!")
            print()
        
        # Test with English first to verify API works correctly
        print("=" * 80)
        print("Testing English TTS (to verify API works)")
        print("=" * 80)
        
        english_text = "Hello, this is a test of the ElevenLabs text-to-speech system. The quick brown fox jumps over the lazy dog."
        print(f"Test text: {english_text}")
        print(f"Current voice ID: {generator.voice_id}")
        print()
        
        print("Generating English audio...")
        try:
            english_audio_bytes = generator.generate_audio(english_text)
            print(f"✅ English audio generated successfully! Size: {len(english_audio_bytes):,} bytes ({len(english_audio_bytes)/1024:.1f} KB)")
            
            # Save English audio to file
            english_output_file = "test_english_voice.mp3"
            with open(english_output_file, "wb") as f:
                f.write(english_audio_bytes)
            print(f"✅ English audio saved to: {english_output_file}")
            print(f"   Play with: ffplay -autoexit {english_output_file}")
            print()
            
        except Exception as e:
            print(f"❌ Error generating English audio: {str(e)}")
            print()
            print("Make sure ELEVENLABS_API_KEY is set correctly")
            return False
        
        # Test with Thai text
        print("=" * 80)
        print("Testing Thai TTS with current voice")
        print("=" * 80)
        
        thai_text = "สวัสดีครับ นี่คือการทดสอบภาษาไทย"
        print(f"Test text: {thai_text}")
        print(f"Current voice ID: {generator.voice_id}")
        print()
        
        print("Generating Thai audio...")
        try:
            thai_audio_bytes = generator.generate_audio(thai_text)
            print(f"✅ Thai audio generated successfully! Size: {len(thai_audio_bytes):,} bytes ({len(thai_audio_bytes)/1024:.1f} KB)")
            
            # Save Thai audio to file
            thai_output_file = "test_thai_voice.mp3"
            with open(thai_output_file, "wb") as f:
                f.write(thai_audio_bytes)
            print(f"✅ Thai audio saved to: {thai_output_file}")
            print()
            print("💡 Compare the two audio files:")
            print(f"   English: ffplay -autoexit {english_output_file}")
            print(f"   Thai:    ffplay -autoexit {thai_output_file}")
            print()
            print("💡 Note: If Thai has strong accent, we need to find a Thai-native voice")
            print("   Try different voice IDs from the list above")
            print()
            print("To use a different voice, set ELEVENLABS_VOICE_ID environment variable:")
            print("   export ELEVENLABS_VOICE_ID='your_voice_id_here'")
            print()
            print("=" * 80)
            print("About Thai Voice Support in ElevenLabs")
            print("=" * 80)
            print()
            print("ElevenLabs multilingual_v2 model supports Thai language, but:")
            print("  1. Not all voices pronounce Thai equally well")
            print("  2. Some voices may have stronger accents than others")
            print("  3. Look for voices labeled as 'multilingual' or optimized for Asian languages")
            print("  4. You may need to test multiple voices to find one with authentic Thai accent")
            print()
            print("Alternative: Check ElevenLabs voice library for Thai-specific voices:")
            print("  https://elevenlabs.io/voice-library")
            print("  Filter by language: Thai")
            print()
            
        except Exception as e:
            print(f"❌ Error generating Thai audio: {str(e)}")
            print()
            print("Make sure ELEVENLABS_API_KEY is set correctly")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = find_and_test_thai_voices()
    sys.exit(0 if success else 1)
