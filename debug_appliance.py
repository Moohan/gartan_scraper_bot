from parse_grid import parse_grid_html

with open('_cache/grid_07-08-2025.html', 'r', encoding='utf-8') as f:
    content = f.read()

result = parse_grid_html(content, '2025-08-07')
print('Appliance keys:', list(result['appliance_availability'].keys()))
if result['appliance_availability']:
    print('First few appliances:')
    for i, key in enumerate(list(result['appliance_availability'].keys())[:3]):
        print(f'  {key}')
