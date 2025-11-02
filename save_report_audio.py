#!/usr/bin/env python3
"""
Save audio file from ticker report generation
Usage: doppler run --project rag-chatbot-worktree --config dev_personal -- python save_report_audio.py <ticker>
"""

import os
import sys
import base64
from src.agent import TickerAnalysisAgent

# Set speaker ID
os.environ['BOTNOI_VOICE_ID'] = '8'

def save_report_audio(ticker):
    """Generate report and save audio file"""
    print("=" * 80)
    print(f"Generating report with audio for: {ticker}")
    print("=" * 80)
    print()
    
    try:
        agent = TickerAnalysisAgent()
        
        state = {'ticker': ticker, 'error': None}
        result = agent.graph.invoke(state)
        
        if 'report' in result and result['report']:
            report = result['report']
            print(f"✅ Report generated ({len(report)} characters)")
            print()
            
            # Save report text
            report_file = f"report_{ticker}_text.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"✅ Report text saved to: {report_file}")
            
            # Save audio if available
            if 'audio_base64' in result and result['audio_base64']:
                audio_bytes = base64.b64decode(result['audio_base64'])
                audio_file = f"report_{ticker}_audio.mp3"
                with open(audio_file, 'wb') as f:
                    f.write(audio_bytes)
                print(f"✅ Audio saved to: {audio_file}")
                print(f"   Size: {len(audio_bytes):,} bytes ({len(audio_bytes)/1024:.1f} KB)")
                return audio_file
            else:
                print("⚠️  No audio generated (check Botnoi API credits)")
                return None
        else:
            print("❌ Report generation failed")
            if 'error' in result:
                print(f"Error: {result['error']}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python save_report_audio.py <ticker>")
        print("Example: python save_report_audio.py DBS19")
        sys.exit(1)
    
    ticker = sys.argv[1]
    audio_file = save_report_audio(ticker)
    
    if audio_file:
        print()
        print(f"✅ Success! Audio file saved: {audio_file}")
        print(f"   Play with: ffplay -autoexit {audio_file}")
    else:
        sys.exit(1)
