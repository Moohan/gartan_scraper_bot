with open('_cache/grid_07-08-2025.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the "Appliances" section
lines = content.split('\n')
appliances_start = None
for i, line in enumerate(lines):
    if 'Appliances' in line:
        appliances_start = i
        break

if appliances_start:
    # Print a few lines around the Appliances section
    start = max(0, appliances_start - 2)
    end = min(len(lines), appliances_start + 10)
    print("Appliances section:")
    for i in range(start, end):
        print(f"{i:3d}: {lines[i]}")
