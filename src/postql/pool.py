"""
Create pool of database connections.

-----------------------------------
Copyright (c) 2026 Leon Gattermeyer
"""

from psycopg import Cursor
from psycopg_pool import ConnectionPool

from .types import Credentials


def create_pool(credentials: Credentials, max_connections: int = 100, min_connections: int = 40) -> ConnectionPool:
    """
    create_pool
    creates a thread pool safely

    Args:
        credentials (Credentials): credentials object containing database connection information
        max_connections (int): maximum number of connections
        min_connections (int): minimum number of connections
    Returns:
        connection_pool: connection_pool
    """
    connection_pool = ConnectionPool(
        min_size=min_connections,
        max_size=max_connections,
        kwargs={
        "user": credentials.user,
        "password": credentials.password,
        "host": credentials.host,
        "port": credentials.port,
        "dbname": credentials.database_name
        }
    )

    if not connection_pool:
        raise Exception("Creation of connection pool failed")
    return connection_pool


def close_pool(pool: ConnectionPool) -> None:
    """
    close_pool
    closes the connection pool

    Args:
        pool (ConnectionPool): connection pool to close
    """
    pool.close()


def get_cursor(pool: ConnectionPool) -> Cursor:
    """
    get a cursor from the pool

    Returns:
        Cursor: cursor object for database
        pool (ConnectionPool): connection pool to get the connection from
    """
    return pool.getconn().cursor()


def close_cursor(cursor: Cursor, pool: ConnectionPool) -> None:
    """
    close a cursor and return the connection to the pool

    Args:
        Cursor: cursor object to close
        pool (ConnectionPool): connection pool to return the connection to
    """
    cursor.close()
    pool.putconn(cursor.connection)
