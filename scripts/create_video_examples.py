#!/usr/bin/env python3
"""
Create placeholder video examples for I2V and T2V modes.
Generates colored video files with text labels using FFmpeg.
"""

import os
import subprocess
import sys
from pathlib import Path

# Video configurations for I2V (Animate Photo)
I2V_VIDEOS = [
    # Portrait category
    {
        'filename': 'i2v_portrait_1.mp4',
        'color': '#667eea',
        'text': 'I2V\\nПортрет\\nДвижение волос',
        'duration': 5
    },
    {
        'filename': 'i2v_portrait_2.mp4',
        'color': '#764ba2',
        'text': 'I2V\\nПортрет\\nМоргание',
        'duration': 5
    },
    # Emotions category
    {
        'filename': 'i2v_emotions_1.mp4',
        'color': '#f093fb',
        'text': 'I2V\\nЭмоции\\nУлыбка',
        'duration': 5
    },
    {
        'filename': 'i2v_emotions_2.mp4',
        'color': '#f5576c',
        'text': 'I2V\\nЭмоции\\nВзгляд',
        'duration': 5
    },
    # Movement category
    {
        'filename': 'i2v_movement_1.mp4',
        'color': '#4facfe',
        'text': 'I2V\\nДвижение\\nВолосы на ветру',
        'duration': 5
    },
    {
        'filename': 'i2v_movement_2.mp4',
        'color': '#00f2fe',
        'text': 'I2V\\nДвижение\\nПоворот головы',
        'duration': 5
    },
    # Effects category
    {
        'filename': 'i2v_effects_1.mp4',
        'color': '#a8edea',
        'text': 'I2V\\nЭффекты\\nЧастицы света',
        'duration': 5
    },
    {
        'filename': 'i2v_effects_2.mp4',
        'color': '#fed6e3',
        'text': 'I2V\\nЭффекты\\nТуман',
        'duration': 5
    },
    # Nature category
    {
        'filename': 'i2v_nature_1.mp4',
        'color': '#fa709a',
        'text': 'I2V\\nПрирода\\nОблака',
        'duration': 5
    },
    {
        'filename': 'i2v_nature_2.mp4',
        'color': '#fee140',
        'text': 'I2V\\nПрирода\\nВолны',
        'duration': 5
    },
]

# Video configurations for T2V (Create Video)
T2V_VIDEOS = [
    # Cinematic category
    {
        'filename': 't2v_cinematic_1.mp4',
        'color': '#667eea',
        'text': 'T2V\\nКинематограф\\nПортрет',
        'duration': 5
    },
    {
        'filename': 't2v_cinematic_2.mp4',
        'color': '#764ba2',
        'text': 'T2V\\nКинематограф\\nДрама',
        'duration': 5
    },
    # Fashion category
    {
        'filename': 't2v_fashion_1.mp4',
        'color': '#f093fb',
        'text': 'T2V\\nМода\\nСъемка',
        'duration': 5
    },
    {
        'filename': 't2v_fashion_2.mp4',
        'color': '#f5576c',
        'text': 'T2V\\nМода\\nПодиум',
        'duration': 5
    },
    # Nature category
    {
        'filename': 't2v_nature_1.mp4',
        'color': '#4facfe',
        'text': 'T2V\\nПрирода\\nПейзаж',
        'duration': 5
    },
    {
        'filename': 't2v_nature_2.mp4',
        'color': '#00f2fe',
        'text': 'T2V\\nПрирода\\nЛес',
        'duration': 5
    },
    # Fantasy category
    {
        'filename': 't2v_fantasy_1.mp4',
        'color': '#a8edea',
        'text': 'T2V\\nФэнтези\\nМагия',
        'duration': 5
    },
    {
        'filename': 't2v_fantasy_2.mp4',
        'color': '#fed6e3',
        'text': 'T2V\\nФэнтези\\nМистика',
        'duration': 5
    },
    # Abstract category
    {
        'filename': 't2v_abstract_1.mp4',
        'color': '#fa709a',
        'text': 'T2V\\nАбстракция\\nКомпозиция',
        'duration': 5
    },
    {
        'filename': 't2v_abstract_2.mp4',
        'color': '#fee140',
        'text': 'T2V\\nАбстракция\\nАрт',
        'duration': 5
    },
]

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        subprocess.run(['ffmpeg', '-version'],
                      stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def create_video(output_path, color, text, duration=5, resolution='1920x1080'):
    """
    Create a placeholder video with colored background and text.

    Args:
        output_path: Path where video will be saved
        color: Hex color code (e.g., '#667eea')
        text: Text to display on video
        duration: Video duration in seconds
        resolution: Video resolution (default: 1920x1080)
    """
    # Convert hex color to RGB for FFmpeg
    color = color.lstrip('#')

    # FFmpeg command to create video with gradient and text
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output file
        '-f', 'lavfi',
        '-i', f'color=c=0x{color}:s={resolution}:d={duration}',
        '-vf', (
            f"drawtext=text='{text}':"
            f"fontsize=70:"
            f"fontcolor=white:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"shadowcolor=black:"
            f"shadowx=4:"
            f"shadowy=4:"
            f"box=1:"
            f"boxcolor=black@0.4:"
            f"boxborderw=20"
        ),
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        str(output_path)
    ]

    try:
        print(f"Creating {output_path.name}...", end=' ')
        subprocess.run(cmd,
                      stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,
                      check=True)
        print("✓")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Main function to generate all placeholder videos."""
    # Check if FFmpeg is installed
    if not check_ffmpeg():
        print("Error: FFmpeg is not installed or not in PATH.")
        print("Please install FFmpeg: https://ffmpeg.org/download.html")
        sys.exit(1)

    # Determine project root (assuming script is in scripts/ directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Create output directory
    output_dir = project_root / 'static' / 'video' / 'examples'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("Creating Video Examples for I2V and T2V")
    print("="*60)
    print(f"Output directory: {output_dir}\n")

    # Generate I2V videos
    print("📹 Creating I2V (Animate Photo) videos...")
    print("-"*60)
    i2v_success = 0
    for video_config in I2V_VIDEOS:
        output_path = output_dir / video_config['filename']
        if create_video(
            output_path=output_path,
            color=video_config['color'],
            text=video_config['text'],
            duration=video_config['duration']
        ):
            i2v_success += 1

    print()

    # Generate T2V videos
    print("🎬 Creating T2V (Create Video) videos...")
    print("-"*60)
    t2v_success = 0
    for video_config in T2V_VIDEOS:
        output_path = output_dir / video_config['filename']
        if create_video(
            output_path=output_path,
            color=video_config['color'],
            text=video_config['text'],
            duration=video_config['duration']
        ):
            t2v_success += 1

    # Summary
    print()
    print("="*60)
    print("Summary")
    print("="*60)
    print(f"I2V videos created: {i2v_success}/{len(I2V_VIDEOS)}")
    print(f"T2V videos created: {t2v_success}/{len(T2V_VIDEOS)}")
    print(f"Total: {i2v_success + t2v_success}/{len(I2V_VIDEOS) + len(T2V_VIDEOS)}")
    print(f"Output directory: {output_dir}")
    print("="*60)

    total_expected = len(I2V_VIDEOS) + len(T2V_VIDEOS)
    total_created = i2v_success + t2v_success

    if total_created == total_expected:
        print("\n✅ All placeholder videos created successfully!")
        return 0
    else:
        print(f"\n⚠️  Warning: {total_expected - total_created} videos failed to create")
        return 1

if __name__ == '__main__':
    sys.exit(main())
