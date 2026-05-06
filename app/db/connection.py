from psycopg2.pool import SimpleConnectionPool
from app.core.config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
)


def get_connection():
    return _pool.getconn()


def release_connection(conn):
    _pool.putconn(conn)
