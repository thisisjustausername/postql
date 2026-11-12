# postql

A PostgreSQL client for Python built on the psycopg package.
It manages handling connections and connection pools from the database.
Furthermore it cleanly implements SQL-operations select, insert, update and delete.
It allows for injection-safe SQL-queries and returns the results in a clean and easy-to-use Result object with dictionary or list of dictionaries as data from the query.

## Installation
Install `dist/postql-0.1.0.tar.gz` using curl or wget, then install it using pip.
```bash
# Download .tar file
curl https://raw.githubusercontent.com/thisisjustausername/postql/refs/heads/main/dist/postql-0.1.0.tar.gz --output postql-0.1.0.tar.gz

# Install .tar file
pip install postql-0.1.0.tar.gz
```

Requires at least Python 3.11+ though we recommend at least Python 3.12+ in general.
## Usage

```python
from postql import DB
from postql.types import Answer_Type, Credentials

credentials = Credentials(
    user="user",
    password="secret",
    host="localhost",
    port=5432,
    database_name="mydb",
)

db = DB(credentials)

result = db.select(
    table="users",
    type_of_answer=Answer_Type.LIST_ANSWER,
    columns=["id", "name", "email"],
    conditions={"id": 1},
    negated_conditions={"email": "test"}
)

if result.success:
    print(result.data)
else:
    print(result.error)

db.shutdown()
```

## API

| Name | Description |
| --- | --- |
| `DB` | Database client |
| `Credentials` | Database connection credentials |
| `Response` | Response type can be used as function return type as it holds the `Status`, `Message` and `Result`. |
| `Message` | Describing additional information about a Response. |
| `Status` | Whether an operation succeeded or failed. |
| `Result` | The data a database operation returns, such as the fetched rows. |
| `ANSWER_TYPE` | Controls the shape of the answer of a database call, for example a single row, all rows or none. |
| `ORDER` | Sort direction for queries: `ASC` for ascending or `DESC` for descending. |
 

## License

Currently Copyright (c) 2026 by Leon Gattermeyer.
