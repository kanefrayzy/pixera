"""Find image-model-card click handler"""

with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the click handler
marker = '.image-model-card'
pos = content.find(marker)

if pos > 0:
    # Find the addEventListener or onclick
    search_start = pos
    search_end = min(pos + 2000, len(content))
    section = content[search_start:search_end]

    print("Found .image-model-card at position:", pos)
    print("\nContext (next 1000 chars):")
    print(section[:1000])
else:
    print("Not found in JavaScript")

# Also search for querySelectorAll
qs_marker = "querySelectorAll('.image-model-card')"
qs_pos = content.find(qs_marker)
if qs_pos > 0:
    print("\n\n" + "="*80)
    print("Found querySelectorAll at position:", qs_pos)
    print("\nContext:")
    print(content[qs_pos:qs_pos+1200])
