# SRID Bounding Boxes

This project scrapes the WGS84 Bounds from the https://spatialreference.org website
in order to provide bounding box recommendations for SRID within PostGIS.

https://spatialreference.org/ref/epsg/2772/

## Create Table


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
CREATE OR REPLACE VIEW public.srid_units AS
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
		bbox.geom
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
pg_dump --table=srid_bbox --no-privileges > srid_bbox.sql
```


