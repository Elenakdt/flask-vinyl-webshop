import pymysql
import app.app
import sys
import mariadb
from pymongo import MongoClient
from .data.api_extractor import get_data_from_api
from .mariadb_handler import erase_and_fill_maria_db
import os
import json
from flask import current_app


def create_data():

    return


def erase_and_fill_database(mariadb_connection):
    create_data()
    try:
        erase_and_fill_maria_db(mariadb_connection)
    except Exception as e:
        print(f"Error during the erase and fill process: {e}")
    finally:
        mariadb_connection.close()
        print("MariaDB connection closed.")
