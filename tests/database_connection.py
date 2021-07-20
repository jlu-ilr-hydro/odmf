import psycopg2 as p2

with p2.connect('postgresql://postgres:password@localhost:5432/postgres') as con:
    with con.cursor() as cur:
        cur.execute('SELECT datname FROM pg_database')
        print('\n'.join(n for n, in cur))
