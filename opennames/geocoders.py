import pyproj
import json

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Case, When, IntegerField, Value
from django.db.models.expressions import RawSQL
from django.contrib.gis.geos import Point, Polygon,GEOSGeometry
from .models import Opennames


def featureMaker(geometry, properties):

    return {
            'type' : 'Feature',
            'geometry': json.loads(geometry),
            'properties': properties
        }


class OpennamesGeocoder:

    def __init__(self, **kwargs):
        self.crs = kwargs.get('opennames_srs', 'epsg:4326')
        self.input_crs = kwargs.get('input_srs', 'epsg:3857')
        self.input_transformer = pyproj.Transformer.from_crs(self.input_crs, self.crs, always_xy=True)
        self.output_transformer = pyproj.Transformer.from_crs(self.crs, self.input_crs, always_xy=True)
        self.query_bbox = None
    def make_query_bbox(self, **kwargs):
        lon1, lat1, lon2, lat2 = kwargs.get('bbox')
        x1, y1 = self.input_transformer.transform(lon1, lat1)
        x2, y2 = self.input_transformer.transform(lon2, lat2)
        self.query_bbox = Polygon.from_bbox((x1,y1,x2,y2))
        geom = GEOSGeometry(self.query_bbox, srid=4326)
        geom.transform(3857)
        self.query_bbox_area = geom.area

    @staticmethod
    def geocode(postcode, **kwargs):
        try:
            # Query the OpenName model using the provided postcode and local_type constraint
            postcode = postcode.replace(' ', '')
            formatted_postcode = " ".join([postcode[:-3], postcode[-3:]]).upper()
            result = Opennames.objects.get(name1=formatted_postcode, local_type='Postcode')

            buffer = kwargs.get('buffer')
            ret = []
            if buffer:
                pt = result.geom.transform(3857, clone=True)
                bp = pt.buffer(buffer)
                bp.transform(4326)
                ret = [featureMaker(bp.geojson,{'buffer': buffer, 'type': 'buffer'})]

            if kwargs.get('format') == 'geojson':
                ret.append(featureMaker(result.geom.geojson,{'postcode': postcode, 'type': 'postcode'}))
                return {'type': 'FeatureCollection', 'features': ret}

            return result.geom

        except Opennames.DoesNotExist:

            # If no matching result is found, return None
            return None

    @staticmethod
    def places_search(query, **kwargs):
        local_types = kwargs.get('local_types', ['City', 'Town', 'Village', 'Suburban Area', 'Named Road', 'Postcode'])
        search_query = SearchQuery(query, config='english')

        ordering_case = Case(
            *[When(local_type=lt, then=Value(idx)) for idx, lt in enumerate(local_types)],
            default=Value(len(local_types)),
            output_field=IntegerField()
        )

        results = Opennames.objects.annotate(
            search=SearchVector('name1', config='english'),
            ordering=ordering_case,
            rank=SearchRank('name1', search_query),
        ).filter(search=query,local_type__in=local_types).order_by('ordering', 'rank')

        data = list(results.values('name1', 'postcode_district', 'region', 'populated_place', 'local_type', 'rank'))
        return data

    def freetext(self, freetext, bbox, **kwargs):

        rank_min = kwargs.get('min_rank',0.03)
        max_area = kwargs.get('max_bbox_area', 10000 * 10000)
        self.make_query_bbox(bbox=bbox)
        if self.query_bbox_area > max_area:
            return {'error': 'bbox too large', 'area': self.query_bbox_area}

        matches = Opennames.objects.annotate(
            rank=RawSQL("""
                ts_rank(to_tsvector('english', %s), phraseto_tsquery('english', name1))
            """, [freetext]),
            headline=RawSQL("""
                ts_headline('english', %s, phraseto_tsquery('english', name1), 'StartSel=<<<,StopSel=>>>')
            """, [freetext])
        ).filter(
            geom__within=self.query_bbox,
            rank__gte=rank_min
        ).order_by('-rank')

        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [match.geom.x, match.geom.y]
                },
                "properties": {
                    "name": match.name1,
                    "rank": match.rank,
                    "headline": match.headline if '<<<' in match.headline else ''
                }
            } for match in matches
        ]

        fc = {"type": "FeatureCollection", "features": features}
        return {'text':freetext, 'bbox': self.query_bbox.ewkt, 'geojson': fc, 'bbox_area': self.query_bbox_area}


