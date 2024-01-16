from django.contrib.gis.db import models

class Opennames(models.Model):
    ogc_fid = models.CharField(max_length=255, null=True)
    names_uri = models.CharField(max_length=255, null=True)
    name1 = models.CharField(max_length=255, null=True)
    name1_lang = models.CharField(max_length=255, null=True)
    name2 = models.CharField(max_length=255, null=True)
    name2_lang = models.CharField(max_length=255, null=True)
    type = models.CharField(max_length=255, null=True)
    local_type = models.CharField(max_length=255, null=True)
    most_detail_view_res = models.IntegerField(null=True)
    least_detail_view_res = models.IntegerField(null=True)
    mbr_xmin = models.FloatField(null=True)
    mbr_ymin = models.FloatField(null=True)
    mbr_xmax = models.FloatField(null=True)
    mbr_ymax = models.FloatField(null=True)
    postcode_district = models.CharField(max_length=255, null=True)
    postcode_district_uri = models.CharField(max_length=255, null=True)
    populated_place = models.CharField(max_length=255, null=True)
    populated_place_uri = models.CharField(max_length=255, null=True)
    populated_place_type = models.CharField(max_length=255, null=True)
    district_borough = models.CharField(max_length=255, null=True)
    district_borough_uri = models.CharField(max_length=255, null=True)
    district_borough_type = models.CharField(max_length=255, null=True)
    county_unitary = models.CharField(max_length=255, null=True)
    county_unitary_uri = models.CharField(max_length=255, null=True)
    county_unitary_type = models.CharField(max_length=255, null=True)
    region = models.CharField(max_length=255, null=True)
    region_uri = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=255, null=True)
    country_uri = models.CharField(max_length=255, null=True)
    related_spatial_object = models.CharField(max_length=255, null=True)
    same_as_dbpedia = models.CharField(max_length=255, null=True)
    same_as_geonames = models.CharField(max_length=255, null=True)
    geom = models.PointField(srid=4326, null=True)
    class Meta:
        ordering = ['name1']
        indexes = [
            models.Index(
                fields=['name1'],
                name='postcode_geocoder',
                condition=models.Q(local_type='Postcode')
            ),
            models.Index(fields=['local_type'], name='idx_opennames_local_type'),
        ]

    def __str__(self):
        return self.name1


