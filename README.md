# SRID Bounding Boxes

This project provides bounding boxes for nearly 4,000 SRIDs found in PostGIS's
`public.spatial_ref_sys` table.  The goal of this project is to make it easier to
find a localized SRID for specific areas in specific units (meters, feet, decimal degrees)  The bounding boxes were collected from the defined
WGS84 Bounds on the https://spatialreference.org website.

These bounding boxes are not inteded to be authoritative and may contain errors.

https://spatialreference.org/ref/epsg/2772/


## Load to PostGIS

Download the SQL script and use `psql` to load.

```bash
wget https://raw.githubusercontent.com/rustprooflabs/srid-bbox/main/srid_bbox.sql
psql -d pgosm -f srid_bbox.sql
```


## Load, not to PostGIS

If using this data in GIS systems outside of PostGIS, download the GeoJSON for use.
This data file was exported via QGIS 3.16 from the ``public.srid_units`` view filtered for rows with a bounding box defined.  The data is in SRID 3857.


```
wget https://raw.githubusercontent.com/rustprooflabs/srid-bbox/main/srid_bbox.geojson
```

## Source to create the data

The code used below is here for reference.  If you want to use this data, follow the
instructions above to load the results.  This code takes a number of hours to run 
through.

```sql
CREATE TABLE public.srid_bbox
(
    srid BIGINT NOT NULL,
    geom GEOMETRY(POLYGON, 3857),
    CONSTRAINT pk_srid_bbox PRIMARY KEY (srid)
);

COMMENT ON TABLE public.srid_bbox IS 'Bounding boxes for SRIDs sourced from https://spatialreference.org';

COMMENT ON COLUMN public.srid_bbox.srid IS 'Spatial Reference identifier, matches values in public.spatial_ref_sys and used to look up bbox from source.';
COMMENT ON COLUMN public.srid_bbox.geom IS 'Bounding box for the SRID from WGS84 Bounds defined at https://spatialreference.org/ref/epsg/{srid}/';

CREATE INDEX gix_srid_bbox ON public.srid_bbox USING GIST (geom);

```

## SRID View

Create view adapted from original Gist: https://gist.github.com/rustprooflabs/a86e3ff5c829b0fa32ebbd5702883ebe


```sql
CREATE VIEW public.srid_units AS
SELECT srs.srid, CASE WHEN proj4text LIKE '%+units=%' THEN True 
			ELSE False 
			END AS units_set,
		CASE WHEN proj4text LIKE '%+units=m%'	 THEN 'Meters'
			WHEN proj4text LIKE '%+units=ft%' THEN 'Feet'
			WHEN proj4text LIKE '%+units=us-ft%' THEN 'Feet'
			WHEN proj4text LIKE '%+units=link%' 
					OR proj4text LIKE '%+units=%'
				THEN 'Set, not caught properly'
			ELSE 'Decimal Degrees'
			END AS units,
		proj4text, srtext,
		ST_Area(ST_Transform(bbox.geom, 4326)::GEOGRAPHY) AS geom_area,
		bbox.geom AS geom
	FROM public.spatial_ref_sys srs
	LEFT JOIN public.srid_bbox bbox ON srs.srid = bbox.srid
;
COMMENT ON VIEW public.srid_units IS 'PostGIS specific view to make it easier to find what units each SRID is in and the bounding box indicating where the SRID is best suited for.';
```


## Run Python

```
python get_srid_bboxes.py
```

Full list will take hours to iterate through.

## Export data

For loading back into PostGIS.

```bash
pg_dump --table=srid_bbox --table=srid_units --no-privileges --no-owner > srid_bbox.sql
```