class GridRefGeocoder:

    @staticmethod
    def geocode(gridref, crs='EPSG:4326'):
        try:
            # Convert UK grid reference to easting and northing coordinates
            letters = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
            easting = 0
            northing = 0
            gridref = gridref.upper()
            for i in range(len(gridref)):
                if gridref[i] in letters:
                    easting = easting * 26 + letters.index(gridref[i]) + 1
                    northing = northing * 26 + letters.index(gridref[i + 1]) + 1
                    break
            easting += int(gridref[i + 2:i + 5]) * 100
            northing += int(gridref[i + 5:i + 8]) * 100

            # Create a GeoDjango point geometry object
            point = Point(easting, northing, srid=27700)
            point.transform(crs)

            return point
        except Exception as e:
            return None


class CoordinateGeocoder:

    @staticmethod
    def geocode(x, y, in_crs='EPSG:4326', out_crs='EPSG:4326'):
        # need a numeric code for CRS to set point srid
        in_crs_code = pyproj.CRS(in_crs).to_epsg()

        # Convert strings to floats
        try:
            x = float(x)
            y = float(y)
        except ValueError:
            return None

        # Create a GeoDjango point geometry in the output CRS
        point = Point(x, y, srid=in_crs)
        point.srid = in_crs_code
        point.transform(out_crs)

        return point


def geocoder(item):
    point = None
    lat = item.get('latitude')
    lon = item.get('longitude')
    if lat and lon:
        point = CoordinateGeocoder.geocode(lon, lat)
    elif item.get('gridref'):
        point = GridRefGeocoder.geocode(item.get('gridref'))
    elif item.get('locationpostcode'):
        point = OpennamesGeocoder.geocode(item.get('locationpostcode'))

    return point


def point_to_grid_ref(location):
    easting = location.x
    northing = location.y

    grid_letters = [
        ['SV', 'SW', 'SX', 'SY', 'SZ', 'TV', 'TW'],
        ['SQ', 'SR', 'SS', 'ST', 'SU', 'TQ', 'TR'],
        ['SL', 'SM', 'SN', 'SO', 'SP', 'TL', 'TM'],
        ['SF', 'SG', 'SH', 'SJ', 'SK', 'TF', 'TG'],
        ['SA', 'SB', 'SC', 'SD', 'SE', 'TA', 'TB'],
        ['OV', 'OW', 'OX', 'OY', 'OZ', 'OV', 'OW'],
        ['OQ', 'OR', 'OS', 'OT', 'OU', 'OQ', 'OR'],
    ]

    # Calculate the grid indices
    x_idx = int(easting // 100000)
    y_idx = int(northing // 100000)

    # Calculate the 100km grid letters
    try:
        grid_ref = grid_letters[y_idx][x_idx]
    except IndexError:
        # Not a UK location
        return None

    # Calculate the remaining easting and northing within the 100km grid cell
    easting_remainder = int(easting % 100000)
    northing_remainder = int(northing % 100000)

    # Calculate the 1km grid digits
    grid_ref += f"{easting_remainder // 100:02}{northing_remainder // 100:02}"

    # Truncate the grid reference to 8 characters
    grid_ref = grid_ref[:8]

    return grid_ref


def reverse_geocoder_latlon(lon, lat, local_type=['Postcode']):
    # Create placeholders for IN clause
    placeholders = ','.join(['%s' for _ in local_type])

    # Use the placeholders in the raw SQL query
    query = f'''
        SELECT id, name1
        FROM {Opennames._meta.db_table}
        WHERE local_type IN ({placeholders})
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT 1
    '''

    # Execute the raw query
    nearest = Opennames.objects.raw(query, local_type + [lon, lat])

    item = next(iter(nearest), None)
    return item.name1 if item else ''
