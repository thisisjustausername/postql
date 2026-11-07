"""
Database credentials type.

-----------------------------------
Copyright (c) 2026 Leon Gattermeyer
"""

from dataclasses import dataclass


@dataclass
class Credentials:
    """
    Credentials dataclass to hold database connection information.

    Args:
        user (str): The username for the database connection.
        password (str): The password for the database connection.
        database_name (str): The name of the database to connect to.
        host (str, optional): The hostname of the database server. Defaults to 'localhost'.
        port (str | int, optional): The port number of the database server. Defaults to 5432.
    """
    user: str
    password: str
    database_name: str
    host: str = 'localhost'
    port: str | int = 5432
