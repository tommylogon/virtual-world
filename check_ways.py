import json, os
for f in sorted(os.listdir('data/scenarios'))[:3]:
    try:
        with open('data/scenarios/' + f, encoding='utf-8') as fh:
            d = json.load(fh)
            ways = d.get('ways', {})
            for way_name in list(ways.keys())[:1]:
                way_data = ways[way_name]
                print(f'{f}/{way_name}:')
                print(f'  kind = {way_data.get("kind")}')
                pkeys = list(way_data.get('properties', {}).keys())
                print(f'  properties keys = {pkeys}')
                print(f'  properties = {way_data.get("properties", {})}')
                print()
    except Exception as e:
        print(f'Error with {f}: {e}')