import geojson
import json
import pandas
import requests

from collections import defaultdict

DATASET_URL = 'https://data.cityofnewyork.us/resource/rvih-nhyn.csv'

CATEGORIES = {
    'Arcade': [],
    'Covered': [],
    'Enclosed': [
        'Glass-Enclosed Urban Plaza Equivalent',
    ],
    'Lobby': [],
    'Outdoor': [
        'Landscaped Terrace',
        'Landscaped Terraces',
    ],
    'Park': [],
    'Passageway': [],
    'Plaza': [
        'Large Square',
        'Small Square',
    ],
}

TYPE_TO_CATEGORY = {i: k for k, v in CATEGORIES.items() for i in v}

PROTECTION = {
    'Outdoor': ['Outdoor', 'Park', 'Plaza'],
    'Indoor': ['Enclosed', 'Lobby'],
    'Covered': ['Arcade', 'Covered'],
    'Other': ['Passageway'],
}

CATEGORY_TO_PROTECTION = {i: k for k, v in PROTECTION.items() for i in v}


def get_data(force_cache_update=False):
    filename = 'data/pops.csv'

    if not force_cache_update:
        try:
            with open(filename) as infile:
                return pandas.read_csv(infile)
        except IOError:
            pass

    content = requests.get(DATASET_URL).content.decode('utf-8')
    with open(filename, 'w') as outfile:
        outfile.write(content)
    return pandas.read_csv(filename)


def get_categories_and_protections(public_space_types):
    categories = []
    for space_type in public_space_types:
        if space_type in TYPE_TO_CATEGORY:
            categories.append(TYPE_TO_CATEGORY[space_type])
        else:
            categories.extend([category for category in CATEGORIES if space_type in category])
    protections = [CATEGORY_TO_PROTECTION[category] for category in categories]
    return categories, protections


def to_geojson(df):
    for column in ['building_name', 'amenities_required', 'public_space_type']:
        df[column].fillna('', inplace=True)

    geojson_items = []
    detail_items = {}

    filters = {v.lower().replace(' ', '_'): v for v in ['Climate Control', 'Seating', 'Restrooms', 'Tables']}

    emoji = defaultdict(lambda: '', {
        'Climate Control': '🌡️',
        'Seating': '🪑',
        'Restrooms': '🚻',
    })

    def to_list(data_string):
        return [i.strip() for i in data_string.split(';') if i]

    for index, row in df.iterrows():
        row_id = row['pops_number']
        amenities = to_list(row['amenities_required'])
        public_space_type = to_list(row['public_space_type'])
        categories, protections = get_categories_and_protections(public_space_type)

        properties = {
            'id': row_id,
        }
        for k, v in filters.items():
            if v in amenities:
                properties[k] = True
        details = {
            'name': row['building_name'],
            'address': row['address_number'] + ' ' + row['street_name'].title(),
            'amenities': [emoji[a] + a for a in amenities],
            'public_space_type': public_space_type,
            'categories': categories,
            'protections': protections,
        }
        geojson_items.append(
            geojson.Feature(geometry=geojson.Point((row['longitude'], row['latitude'])),
                            properties=properties))
        detail_items[row_id] = details

    with open('web/data/pops.geojson', 'w') as outfile:
        json.dump(geojson.FeatureCollection(features=geojson_items), outfile)
    with open('web/data/pops.json', 'w') as outfile:
        json.dump(detail_items, outfile)


def main():
    data = get_data(force_cache_update=True)
    to_geojson(data)


if __name__ == "__main__":
    main()
