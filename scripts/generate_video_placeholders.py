#!/usr/bin/env python3
"""
Generate placeholder videos for I2V and T2V examples using local FFmpeg.
"""

import subprocess
import sys
from pathlib import Path

def get_ffmpeg_path():
    """Get path to local FFmpeg."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    ffmpeg_path = project_root / 'static' / 'ffmpeg-8.0' / 'bin' / 'ffmpeg.exe'

    if ffmpeg_path.exists():
        return str(ffmpeg_path)
    return None

def create_placeholder_video(output_path, text, color, duration=5):
    """Create a simple placeholder video with text and color."""
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print(f"Error: FFmpeg not found")
        return False

    cmd = [
        ffmpeg_path,
        '-y',
        '-f', 'lavfi',
        '-i', f'color=c={color}:s=1280x720:d={duration}',
        '-vf', f"drawtext=text='{text}':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=10",
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        str(output_path)
    ]

    try:
        print(f"Creating {output_path.name}...", end=' ')
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("✓")
        return True
    except subprocess.CalledProcessError:
        print("✗")
        return False

def main():
    """Generate all placeholder videos."""
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("Error: FFmpeg not found at static/ffmpeg-8.0/bin/ffmpeg.exe")
        sys.exit(1)

    print(f"Using FFmpeg: {ffmpeg_path}\n")

    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / 'static' / 'video' / 'examples'
    output_dir.mkdir(parents=True, exist_ok=True)

    # I2V videos
    i2v_videos = [
        ('i2v_portrait_1.mp4', 'I2V Portrait 1', '667eea'),
        ('i2v_portrait_2.mp4', 'I2V Portrait 2', '764ba2'),
        ('i2v_emotions_1.mp4', 'I2V Emotions 1', 'f093fb'),
        ('i2v_emotions_2.mp4', 'I2V Emotions 2', 'f5576c'),
        ('i2v_hair_1.mp4', 'I2V Hair 1', '4facfe'),
        ('i2v_hair_2.mp4', 'I2V Hair 2', '00f2fe'),
        ('i2v_eyes_1.mp4', 'I2V Eyes 1', 'a8edea'),
        ('i2v_eyes_2.mp4', 'I2V Eyes 2', 'fed6e3'),
        ('i2v_fabric_1.mp4', 'I2V Fabric 1', 'fa709a'),
        ('i2v_fabric_2.mp4', 'I2V Fabric 2', 'fee140'),
    ]

    # T2V videos
    t2v_videos = [
        ('t2v_cinematic_1.mp4', 'T2V Cinematic 1', '667eea'),
        ('t2v_cinematic_2.mp4', 'T2V Cinematic 2', '764ba2'),
        ('t2v_fashion_1.mp4', 'T2V Fashion 1', 'f093fb'),
        ('t2v_fashion_2.mp4', 'T2V Fashion 2', 'f5576c'),
        ('t2v_architecture_1.mp4', 'T2V Architecture 1', '4facfe'),
        ('t2v_architecture_2.mp4', 'T2V Architecture 2', '00f2fe'),
        ('t2v_nature_1.mp4', 'T2V Nature 1', '43e97b'),
        ('t2v_nature_2.mp4', 'T2V Nature 2', '38f9d7'),
        ('t2v_fantasy_1.mp4', 'T2V Fantasy 1', 'a8edea'),
        ('t2v_fantasy_2.mp4', 'T2V Fantasy 2', 'fed6e3'),
    ]

    print("Creating I2V placeholder videos...")
    print("-" * 50)
    for filename, text, color in i2v_videos:
        create_placeholder_video(output_dir / filename, text, color)

    print("\nCreating T2V placeholder videos...")
    print("-" * 50)
    for filename, text, color in t2v_videos:
        create_placeholder_video(output_dir / filename, text, color)

    print("\n✅ All placeholder videos created!")
    print(f"Location: {output_dir}")

if __name__ == '__main__':
    main()
