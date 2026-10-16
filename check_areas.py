import json, os
for f in sorted(os.listdir('data/scenarios'))[:5]:
    try:
        with open('data/scenarios/' + f, encoding='utf-8') as fh:
            d = json.load(fh)
            areas = d.get('areas', {})
            for area_name in list(areas.keys())[:1]:
                area_data = areas[area_name]
                print(f'{f}/{area_name}:')
                print(f'  floor = {area_data.get("floor")}')
                pkeys = list(area_data.get("properties", {}).keys())
                print(f'  properties keys = {pkeys}')
                print(f'  properties = {area_data.get("properties", {})}')
                print()
    except Exception as e:
        print(f'Error with {f}: {e}')