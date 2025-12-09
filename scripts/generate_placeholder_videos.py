#!/usr/bin/env python3
"""
Generate placeholder videos for video showcase examples.
Requires FFmpeg to be installed on the system.
"""

import os
import subprocess
import sys
from pathlib import Path

# Video configurations
VIDEOS = [
    # Portrait
    {
        'filename': 'portrait_1.mp4',
        'color': '#667eea',
        'text': 'Portrait T2V\\nCinematic',
        'duration': 5
    },
    {
        'filename': 'portrait_2.mp4',
        'color': '#764ba2',
        'text': 'Portrait I2V\\nAnimate Photo',
        'duration': 5
    },
    # Fashion
    {
        'filename': 'fashion_1.mp4',
        'color': '#f093fb',
        'text': 'Fashion T2V\\nRunway',
        'duration': 5
    },
    {
        'filename': 'fashion_2.mp4',
        'color': '#f5576c',
        'text': 'Fashion I2V\\nModel Motion',
        'duration': 5
    },
    # Nature
    {
        'filename': 'nature_1.mp4',
        'color': '#4facfe',
        'text': 'Nature T2V\\nLandscape',
        'duration': 5
    },
    {
        'filename': 'nature_2.mp4',
        'color': '#00f2fe',
        'text': 'Nature I2V\\nClouds Moving',
        'duration': 5
    },
    # Fantasy
    {
        'filename': 'fantasy_1.mp4',
        'color': '#a8edea',
        'text': 'Fantasy T2V\\nMagical Scene',
        'duration': 5
    },
    {
        'filename': 'fantasy_2.mp4',
        'color': '#fed6e3',
        'text': 'Fantasy I2V\\nLight Particles',
        'duration': 5
    },
    # Art
    {
        'filename': 'art_1.mp4',
        'color': '#fa709a',
        'text': 'Art T2V\\nAbstract',
        'duration': 5
    },
    {
        'filename': 'art_2.mp4',
        'color': '#fee140',
        'text': 'Art I2V\\nCreative Motion',
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
            f"fontsize=80:"
            f"fontcolor=white:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"shadowcolor=black:"
            f"shadowx=3:"
            f"shadowy=3"
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

    print(f"Generating placeholder videos in: {output_dir}")
    print(f"Total videos to create: {len(VIDEOS)}\n")

    # Generate each video
    success_count = 0
    for video_config in VIDEOS:
        output_path = output_dir / video_config['filename']

        if create_video(
            output_path=output_path,
            color=video_config['color'],
            text=video_config['text'],
            duration=video_config['duration']
        ):
            success_count += 1

    # Summary
    print(f"\n{'='*50}")
    print(f"Successfully created: {success_count}/{len(VIDEOS)} videos")
    print(f"Output directory: {output_dir}")
    print(f"{'='*50}")

    if success_count == len(VIDEOS):
        print("\n✓ All placeholder videos created successfully!")
        return 0
    else:
        print(f"\n⚠ Warning: {len(VIDEOS) - success_count} videos failed to create")
        return 1

if __name__ == '__main__':
    sys.exit(main())
