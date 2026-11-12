"""
Database interaction module

This module provides functions to connect to a PostgreSQL database and perform basic operations such as
selecting, inserting, updating, and deleting records. It also includes decorators for cursor management and error handling.

-----------------------------------
Copyright (c) 2026 Leon Gattermeyer
"""

import traceback
from typing import Any

import psycopg as pg
from psycopg import Cursor, sql
from psycopg.rows import TupleRow

from .pool import close_pool, create_pool
from .types import ANSWER_TYPE, ORDER, Credentials, Result


class DB:
    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.pool = create_pool(credentials=credentials)

    def connect(self) -> Cursor:
        """
        connect
        Args:
            credentials (Credentials): credentials object containing user, password, host, port, and dbname
        Returns:
            Cursor: cursor to interact with db
        """
        return pg.connect(
            user=self.credentials.user, password=self.credentials.password, host=self.credentials.host, port=self.credentials.port, dbname=self.credentials.database_name
        ).cursor()

    def fetch(
        self,
        query: sql.Composable,
        type_of_answer: ANSWER_TYPE,
        variables: list[Any] | tuple[Any,...] | None = None,
        commit: bool = False
    ) -> TupleRow | list[list[TupleRow]] | None | Exception:
        """
        fetches one record from the database based on the provided query and variables

        Args:
            query (str): the SQL query to execute
            type_of_answer (ANSWER_TYPE): what answer to expect, fetchone if SINGLE_ANSWER, fetchall if LIST_ANSWER, else no fetch
            variables (list | tuple | None): the variables to pass into the query, if any
            commit (bool): whether to commit the transaction after executing the query, default False

        Returns:
            TupleRow | None | list[list[TupleRow]] | Exception: either no, the first or all records will be returned
        """
        with self.pool.connection() as conn,  conn.cursor() as cursor:
            try:
                cursor.execute(query, variables) # type: ignore
                if commit:
                    conn.commit()
                if type_of_answer == ANSWER_TYPE.SINGLE_ANSWER:
                    return cursor.fetchone()
                if type_of_answer == ANSWER_TYPE.LIST_ANSWER:
                    return [list(i) for i in cursor.fetchall()]
                return None
            except Exception as e:
                if commit:
                    conn.rollback()
                return e


    # TODO: can't return success: False right now
    # TODO: for arguments as list might not be completely implemented
    # TODO: specific_where and variables don't work together
    # @catch_exception
    def select(
        self,
        table: str,
        type_of_answer: ANSWER_TYPE = ANSWER_TYPE.LIST_ANSWER,
        columns: tuple[str] | list[str] = ("*",),
        conditions: dict[str, Any] | None = None,
        negated_conditions: dict[str, Any] | None = None,
        select_max_of_key: str = "",
        specific_where: str = "",
        variables: list[str] | None = None,
        order_by: tuple[str, ORDER] | None = None,
    ) -> Result[Any, Exception]:
        """
        select
        read data from a table

        Args:
            table (str): table to select from
            columns (tuple[str] | list[str]): columns, that should be selected, if empty, get all
            conditions (dict): under which conditions (key: column, value: value) values should be selected, if empty, no conditions
            negated_conditions (dict): under which conditions (key: column, value: value) values should NOT be selected, if empty, no negated conditions
            type_of_answer (ANSWER_TYPE): specify whether one or more answers are to be received, therefore it changes, whether list or single object will be returned
            select_max_of_key (bool): conditions must be empty, otherwise it won't be used
            specific_where (str): select_max_of_key must be empty as well as conditions must be empty, else specific_where is ignored, allows to pass in a unique where statement (WHERE is already in the string),
            variables (list | None): list of variables that should be passed into the specific_where statement
            order_by (str, ORDER) | None: ORDER by default no ordering
        Returns:
            Result: result object with data or error
        """

        # check, whether type_of_answer is valid
        if (
            not ANSWER_TYPE.is_valid(type_of_answer)
            or type_of_answer == ANSWER_TYPE.NO_ANSWER
        ):
            raise ValueError(
                "parameter type_of_answer of the function must be of enum type LIST_ANSWER and not SINGLE_ANSWER"
            )

        # specific_where and variables can't be used together
        if specific_where != "" and (
            conditions is not None or negated_conditions is not None
        ):
            raise ValueError(
                "specific_where and conditions or negated_conditions are explicit"
            )

        # initialize variables
        columns = list(columns)
        conditions = {} if conditions is None else conditions
        negated_conditions = {} if negated_conditions is None else negated_conditions
        result = {"success": False, "data": None, "error": None}

        # build query
        all_conditions = {
            key: {"value": value, "negated": False} for key, value in conditions.items()
        } | {
            key: {"value": value, "negated": True}
            for key, value in negated_conditions.items()
        }

        schema = None
        if "." in table:
            schema, table = table.split(".")

        query = sql.SQL("SELECT {cols} FROM {schema}{table}").format(
            cols=sql.SQL(", ").join(map(sql.Identifier, columns)) if columns[0] != "*" else sql.SQL("*"),
            schema=sql.SQL("{schema}.").format(schema=sql.Identifier(schema)) if schema is not None else sql.SQL(""),
            table=sql.Identifier(table)
        )


        # add conditions if any
        if len(all_conditions) > 0:
            query += sql.SQL(" WHERE ") + \
                sql.SQL(' AND '.join([f'{{}} {"!" if value_data["negated"] is True else ""}= %s'
                    for value_data in all_conditions.values()])) \
            .format(*[sql.Identifier(key) for key in all_conditions])
            if order_by is not None:
                query += sql.SQL(" ORDER BY {} {}").format(sql.Identifier(order_by[0], order_by[1].value))
            # get data based on answer type
            data = self.fetch(query=query, type_of_answer=type_of_answer, variables=tuple(i["value"] for i in all_conditions.values()), commit=False)
            if data is None: data = []
            # map the data to the columns if columns are explicitly specified
            if columns is not None and "*" not in columns:
                result = (
                    dict(zip(columns, data))  # type: ignore
                    if type_of_answer == ANSWER_TYPE.SINGLE_ANSWER
                    else [dict(zip(columns, vals)) for vals in data]  # type: ignore
                )
            else:
                result = data
            if isinstance(data, Exception):
                return Result(error=data, stack_trace=traceback.format_exc())
            return Result(data=result)

        # add select max of key condition
        elif select_max_of_key != "":
            query += sql.SQL(" WHERE {max_key} = (SELECT MAX({max_key}) FROM {schema}{table}) LIMIT 1").format(max_key=sql.Identifier(select_max_of_key),
                                                                                                               schema=sql.SQL("{schema}.").format(schema=sql.Identifier(schema)) if schema is not None else sql.SQL(""),
                                                                                                               table=sql.Identifier(table))

        # add specific where condition
        elif specific_where != "":
            query += sql.SQL(f" WHERE {specific_where}").format(specific_where=sql.Identifier(specific_where)) # type: ignore
            if specific_where.count(" %s") != (
                len(variables) if variables is not None else 0
            ):
                raise ValueError(
                    "number of placeholders must match the number of provided variables"
                )
        if order_by is not None:
            query += sql.SQL(" ORDER BY {} {}").format(sql.Identifier(order_by[0], order_by[1].value))

        # get data based on answer type
        data = self.fetch(query=query, type_of_answer=type_of_answer, variables=variables, commit=False)
        # map the data to the columns if columns are explicitly specified
        if columns is not None and "*" not in columns:
            result = (
                dict(zip(columns, data))  # type: ignore
                if type_of_answer == ANSWER_TYPE.SINGLE_ANSWER
                else [dict(zip(columns, vals)) for vals in data]  # type: ignore
            )
            if not isinstance(data, Exception):
                return Result(data=result)
        else:
            result = data
        if isinstance(data, Exception):
            return Result(error=data, stack_trace=traceback.format_exc())
        return Result(data=result)


    # NOTE arguments is either of type dict or of type list
    # TODO: parametrize returning_column
    # @catch_exception
    def insert(
        self,
        table: str,
        values: dict[str, Any] | list[str] | None,
        returning_column: str | None = None,
    ) -> Result[Any, Exception]:
        """
        insert data into table

        Args:
            cursor (Cursor): cursor for interaction with db
            table (str): table to insert into, if empty set all
            values (dict | list): values that should be entered (key: column, value: value), if empty, no conditions, if values is of type list, then list has to contain all values that have to be entered
            returning_column (int): returns the column; IMPORTANT: returning_column is not being parametrized
        Returns:
            Result: result object with data or error
        """

        # initialize variables
        if values is None:
            values = {}
        if returning_column == "":
            returning_column = None
        query = ""
        vals = []

        schema = None
        if "." in table:
            schema, table = table.split(".")

        # build parametrized query
        if isinstance(values, list):
            query = sql.SQL("INSERT INTO {schema}{table} VALUES (").format(
                schema=sql.SQL("{schema}.").format(schema=sql.Identifier(schema)) if schema is not None else sql.SQL(""),
                table=sql.Identifier(table)
            ) + sql.SQL(", ").join(sql.Placeholder() * len(values)) + sql.SQL(")")
            vals = values
        elif isinstance(values, dict):
            query = sql.SQL("INSERT INTO {schema}{table} ({cols}) VALUES ({vals})").format(
                schema=sql.SQL("{schema}.").format(schema=sql.Identifier(schema)) if schema is not None else sql.SQL(""),
                table=sql.Identifier(table),
                cols=sql.SQL(", ").join(map(sql.Identifier, values.keys())),
                vals=sql.SQL(", ").join(sql.Placeholder() for _ in values)
            )
            vals = list(values.values())

        # add returning_column
        if returning_column is not None:
            query += sql.SQL(" RETURNING {returning_column}").format(returning_column=sql.Identifier(returning_column))

        # run query
        data = self.fetch(query=query, type_of_answer=ANSWER_TYPE.SINGLE_ANSWER if returning_column is not None else ANSWER_TYPE.NO_ANSWER, variables=vals, commit=True)

        # return data if requested
        if isinstance(data, Exception):
            return Result(error=data, stack_trace=traceback.format_exc())
        return Result(data=data)


    # for specific_where conditions must be empty, otherwise conditions will be ignored IMPORTANT what is being ignored differs from the other functions
    def update(
        self,
        table: str,
        returning_column: str | None = None,
        columns: dict[str, Any] | None = None,
        conditions: dict[str, Any] | None = None,
        specific_where: str = "",
        specific_set: str = "",
    ) -> Result[Any, Exception]:
        """
        updates values in a table
        already has try catch

        Args:
            table (str): table to insert into, if empty set all
            columns (dict | None): values that should be entered (key: column, value: value)
            conditions (dict | None): specify to insert into the correct row
            specific_where (str): conditions must be empty, otherwise conditions will be ignored, specifies where should be set,
                                  IMPORTANT what is being ignored differs from the other functions
            specific_set (str): columns must be empty, otherwise columns will be ignored, specifies what should be set
            returning_column (str): returns the specified column, returns just a single column
        Returns:
            Result: result object with data or error
        """

        # initialize variables
        if columns is None:
            columns = {}
        if conditions is None:
            conditions = {}
        if returning_column == "":
            returning_column = None

        schema = None
        if "." in table:
            schema, table = table.split(".")

        # build query
        query = sql.SQL("UPDATE {schema}{table} SET {setter}").format(
            schema=sql.SQL("{schema}.").format(schema=sql.Identifier(schema)) if schema is not None else sql.SQL(""),
            table=sql.Identifier(table),
            setter=(sql.SQL(specific_set) if specific_set != "" else sql.SQL(", ").join([sql.SQL("{key} = {placeholder}").format(key=sql.Identifier(key), placeholder=sql.Placeholder()) for key in columns])) # type: ignore
        )

        # where part
        if specific_where != "":
            query += sql.SQL(" WHERE {specific_where}").format(specific_where=sql.SQL(specific_where)) # type: ignore
        else:
            query += sql.SQL(" WHERE {w}").format(w=sql.SQL(" AND ").join([sql.SQL("{key} = {placeholder}").format(key=sql.Identifier(key), placeholder=sql.Placeholder()) for _, key in enumerate(conditions)]))

        # returning part
        if returning_column is not None:
            query += sql.SQL(" RETURNING {returning_column}").format(returning_column=sql.Identifier(returning_column))

        # execute query
        data = self.fetch(query=query, type_of_answer=ANSWER_TYPE.SINGLE_ANSWER if returning_column is not None else ANSWER_TYPE.NO_ANSWER, variables=list(columns.values()) + list(conditions.values()))
        if isinstance(data, Exception):
            return Result(error=data, stack_trace=traceback.format_exc())
        return Result(data=data)


    def delete(
        self,
        table: str,
        conditions: dict[str, Any],
        returning_column: str | None = None,
    ) -> Result[Any, Exception]:
        """
        removes data from table
        already has try catch

        Args:
            table (str): table to insert into, if empty set all
            conditions (dict): specify from which row to remove the data
            returning_column (str): returns the specified column, returns just a single value
        Returns:
            Result: result object with data or error
        """

        # initialize variables
        if returning_column == "":
            returning_column = None

        schema = None
        if "." in table:
            schema, table = table.split(".")

        # build query
        query = sql.SQL("DELETE FROM {schema}{table} WHERE ").format(
            schema=sql.SQL("{schema}.").format(schema=sql.Identifier(schema)) if schema is not None else sql.SQL(""),
            table=sql.Identifier(table)
        )
        query += sql.SQL(" AND ").join(sql.SQL("{key} = {placeholder}").format(key=sql.Identifier(key), placeholder=sql.Placeholder()) for key in conditions)

        # returning part
        if returning_column is not None:
            query += sql.SQL(" RETURNING {returning_column}").format(returning_column=sql.Identifier(returning_column))

        data = self.fetch(query=query, type_of_answer=ANSWER_TYPE.SINGLE_ANSWER if returning_column is not None else ANSWER_TYPE.NO_ANSWER, variables=list(conditions.values()), commit=True)

        if isinstance(data, Exception):
            return Result(error=data, stack_trace=traceback.format_exc())

        return Result(data=data)


    def custom_call(
        self,
        query: sql.Composed | str,
        type_of_answer: ANSWER_TYPE,
        variables: list[Any] | tuple[Any,...] | None = None,
    ) -> Result[Any, Exception]:
        """
        send a custom query to the database

        Args:
            query (sql.Composed | str): the SQL query to execute
            type_of_answer (ANSWER_TYPE): what answer to expect
            variables (list | tuple | None): list of variables that should be passed into the query
        Returns:
            Result: result object with data or error
        """
        commit = (query if isinstance(query, str) else query.as_string()).startswith("SELECT") is False
        data = self.fetch(query=query, type_of_answer=type_of_answer, variables=variables, commit=commit) # type: ignore

        if isinstance(data, Exception):
            return Result(error=data, stack_trace=traceback.format_exc())
        return Result(data=data)


    # TODO can only return success True right now
    # @catch_exception
    def get_time(self) -> Result[Any, Exception]:
        """
        returns the current berlin time

        Returns:
            Result: result object with data or error
        """
        # execute query
        query = sql.SQL("SELECT NOW() AT TIME ZONE 'Europe/Berlin' AS current_time")
        data = self.fetch(query=query, type_of_answer=ANSWER_TYPE.SINGLE_ANSWER, variables=None, commit=False)
        if isinstance(data, Exception):
            return Result(error=data, stack_trace=traceback.format_exc())
        return Result(data=data[0] if data is not None else None)


    def close(self, cursor: Cursor):
        """
        closes the current cursor

        Args:
            cursor: cursor that should be closed
        """
        cursor.close()
        conn = getattr(cursor, "connection", None)
        if conn is not None:
            conn.close()


    def shutdown(self):
        """
        closes the connection pool
        """
        close_pool(self.pool)


def close(cursor: Cursor):
    """
    closes the current cursor

    Args:
        cursor: cursor that should be closed
    """
    cursor.close()
    conn = getattr(cursor, "connection", None)
    if conn is not None:
        conn.close()
