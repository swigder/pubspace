import geojson
import json
import pandas
import requests

from collections import defaultdict, namedtuple

Filter = namedtuple('Filter', ['description', 'filter_id', 'any_all', 'options'])
FilterOption = namedtuple('FilterOption', ['option_id', 'display_name'])

DATASET_URL = 'https://data.cityofnewyork.us/resource/rvih-nhyn.csv'

CATEGORIES = {
    'Arcade': [],
    'Lobby': [],
    'Other Enclosed': [
        'Covered Pedestrian Space',
        'Glass-Enclosed Urban Plaza Equivalent',
    ],
    'Other Outdoors': [
        'Courtyard',
        'Landscaped Terrace',
        'Landscaped Terraces',
    ],
    'Park': [],
    'Passageway': [],
    'Plaza': [
        'Large Square',
        'Small Square',
    ],
    'Other / Unknown': [],
}

TYPE_TO_CATEGORY = {i: k for k, v in CATEGORIES.items() for i in v}

PROTECTION = {
    'Outdoors': ['Park', 'Plaza', 'Other Outdoors'],
    'Enclosed': ['Enclosed', 'Lobby', 'Other Enclosed'],
    'Covered': ['Arcade', 'Covered'],
    'Other / Unknown': ['Other / Unknown', 'Passageway'],
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


def get_categories_and_protections(public_space_type):
    categories = []
    for space_type in public_space_type:
        if space_type in TYPE_TO_CATEGORY:
            categories.append(TYPE_TO_CATEGORY[space_type])
        else:
            matches = [category for category in CATEGORIES.keys() if category in space_type]
            categories.extend(matches)
            if not len(matches):
                categories.append('Other / Unknown')
    protections = [CATEGORY_TO_PROTECTION[category] for category in categories]
    return categories, protections


EMOJIS = defaultdict(lambda: '', {
    'Accessible': '♿️',
    'Climate Control': '🌡️',
    'Covered': '☂️',
    'Enclosed': '🏢',
    'Full/Partial': '♿️',
    'Outdoors': '☀️',
    'Seating': '🪑',
    'Restrooms': '🚻',
})

AMENITY_FILTERS = ['Climate Control', 'Seating', 'Tables', 'Restrooms', 'Accessible']

SPACE_TYPE_FILTERS = CATEGORIES.keys()

PROTECTION_FILTERS = PROTECTION.keys()

def filter_key(name):
    if name == 'Other / Unknown':
        return 'unk'
    return name.lower().replace(' ', '_')


def display_name(name):
    return EMOJIS[name] + name


def to_geojson(df):
    for column in ['building_name', 'amenities_required', 'public_space_type', 'physically_disabled']:
        df[column].fillna('', inplace=True)

    geojson_items = []
    detail_items = {}

    def to_list(data_string):
        return [i.strip().replace("'", '') for i in data_string.split(';') if i]

    for index, row in df.iterrows():
        row_id = row['pops_number']
        amenities = to_list(row['amenities_required'])
        accessible = row['physically_disabled'] == 'Full/Partial'
        amenities_for_filter = amenities + (['Accessible'] if accessible else [])
        public_space_type = to_list(row['public_space_type'])
        categories, protections = get_categories_and_protections(public_space_type)

        def filter_values(filter_options, item_values):
            return ';'.join([filter_key(f) for f in filter_options if f in item_values])

        properties = {
            'id': row_id,
            'amenities': filter_values(AMENITY_FILTERS, amenities_for_filter),
            'protections': filter_values(PROTECTION_FILTERS, protections),
        }
        details = {
            'name': row['building_name'],
            'address': row['address_number'] + ' ' + row['street_name'].title(),
            'amenities': [display_name(a) for a in amenities],
            'public_space_type': public_space_type,
            'accessibility': display_name(row['physically_disabled']),
        }
        geojson_items.append(
            geojson.Feature(geometry=geojson.Point((row['longitude'], row['latitude'])),
                            properties=properties))
        detail_items[row_id] = details

    with open('web/data/pops.geojson', 'w') as outfile:
        json.dump(geojson.FeatureCollection(features=geojson_items), outfile)
    with open('web/data/pops.json', 'w') as outfile:
        json.dump(detail_items, outfile)


def write_metadata():
    metadata = {
        'filters': [
            Filter(description='Amenities',
                   filter_id='amenities',
                   any_all='all',
                   options=[
                       FilterOption(
                           option_id=filter_key(a),
                           display_name=display_name(a))._asdict()
                       for a in AMENITY_FILTERS])._asdict(),
            Filter(description='Space type (best effort guess)',
                   filter_id='protections',
                   any_all='any',
                   options=[
                       FilterOption(
                           option_id=filter_key(a),
                           display_name=display_name(a))._asdict()
                       for a in PROTECTION_FILTERS])._asdict()
        ]
    }
    with open('web/data/metadata.json', 'w') as outfile:
        json.dump(metadata, outfile)


def main():
    data = get_data(force_cache_update=True)
    to_geojson(data)
    write_metadata()


if __name__ == "__main__":
    main()
