# Audio Generation Feature

## Overview

The DR Ticker Report now includes audio generation using **Botnoi Voice API** for authentic Thai pronunciation. This allows users who prefer listening to receive audio versions of the Thai language reports with native Thai accent.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

No additional packages needed - uses standard `requests` library.

### 2. Configure Environment Variables

Add your Botnoi API key and voice ID to your environment:

```bash
export BOTNOI_API_KEY="your_api_key_here"
export BOTNOI_VOICE_ID="voice_id_here"
```

### 3. Get Botnoi API Credentials

1. Sign up at [Botnoi Voice](https://botnoigroup.com/botnoivoice)
2. Get your API key from the dashboard
3. Get a voice ID from available Thai voices
4. Add them to your environment variables or Doppler secrets

**API Documentation:** https://botnoigroup.com/botnoivoice/doc/api-user-guide

### 4. Get Voice ID

Check Botnoi dashboard or API documentation for available Thai voices. The API endpoint is:
- `/openapi/v1/generate_audio_v2`

You'll need to provide a `voiceId` parameter when generating audio.

## Usage

### Automatic Generation

Audio is automatically generated after the report is created. The audio is included in the API response:

```python
import requests

response = requests.get(
    "https://your-api-gateway-url/analyze",
    params={"ticker": "DBS19"}
)

data = response.json()
audio_base64 = data.get("audio_base64", "")

# Decode and save audio
if audio_base64:
    import base64
    audio_bytes = base64.b64decode(audio_base64)
    with open("report.mp3", "wb") as f:
        f.write(audio_bytes)
```

### Testing Locally

Test the audio generator directly:

```bash
doppler run --project rag-chatbot-worktree --config dev_personal -- python test_botnoi.py
```

Or test the audio generator module:

```bash
python src/audio_generator.py
```

This will:
1. Test text cleaning (removes markdown, emojis)
2. Generate audio from sample Thai text
3. Save `test_audio.mp3` for playback

## Features

### Text Cleaning

The audio generator automatically cleans the report text for better TTS quality:

- Removes markdown formatting (`**bold**`, `# headers`)
- Removes emojis
- Converts markdown links to readable text
- Removes reference numbers `[1]`, `[2]`
- Normalizes spacing and newlines

### Voice Settings

Default settings optimized for financial content:

- **Speed**: 1.0 (normal speed, can be adjusted 0.5-2.0)
- **Voice**: Native Thai voices from Botnoi (authentic pronunciation)

### API

Uses Botnoi Voice API endpoint `/openapi/v1/generate_audio_v2` which provides:
- Native Thai language support
- Authentic Thai pronunciation
- Professional voices optimized for Thai content

## API Response Format

The API response now includes `audio_base64`:

```json
{
  "ticker": "DBS19",
  "report": "📖 เรื่องราวของหุ้นตัวนี้...",
  "audio_base64": "UklGRiQAAABXQVZFZm10...",
  "chart_base64": "...",
  ...
}
```

The audio is base64-encoded MP3 format. Decode it to get the actual audio file.

## Error Handling

- If Botnoi API key is not set, audio generation is skipped gracefully
- If audio generation fails, the report is still returned (audio is optional)
- Error messages are logged but don't break the pipeline

## Cost Considerations

Check Botnoi Voice pricing at: https://botnoigroup.com/botnoivoice

Typical report length: ~500-2000 characters

## Performance

- Audio generation adds ~2-5 seconds to total response time
- Audio file size: ~50-200 KB per report (depending on length)
- Base64 encoding increases size by ~33%

## Troubleshooting

### Audio not generating

1. Check if Doppler is injecting the variables:
   ```bash
   doppler run --project rag-chatbot-worktree --config dev_personal --command env | grep BOTNOI
   ```

2. Or check environment variables directly:
   ```bash
   echo $BOTNOI_API_KEY
   echo $BOTNOI_VOICE_ID
   ```

3. Verify the keys are set in Doppler:
   ```bash
   doppler secrets get BOTNOI_API_KEY \
     --project rag-chatbot-worktree \
     --config dev_personal
   doppler secrets get BOTNOI_VOICE_ID \
     --project rag-chatbot-worktree \
     --config dev_personal
   ```

4. Check logs for error messages:
   ```
   ⚠️  Audio generation failed: ...
   ```

5. Verify API credentials are valid:
   ```bash
   doppler run --project rag-chatbot-worktree --config dev_personal -- python test_botnoi.py
   ```

### Audio quality issues

1. Adjust speech speed in `src/agent.py`:
   ```python
   audio_base64 = self.audio_generator.generate_audio_base64(
       cleaned_text,
       speed=0.9,  # Slower for clearer pronunciation
       # or
       speed=1.1,  # Faster for quicker delivery
   )
   ```

2. Try different voice IDs:
   ```python
   generator = AudioGenerator(voice_id="your_voice_id")
   ```

### Thai language pronunciation

Botnoi Voice provides **authentic Thai pronunciation** with native Thai voices. This is much better than multilingual models that may have accents.

1. **Botnoi voices are Thai-native:**
   All Botnoi voices are optimized for Thai language, so pronunciation should be authentic.

2. **Adjust speed if needed:**
   If speech is too fast or slow, adjust the speed parameter (0.5-2.0).

3. **Check voice ID:**
   Make sure you're using a Thai voice ID from Botnoi. Check the Botnoi dashboard for available voices.

### Rate limiting

If you hit rate limits:
- Implement caching (same report = same audio)
- Add delays between requests
- Upgrade ElevenLabs plan

## Integration Example

### Web Frontend

```javascript
// Fetch report with audio
const response = await fetch('/api/analyze?ticker=DBS19');
const data = await response.json();

// Play audio
if (data.audio_base64) {
  const audioBytes = atob(data.audio_base64);
  const audioBlob = new Blob(
    [new Uint8Array([...audioBytes].map(c => c.charCodeAt(0)))],
    { type: 'audio/mpeg' }
  );
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  audio.play();
}
```

### Python Client

```python
import requests
import base64
from io import BytesIO
from playsound import playsound

response = requests.get(
    "https://api.example.com/analyze",
    params={"ticker": "DBS19"}
)

data = response.json()
if data.get("audio_base64"):
    audio_bytes = base64.b64decode(data["audio_base64"])
    
    # Save to file
    with open("report.mp3", "wb") as f:
        f.write(audio_bytes)
    
    # Play audio
    playsound("report.mp3")
```

## Future Enhancements

- [ ] Voice selection via API parameter
- [ ] Audio caching (same report = same audio)
- [ ] Streaming audio for long reports
- [ ] Multiple language support
- [ ] Custom voice cloning for brand consistency
