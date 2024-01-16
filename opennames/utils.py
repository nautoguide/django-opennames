import re
import random

from opennames.models import Opennames


"""
Find a postcode in a string, will return the matched full postcode if found or the original search string

"""


def postcode_finder(searchtext):
    matches = []
    # Full postcode match
    full_match = re.compile(
        r'([A-Z]{1,2}[0-9][A-Z0-9]? [0-9][ABD-HJLNP-UW-Z]{2})',
        re.IGNORECASE)

    # Basic search looking from anything from an outwards onwards
    partial_match = re.compile(
        r'.*([A-Z]{1,2}[0-9]).*',
        re.IGNORECASE
    )

    postcode_found = bool(partial_match.match(searchtext))

    if postcode_found:
        matches = full_match.search(searchtext)

    return postcode_found, matches.group(1).replace(' ', '').upper() if matches else searchtext



"""
Make geojson from a location structure
"""


def geojson_from_location(location, icon='point'):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "icon": icon
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(location.get('lon')), float(location.get('lat'))]
                }
            }
        ]
    }


def geojson_from_items(items):
    geojson = {"type": "FeatureCollection", "features": []}

    for item in items:
        location = item.get('location')
        if location:
            geojson['features'].append({"properties": {"icon": "point"},
                                        "geometry": {"type": "Point",
                                                     "coordinates": [
                                                         location.get('lon'), location.get('lat')]}})

    return geojson

def random_place():

    opennames_count = 3000000
    random_index = random.randint(0, opennames_count)
    rand_item = None
    while not rand_item:
        try:
            rand_item = Opennames.objects.get(id=random_index)
        except:
            random_index = random.randint(0, opennames_count)
            rand_item = None

    random_item = Opennames.objects.get(id=random_index)

    return random_item