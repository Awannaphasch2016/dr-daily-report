# Utilities Module
# Quick development tasks and utilities

# Quick test for a ticker
quick-test TICKER:
    @echo "⚡ Quick test for {{TICKER}}..."
    python ../test_direct.py {{TICKER}}

# Test audio generation
test-audio:
    @echo "🔊 Testing audio generation..."
    python ../test_audio.py

# Test botnoi integration
test-botnoi:
    @echo "🤖 Testing Botnoi integration..."
    python ../test_botnoi.py

# Show scores
scores:
    @echo "📊 Showing scores..."
    python ../show_scores.py
