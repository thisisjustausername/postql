"""
Enum classes for database operations.

-----------------------------------
Copyright (c) 2026 Leon Gattermeyer
"""

from enum import Enum


class ANSWER_TYPE(str, Enum):
    """
    Enum for answer types of db calls

    Attributes:
        NO_ANSWER: no answer expected
        SINGLE_ANSWER: single answer expected
        LIST_ANSWER: list of answers expected
    """

    NO_ANSWER = "NO_ANSWER"
    SINGLE_ANSWER = "SINGLE_ANSWER"
    LIST_ANSWER = "LIST_ANSWER"

    @staticmethod
    def is_valid(value):
        """
        static method to check whether the input value is a valid ANSWER_TYPE attribute
        """
        return value in ANSWER_TYPE._value2member_map_


class ORDER(str, Enum):
    """
    Enum for order in SQL ORDER BY statements

    Attributes:
        ASC: ascending order
        DESC: descending order
    """

    ASC = "ASC"
    DESC = "DESC"

    @staticmethod
    def is_valid(value):
        """
        static method to check whether the input value is a valid ORDER attribute
        """
        return value in ORDER._value2member_map_
