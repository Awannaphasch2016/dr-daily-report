"""
Dual Audio Generator supporting Botnoi Voice (Thai) and ElevenLabs (English)
Converts text reports to audio for users who prefer listening
- Uses Botnoi Voice API for authentic Thai pronunciation
- Uses ElevenLabs API for English pronunciation
"""

import os
import base64
import requests
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def detect_language(text: str) -> str:
    """Detect if text is Thai or English"""
    # Check for Thai characters (Unicode range: \u0E00-\u0E7F)
    thai_char_pattern = re.compile(r'[\u0E00-\u0E7F]')
    has_thai = bool(thai_char_pattern.search(text))
    
    # If has Thai characters, it's Thai
    if has_thai:
        return 'th'
    
    # Otherwise assume English
    return 'en'


class ElevenLabsGenerator:
    """Generate audio using ElevenLabs API (for English)"""
    
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "pNInz6obpgDQGcFmaJgB"  # Default: Adam
        self.api_url = "https://api.elevenlabs.io/v1/text-to-speech"
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not found")
    
    def generate_audio(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """Generate audio using ElevenLabs API"""
        voice_id = voice_id or self.voice_id
        
        payload = {
            "text": text.strip(),
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        url = f"{self.api_url}/{voice_id}"
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            error_msg = f"ElevenLabs API error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - Status: {e.response.status_code}"
            raise requests.exceptions.RequestException(error_msg) from e


class BotnoiGenerator:
    """Generate audio using Botnoi Voice API (for Thai)"""
    
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None, speed: float = 1.0):
        self.api_key = api_key or os.getenv("BOTNOI_API_KEY")
        self.voice_id = voice_id or os.getenv("BOTNOI_VOICE_ID")
        self.speed = speed
        self.api_url = "https://api-voice.botnoi.ai/openapi/v1/generate_audio_v2"
        
        if not self.api_key:
            raise ValueError("BOTNOI_API_KEY not found")
    
    def generate_audio(self, text: str, voice_id: Optional[str] = None, speed: Optional[float] = None) -> bytes:
        """Generate audio using Botnoi Voice API"""
        voice_id = voice_id or self.voice_id
        if not voice_id:
            raise ValueError("Voice ID (speaker) is required. Set BOTNOI_VOICE_ID environment variable.")
        
        speed = speed if speed is not None else self.speed
        
        payload = {
            "text": text.strip(),
            "speaker": str(voice_id),
            "volume": 1.0,
            "speed": speed,
            "type_media": "mp3",
            "save_file": "True",
            "language": "th"
        }
        
        headers = {
            "accept": "application/json",
            "botnoi-token": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if 'audio_url' in result:
                audio_response = requests.get(result['audio_url'], timeout=60)
                audio_response.raise_for_status()
                return audio_response.content
            else:
                raise ValueError(f"Unexpected response format - missing audio_url: {result}")
        except requests.exceptions.RequestException as e:
            error_msg = f"Botnoi API error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - Status: {e.response.status_code}"
                    error_msg += f" - Response: {e.response.text[:200]}"
            raise requests.exceptions.RequestException(error_msg) from e


class AudioGenerator:
    """
    Dual Audio Generator supporting both Botnoi Voice (Thai) and ElevenLabs (English)
    
    Automatically detects language and uses appropriate TTS service:
    - Thai text ? Botnoi Voice API (authentic Thai pronunciation)
    - English text ? ElevenLabs API (high-quality English voices)
    """
    
    def __init__(
        self,
        botnoi_api_key: Optional[str] = None,
        botnoi_voice_id: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        elevenlabs_voice_id: Optional[str] = None,
        speed: float = 1.0
    ):
        """
        Initialize dual audio generator
        
        Args:
            botnoi_api_key: Botnoi API key (defaults to BOTNOI_API_KEY env var)
            botnoi_voice_id: Botnoi voice ID (defaults to BOTNOI_VOICE_ID env var)
            elevenlabs_api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
            elevenlabs_voice_id: ElevenLabs voice ID (defaults to ELEVENLABS_VOICE_ID env var)
            speed: Speech speed for Botnoi (default: 1.0)
        """
        # Initialize Botnoi generator (required for Thai)
        try:
            self.botnoi_generator = BotnoiGenerator(
                api_key=botnoi_api_key,
                voice_id=botnoi_voice_id,
                speed=speed
            )
        except ValueError:
            self.botnoi_generator = None
        
        # Initialize ElevenLabs generator (optional for English)
        try:
            self.elevenlabs_generator = ElevenLabsGenerator(
                api_key=elevenlabs_api_key,
                voice_id=elevenlabs_voice_id
            )
        except ValueError:
            self.elevenlabs_generator = None
    
    def generate_audio(
        self,
        text: str,
        language: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Generate audio from text, automatically selecting the appropriate TTS service
        
        Args:
            text: Text to convert to speech (Thai or English)
            language: Language code ('th' or 'en'). If None, auto-detects from text.
            **kwargs: Additional parameters passed to specific generators
            
        Returns:
            Audio bytes (MP3 format)
            
        Raises:
            ValueError: If text is empty or appropriate TTS service not available
            requests.RequestException: If API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Auto-detect language if not specified
        if language is None:
            language = detect_language(text)
        
        # Generate audio using appropriate service
        if language == 'th':
            if not self.botnoi_generator:
                raise ValueError("Botnoi generator not available. Set BOTNOI_API_KEY.")
            return self.botnoi_generator.generate_audio(text, **kwargs)
        elif language == 'en':
            if not self.elevenlabs_generator:
                raise ValueError("ElevenLabs generator not available. Set ELEVENLABS_API_KEY.")
            return self.elevenlabs_generator.generate_audio(text, **kwargs)
        else:
            raise ValueError(f"Unsupported language: {language}. Supported: 'th', 'en'")
    
    def generate_audio_base64(
        self,
        text: str,
        language: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate audio and return as base64-encoded string
        
        Args:
            text: Text to convert to speech
            language: Language code ('th' or 'en'). If None, auto-detects.
            **kwargs: Additional parameters passed to specific generators
            
        Returns:
            Base64-encoded audio string
        """
        audio_bytes = self.generate_audio(text, language=language, **kwargs)
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def translate_to_english(self, thai_text: str, llm) -> str:
        """
        Translate Thai text to English using LLM
        
        Args:
            thai_text: Thai text to translate
            llm: LangChain LLM instance for translation
            
        Returns:
            English translated text
        """
        from langchain_core.messages import HumanMessage
        
        prompt = f"""Translate the following Thai financial report to English. 
Maintain the same structure, formatting, and meaning. Keep financial terms accurate.
Keep numbers, percentages, and technical indicators unchanged.

Thai text:
{thai_text}

Provide only the English translation:"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def clean_text_for_tts(self, text: str) -> str:
        """
        Clean text for better TTS quality
        
        Removes markdown formatting, emojis, and other elements that don't translate well to speech.
        Converts markdown links to readable text.
        
        Args:
            text: Raw text with markdown/formatting
            
        Returns:
            Cleaned text suitable for TTS
        """
        import re
        
        # Remove markdown headers (# ## ###)
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Remove markdown bold (**text**)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Remove markdown italic (*text*)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Convert markdown links [text](url) to just "text"
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove emojis (optional - you might want to keep some)
        # Common emojis used in reports: ?? ?? ?? ?? ?? ?? ??
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
        
        # Clean up multiple spaces/newlines
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r' {2,}', ' ', text)  # Max 1 space
        
        # Remove reference numbers like [1], [2] (keep the text before them)
        text = re.sub(r'\s*\[\d+\]', '', text)
        
        # Add pauses after sentences (periods, question marks, exclamation marks)
        text = re.sub(r'([.!?])\s+', r'\1 ', text)
        
        return text.strip()
    
    def get_available_voices(self) -> list:
        """
        Get list of available voices from Botnoi Voice API
        
        Note: Botnoi API may have a different endpoint for listing voices.
        Check https://botnoigroup.com/botnoivoice/doc/api-user-guide for details.
        
        Returns:
            List of voice dictionaries with id, name, and language info
        """
        # Botnoi may have a different endpoint for listing voices
        # For now, return empty list - user should check Botnoi documentation
        # or set voice_id manually
        print("Note: Use Botnoi dashboard or API docs to find available voice IDs")
        print("See: https://botnoigroup.com/botnoivoice/doc/api-user-guide")
        return []


def test_audio_generator():
    """Test function for audio generator"""
    try:
        generator = AudioGenerator()
        
        test_text = """
        ?? ??????????????????????
        Apple ???????????????????????????? - ?????????? ????????????? 22 ??? 100
        
        ?? ?????????????????
        ????????????????? ??????? 2.4% ????? VWAP ??????????????
        
        ?? ????????????????
        ????? BUY - ?????????????????????????
        """
        
        print("?? Testing audio generation...")
        print(f"Text length: {len(test_text)} characters")
        
        # Clean text
        cleaned_text = generator.clean_text_for_tts(test_text)
        print(f"Cleaned text length: {len(cleaned_text)} characters")
        print(f"\nCleaned text preview:\n{cleaned_text[:200]}...\n")
        
        # Generate audio
        print("Generating audio...")
        audio_bytes = generator.generate_audio(cleaned_text)
        print(f"? Audio generated! Size: {len(audio_bytes):,} bytes ({len(audio_bytes)/1024:.1f} KB)")
        
        # Save to file for testing
        output_file = "test_audio.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        print(f"? Audio saved to: {output_file}")
        
        # Test base64 encoding
        audio_base64 = generator.generate_audio_base64(cleaned_text)
        print(f"? Base64 encoded length: {len(audio_base64):,} characters")
        print()
        print("?? Play the audio to verify authentic Thai pronunciation:")
        print(f"   ffplay -autoexit {output_file}")
        
        return True
        
    except Exception as e:
        print(f"? Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_audio_generator()
