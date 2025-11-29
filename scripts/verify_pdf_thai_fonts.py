#!/usr/bin/env python3
"""
Test script to verify Thai fonts work correctly in PDF generation locally.
This generates a simple PDF with Thai text to check for tofu characters.
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.formatters.pdf_generator import PDFReportGenerator
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def test_thai_fonts():
    """Test Thai font rendering in PDF"""
    print("=" * 80)
    print("THAI FONT TEST - PDF Generation")
    print("=" * 80)
    print()

    # Initialize PDF generator
    print("🔄 Initializing PDF generator...")
    pdf_gen = PDFReportGenerator(use_thai_font=True)
    print(f"✅ PDF generator initialized")
    print(f"   Thai font loaded: {pdf_gen.thai_font}")
    print()

    # Test Thai text samples
    thai_samples = [
        "สวัสดีครับ",  # Hello
        "การวิเคราะห์หุ้น",  # Stock analysis
        "ราคาหุ้น",  # Stock price
        "📖 **เรื่องราวของหุ้นตัวนี้**",  # Section header
        "💡 **สิ่งที่คุณต้องรู้**",  # What you need to know
        "🎯 **ควรทำอะไรตอนนี้?**",  # What should you do now?
        "⚠️ **ระวังอะไร?**",  # What to watch out for?
        "บริษัท Apple Inc. มีราคาหุ้นที่ $150.00 และมี P/E Ratio เท่ากับ 25.5",
        "RSI อยู่ที่ 65.5 ซึ่งอยู่ในระดับปกติ",
        "MACD แสดงสัญญาณ Bullish และมีแนวโน้มที่ดี",
    ]

    # Create a simple test PDF
    print("📄 Creating test PDF with Thai text...")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate
    from io import BytesIO

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"test_thai_fonts_{timestamp}.pdf"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    story = []

    # Title
    story.append(Paragraph(
        "ทดสอบฟอนต์ไทย (Thai Font Test)",
        pdf_gen.styles['CustomTitle']
    ))
    story.append(Spacer(1, 20))

    # Test each Thai sample
    story.append(Paragraph(
        "ตัวอย่างข้อความไทย (Thai Text Samples):",
        pdf_gen.styles['SectionHeader']
    ))
    story.append(Spacer(1, 10))

    for i, thai_text in enumerate(thai_samples, 1):
        story.append(Paragraph(
            f"{i}. {thai_text}",
            pdf_gen.styles['ThaiBody']
        ))
        story.append(Spacer(1, 8))

    # Add font info
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Font Information:",
        pdf_gen.styles['SectionHeader']
    ))
    story.append(Paragraph(
        f"Active Thai Font: <b>{pdf_gen.thai_font}</b>",
        pdf_gen.styles['ThaiBody']
    ))
    story.append(Paragraph(
        f"Bold Font: <b>{'Sarabun-Bold' if pdf_gen.thai_font == 'Sarabun' else 'Helvetica-Bold'}</b>",
        pdf_gen.styles['ThaiBody']
    ))

    # Build PDF
    doc.build(story)

    # Save to file
    pdf_bytes = buffer.getvalue()
    buffer.close()

    with open(output_filename, 'wb') as f:
        f.write(pdf_bytes)

    print(f"✅ Test PDF created: {output_filename}")
    print(f"   Size: {len(pdf_bytes):,} bytes ({len(pdf_bytes)/1024:.1f} KB)")
    print()
    print("📋 PDF Contents:")
    print("   - Title with Thai text")
    print("   - 10 Thai text samples")
    print("   - Font information")
    print()
    print("🔍 Please open the PDF and check:")
    print("   1. All Thai characters display correctly (no □ or ?)")
    print("   2. Font looks smooth and readable")
    print("   3. Emojis display correctly")
    print()
    print(f"💡 Open with: xdg-open {output_filename} (Linux) or open {output_filename} (Mac)")
    print()

    # Verify font files exist
    print("=" * 80)
    print("FONT FILE VERIFICATION")
    print("=" * 80)
    
    font_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    sarabun_regular = os.path.join(font_dir, 'Sarabun-Regular.ttf')
    sarabun_bold = os.path.join(font_dir, 'Sarabun-Bold.ttf')

    print(f"Font directory: {font_dir}")
    print(f"  Sarabun-Regular.ttf: {'✅ EXISTS' if os.path.exists(sarabun_regular) else '❌ MISSING'}")
    if os.path.exists(sarabun_regular):
        size = os.path.getsize(sarabun_regular)
        print(f"    Size: {size:,} bytes ({size/1024:.1f} KB)")
    
    print(f"  Sarabun-Bold.ttf: {'✅ EXISTS' if os.path.exists(sarabun_bold) else '❌ MISSING'}")
    if os.path.exists(sarabun_bold):
        size = os.path.getsize(sarabun_bold)
        print(f"    Size: {size:,} bytes ({size/1024:.1f} KB)")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print("✅ If Thai characters display correctly in the PDF, fonts are working!")
    print("❌ If you see □ or ? characters, fonts are not loading correctly.")
    print()

    return output_filename


if __name__ == "__main__":
    test_thai_fonts()
