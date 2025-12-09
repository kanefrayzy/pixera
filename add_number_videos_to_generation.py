"""
Add number_videos parameter to video-generation.js
"""

# Read the file
with open('static/js/video-generation.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the seed parameter section and add number_videos after it
old_code = """    const seed = document.getElementById('video-seed')?.value.trim();
    if (seed) formData.append('seed', seed);"""

new_code = """    const seed = document.getElementById('video-seed')?.value.trim();
    if (seed) formData.append('seed', seed);

    // Number of videos to generate
    const numberVideos = document.getElementById('video-quantity')?.value || '1';
    formData.append('number_videos', numberVideos);"""

if old_code in content:
    content = content.replace(old_code, new_code)

    # Write back
    with open('static/js/video-generation.js', 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Successfully added number_videos parameter to video-generation.js")
else:
    print("❌ Could not find the code to replace")
    print("Please add manually after the seed parameter:")
    print("""
    // Number of videos to generate
    const numberVideos = document.getElementById('video-quantity')?.value || '1';
    formData.append('number_videos', numberVideos);
    """)
