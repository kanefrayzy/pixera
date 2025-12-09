#!/usr/bin/env python3
"""
Optimize video examples for web performance.
Compresses videos to minimal size while maintaining quality.
"""

import os
import subprocess
import sys
from pathlib import Path

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    # Try local ffmpeg first
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    local_ffmpeg = project_root / 'static' / 'ffmpeg-8.0' / 'bin' / 'ffmpeg.exe'

    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    # Try system ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              check=True)
        return 'ffmpeg'
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_video_info(video_path):
    """Get video duration and size."""
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration,size',
            '-of', 'default=noprint_wrappers=1',
            str(video_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        info = {}
        for line in result.stdout.split('\n'):
            if '=' in line:
                key, value = line.split('=')
                info[key] = value

        return info
    except:
        return {}

def optimize_video(input_path, output_path, target_size_kb=150, ffmpeg_path='ffmpeg'):
    """
    Optimize video for web with aggressive compression.

    Args:
        input_path: Source video file
        output_path: Optimized output file
        target_size_kb: Target file size in KB (default: 150KB)
    """
    # Get original video info
    info = get_video_info(input_path)
    duration = float(info.get('duration', 5))

    # Calculate target bitrate (in kbps)
    # Formula: (target_size_kb * 8) / duration
    target_bitrate = int((target_size_kb * 8) / duration)

    # Ensure minimum bitrate
    video_bitrate = max(target_bitrate - 32, 50)  # Reserve 32k for audio
    audio_bitrate = 32

    cmd = [
        ffmpeg_path,
        '-y',  # Overwrite output
        '-i', str(input_path),

        # Video settings - aggressive compression
        '-c:v', 'libx264',
        '-preset', 'veryslow',  # Best compression
        '-crf', '28',  # Higher CRF = more compression
        '-b:v', f'{video_bitrate}k',
        '-maxrate', f'{video_bitrate}k',
        '-bufsize', f'{video_bitrate * 2}k',

        # Resolution - scale down for web
        '-vf', 'scale=640:-2',  # 640px width, maintain aspect ratio

        # Frame rate
        '-r', '24',  # 24 fps for smaller size

        # Audio settings - minimal
        '-c:a', 'aac',
        '-b:a', f'{audio_bitrate}k',
        '-ac', '1',  # Mono audio

        # Format settings
        '-movflags', '+faststart',  # Enable streaming
        '-pix_fmt', 'yuv420p',

        # Output
        str(output_path)
    ]

    try:
        print(f"Optimizing {input_path.name}...", end=' ')
        subprocess.run(cmd,
                      stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,
                      check=True)

        # Get output size
        output_size = output_path.stat().st_size / 1024  # KB
        print(f"✓ ({output_size:.1f} KB)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error")
        return False

def create_poster_image(video_path, poster_path, ffmpeg_path='ffmpeg'):
    """Create poster image from first frame of video."""
    cmd = [
        ffmpeg_path,
        '-y',
        '-i', str(video_path),
        '-vframes', '1',
        '-vf', 'scale=640:-2',
        '-q:v', '5',  # Quality 5 (lower = better)
        str(poster_path)
    ]

    try:
        subprocess.run(cmd,
                      stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,
                      check=True)
        return True
    except:
        return False

def main():
    """Main optimization function."""
    # Check FFmpeg
    ffmpeg_path = check_ffmpeg()
    if not ffmpeg_path:
        print("Error: FFmpeg is not installed or not in PATH.")
        print("Please install FFmpeg: https://ffmpeg.org/download.html")
        sys.exit(1)

    print(f"Using FFmpeg: {ffmpeg_path}")

    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    input_dir = project_root / 'static' / 'video' / 'examples'
    output_dir = project_root / 'static' / 'video' / 'examples' / 'optimized'
    posters_dir = project_root / 'static' / 'video' / 'examples' / 'posters'

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    posters_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("Video Optimization for Web Performance")
    print("="*70)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Target: ~150KB per video, 640px width, 24fps")
    print("="*70)
    print()

    # Find all video files
    video_files = list(input_dir.glob('*.mp4'))

    if not video_files:
        print("No video files found in input directory!")
        sys.exit(1)

    print(f"Found {len(video_files)} videos to optimize\n")

    # Optimize each video
    success_count = 0
    total_original_size = 0
    total_optimized_size = 0

    for video_file in sorted(video_files):
        # Skip if already in optimized folder
        if 'optimized' in str(video_file):
            continue

        output_file = output_dir / video_file.name
        poster_file = posters_dir / f"{video_file.stem}.jpg"

        # Get original size
        original_size = video_file.stat().st_size / 1024  # KB
        total_original_size += original_size

        # Optimize video
        if optimize_video(video_file, output_file, target_size_kb=150, ffmpeg_path=ffmpeg_path):
            success_count += 1
            optimized_size = output_file.stat().st_size / 1024  # KB
            total_optimized_size += optimized_size

            # Create poster image
            print(f"  Creating poster...", end=' ')
            if create_poster_image(output_file, poster_file, ffmpeg_path=ffmpeg_path):
                poster_size = poster_file.stat().st_size / 1024
                print(f"✓ ({poster_size:.1f} KB)")
            else:
                print("✗")

    # Summary
    print()
    print("="*70)
    print("Optimization Summary")
    print("="*70)
    print(f"Videos processed: {success_count}/{len(video_files)}")
    print(f"Original total size: {total_original_size:.1f} KB ({total_original_size/1024:.2f} MB)")
    print(f"Optimized total size: {total_optimized_size:.1f} KB ({total_optimized_size/1024:.2f} MB)")

    if total_original_size > 0:
        reduction = ((total_original_size - total_optimized_size) / total_original_size) * 100
        print(f"Size reduction: {reduction:.1f}%")

    print(f"Average size per video: {total_optimized_size/success_count:.1f} KB")
    print()
    print(f"Optimized videos: {output_dir}")
    print(f"Poster images: {posters_dir}")
    print("="*70)

    if success_count == len(video_files):
        print("\n✅ All videos optimized successfully!")
        print("\n📝 Next steps:")
        print("1. Replace original videos with optimized versions")
        print("2. Update video_prompts.html to use poster images")
        print("3. Test page load performance")
        return 0
    else:
        print(f"\n⚠️  Warning: {len(video_files) - success_count} videos failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
