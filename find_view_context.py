"""Find how context is created in new() view"""

with open('generate/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find function new
start = content.find('def new(request')
if start < 0:
    print("Function not found")
    exit(1)

# Find next function or end of file
next_def = content.find('\ndef ', start + 10)
if next_def < 0:
    next_def = len(content)

# Get the function body
func_body = content[start:next_def]

# Find return render
render_pos = func_body.find('return render')
if render_pos > 0:
    print("Found return render at position:", render_pos)
    print("\nContext around return render:")
    print(func_body[max(0, render_pos-500):render_pos+200])
else:
    print("return render not found")
    print("\nLast 1000 chars of function:")
    print("\nLast 1000 chars of function:")
    print(func_body[-1000:])
