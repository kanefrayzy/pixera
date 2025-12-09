"""
Find where image model selection is handled in templates/generate/new.html
"""

with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Search for image model related code
searches = [
    'image-model-card',
    'data-model-id',
    'image_models',
    'selectImageModel',
    'imageModelId'
]

print("Searching for image model selection code...\n")

for search in searches:
    pos = content.find(search)
    if pos > 0:
        print(f"Found '{search}' at position {pos}")
        print("Context:")
        print(content[max(0, pos-150):pos+250])
        print("\n" + "="*80 + "\n")
