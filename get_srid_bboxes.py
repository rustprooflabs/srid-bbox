import datetime
import time
import pandas as pd
import sqlalchemy as sa
import getpass
import requests
from bs4 import BeautifulSoup

# Fix error with SRID coming through as np.int64
# per https://stackoverflow.com/questions/50626058/psycopg2-cant-adapt-type-numpy-int64#50630451
import numpy as np
import psycopg2
from psycopg2.extensions import register_adapter, AsIs
register_adapter(np.int64, psycopg2._psycopg.AsIs)


def get_srid_bbox(srid):
    """Scrapes the SRS site for WGS84 bounding box information.
    
    Parameters
    ------------------------------
    srid : int
        SRID to search

    Returns
    bbox : dict
        Bounding box with xmin, ymin, xmax, ymax
    """
    # Be nice to the endpoint
    loop_delay = 2
    time.sleep(loop_delay)

    base_url = 'https://spatialreference.org/ref/epsg/{srid}/'
    url = base_url.format(srid=srid)
    response = requests.get(url)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, 'lxml')
    found_text = soup.find(string='WGS84 Bounds')
    # The following <script> has the bbox data to easily extract
    script_with_bbox = str(found_text.findAllNext('script', limit=1)[0])

    # Only parens in string seems to be around the bbox data needed
    # Remove first paren and preceeding text
    bbox_in_progress = script_with_bbox.split('(')[1]
    bbox_raw = bbox_in_progress.split(')')[0]

    # Get individual components
    bbox_parts = bbox_raw.split(',')

    xmin = float(bbox_parts[0])
    ymin = float(bbox_parts[1])
    xmax = float(bbox_parts[2])
    ymax = float(bbox_parts[3])
    
    bbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
    return bbox



def get_db_string():
    """Prompts user for details to construct Postgres connection string.

    Returns
    -------------------
    database_string : str
    """
    database_string = 'postgresql://{user}:{pw}@{host}:{port}/{dbname}'
    db_name = input('Database name: ')
    db_user = input('Enter PgSQL username: ')
    db_pw = getpass.getpass('Enter password (optional w/ ~/.pgpass): ')
    db_host = input('Database host [127.0.0.1]: ') or '127.0.0.1'
    db_port = input('Database port [5432]: ') or '5432'
    
    return database_string.format(user=db_user, pw=db_pw, host=db_host,
                                  port=db_port, dbname=db_name)


def get_srids():
    """Querys database to find records missing bbox row.

    Returns
    ------------------
    srids : pandas.DataFrame
    """
    sql_select_srids = """
    SELECT srs.srid
        FROM public.spatial_ref_sys srs
        LEFT JOIN public.srid_bbox bbox ON srs.srid = bbox.srid
        WHERE srs.auth_name = 'EPSG'
            AND bbox.srid IS NULL
            AND srs.srid > (SELECT MAX(srid) FROM public.srid_bbox)
        ORDER BY srs.srid
    ;
    """
    srids = pd.read_sql(sql_select_srids, conn)
    #srids['srid'] = srids['srid'].astype(int)
    return srids


DB_STRING = get_db_string()
conn = sa.create_engine(DB_STRING, echo=False)


start = datetime.datetime.now()
print(f"Starting time: {start}")

srids = get_srids()
print(f'SRID count: {len(srids)}')
found = 0
not_found = 0

for _, row in srids.iterrows():
    srid = row['srid']
    bbox = get_srid_bbox(srid)
    if isinstance(bbox, dict):
        found += 1
        sql_insert = """INSERT INTO public.srid_bbox (srid, geom)
VALUES (%(srid)s, 
        ST_Transform(ST_SetSRID(ST_MakeBox2D(ST_Point(%(xmin)s, %(ymin)s),
            ST_Point(%(xmax)s, %(ymax)s)), 4326),
        3857) 
       )
        """
        params = bbox
        params['srid'] = srid
        db_result = conn.execute(sql_insert, params)
    else:
        not_found += 1


print(f'Found {found}')
print(f'Not Found {not_found}')


end = datetime.datetime.now()
print(f"End time: {end}")
print(f'Elapsed: {end  - start}')
