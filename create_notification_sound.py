"""
Create a lunar/moon notification sound using pydub
This creates a pleasant, ethereal notification sound
"""
import os
import sys

try:
    from pydub import AudioSegment
    from pydub.generators import Sine
except ImportError:
    print("Installing required package: pydub")
    os.system(f"{sys.executable} -m pip install pydub")
    from pydub import AudioSegment
    from pydub.generators import Sine

def create_lunar_notification_sound():
    """Create a pleasant lunar/moon notification sound"""

    # Create two sine wave tones for a pleasant chime
    # First tone: 880 Hz (A5)
    tone1 = Sine(880).to_audio_segment(duration=400)

    # Second tone: 1320 Hz (E6) - a perfect fifth above
    tone2 = Sine(1320).to_audio_segment(duration=600)

    # Apply fade in and fade out for smooth sound
    tone1 = tone1.fade_in(30).fade_out(200)
    tone2 = tone2.fade_in(50).fade_out(300)

    # Reduce volume to make it pleasant
    tone1 = tone1 - 6  # Reduce by 6dB
    tone2 = tone2 - 8  # Reduce by 8dB

    # Overlay the second tone slightly after the first
    combined = tone1.overlay(tone2, position=50)

    # Add a subtle reverb effect by overlaying delayed, quieter versions
    reverb1 = combined - 15  # Much quieter
    reverb2 = combined - 20  # Even quieter

    final = combined.overlay(reverb1, position=100).overlay(reverb2, position=200)

    # Normalize to prevent clipping
    final = final.normalize()

    # Export as MP3
    output_path = os.path.join('static', 'sounds', 'notification-chime.mp3')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    final.export(output_path, format='mp3', bitrate='128k')
    print(f"✓ Created notification sound: {output_path}")
    print(f"  Duration: {len(final)}ms")
    print(f"  Format: MP3")

    return output_path

if __name__ == '__main__':
    create_lunar_notification_sound()
