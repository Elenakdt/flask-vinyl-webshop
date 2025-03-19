from app.backend import mariadb_handler
from app.backend import mariadb_initializer
from app.backend import mongodb_initializer
from app.backend import mongodb_handler
import pymysql
import sys
from flask import request, current_app
from pymongo import MongoClient


def get_mariadb_connection():
    try:
        mariadb_config = current_app.config["MARIADB"]
        connection = pymysql.connect(
            host=mariadb_config["host"],
            port=mariadb_config["port"],
            user=mariadb_config["user"],
            password=mariadb_config["password"],
            database=mariadb_config["name"],
        )
        return connection
    except pymysql.MySQLError as e:
        current_app.logger.error(f"MARIADB Database Error: {e}")
        sys.exit(1)


def get_mongodb_connection():
    mongo_config = current_app.config["MONGODB"]
    client = MongoClient(host=mongo_config["host"], port=mongo_config["port"])
    current_app.logger.info(f"Connected to MongoDB database '{mongo_config['db']}' successfully.")
    db = client[mongo_config["db"]]
    return db


initialized = False
migrated = False


def initialize_db():
    global initialized
    global migrated
    if not initialized:
        mariadb_connection = get_mariadb_connection()
        mariadb_initializer.erase_and_fill_maria_db(mariadb_connection)
        initialized = True
        migrated = False


def erase_and_fill_db():
    global migrated
    migrated = False
    mariadb_connection = get_mariadb_connection()
    mariadb_initializer.erase_and_fill_maria_db(mariadb_connection)


def query_vinyls(limit):
    if migrated:
        current_app.logger.debug("Querying Vinyls from MongoDB")
        return mongodb_handler.query_vinyls(get_mongodb_connection(), limit)
    else:
        current_app.logger.debug("Querying Vinyls from MariaDB")
        return mariadb_handler.query_vinyls(get_mariadb_connection(), limit)


def search_vinyls(query):
    if migrated:
        current_app.logger.debug("Searching Vinyls from MongoDB")
        return mongodb_handler.search_vinyls(get_mongodb_connection(), query)
    else:
        current_app.logger.debug("Searching Vinyls from MariaDB")
        return mariadb_handler.search_vinyls(get_mariadb_connection(), query)


def handle_login(email, password):
    if migrated:
        current_app.logger.debug("handling login from mongodb")
        return mongodb_handler.handle_login(get_mongodb_connection(), email, password)
    else:
        current_app.logger.debug("handling login with mariadb")
        return mariadb_handler.handle_login(get_mariadb_connection(), email, password)


def insert_vinyl(artist_id, vinyl_name, vinyl_price, release_date, cover_image, genre):
    if migrated:
        current_app.logger.debug("inserting vinyl mongodb")
        return mongodb_handler.insert_vinyl(
            get_mongodb_connection(), artist_id, vinyl_name, vinyl_price, release_date, cover_image, genre
        )
    else:
        current_app.logger.debug("inserting vinyl mariadb")
        return mariadb_handler.insert_vinyl(
            get_mariadb_connection(), artist_id, vinyl_name, vinyl_price, release_date, cover_image, genre
        )


def handle_migration():
    mongodb_connection = get_mongodb_connection()
    mariadb_connection = get_mariadb_connection()
    mongodb_initializer.create_collections_with_schemas(mongodb_connection)
    mongodb_initializer.fill_mongodb(mongodb_connection, mariadb_connection)
    global migrated
    migrated = True


def search_vinyls_admin(genre, artist, min_price, max_price, id):
    if migrated:
        current_app.logger.debug("searching vinyls admin from mongodb")
        return mongodb_handler.search_vinyls_admin(get_mongodb_connection(), genre, artist, min_price, max_price, id)
    else:
        current_app.logger.debug("seraching vinyls admin with mariadb")
        return mariadb_handler.search_vinyls_admin(get_mariadb_connection(), genre, artist, min_price, max_price, id)


def get_orders_for_user(user_id):
    if migrated:
        current_app.logger.debug(f"getting user orders for user_id {user_id} from mongodb")
        return mongodb_handler.get_orders_for_user(get_mongodb_connection(), user_id)
    else:
        current_app.logger.debug(f"getting user orders for user_id {user_id} from mariadb")
        return mariadb_handler.get_orders_for_user(get_mariadb_connection(), user_id)


def query_review_by_user(user_id, vinyl_id):
    if migrated:
        current_app.logger.debug(f"getting user review for user_id {user_id} and vinyl_id {vinyl_id} from mongodb")
        return mongodb_handler.query_review_by_user(get_mongodb_connection(), user_id, vinyl_id)
    else:
        current_app.logger.debug(f"getting user review for user_id {user_id} and vinyl_id {vinyl_id} from mariadb")
        return mariadb_handler.query_review_by_user(get_mariadb_connection(), user_id, vinyl_id)


def insert_review_for_vinyl(user_id, vinyl_id, rating, review_text):
    if migrated:
        current_app.logger.debug(
            f"inserting user review for user_id {user_id} and vinyl_id {vinyl_id}, with rating {rating} and comment{review_text}, mongodb"
        )
        return mongodb_handler.insert_review_for_vinyl(get_mongodb_connection(), user_id, vinyl_id, rating, review_text)
    else:
        current_app.logger.debug(
            f"inserting user review for user_id {user_id} and vinyl_id {vinyl_id}, with rating {rating} and comment{review_text}, mariadb"
        )
        return mariadb_handler.insert_review_for_vinyl(get_mariadb_connection(), user_id, vinyl_id, rating, review_text)


def delete_review(user_id, vinyl_id):
    if migrated:
        current_app.logger.debug(f"deleting user review for user_id {user_id} and vinyl_id {vinyl_id} from mongodb")
        return mongodb_handler.delete_review(get_mongodb_connection(), user_id, vinyl_id)
    else:
        current_app.logger.debug(f"deletiong user review for user_id {user_id} and vinyl_id {vinyl_id} from mariadb")
        return mariadb_handler.delete_review(get_mariadb_connection(), user_id, vinyl_id)


def fetch_reviews_summary(start_date, end_date):
    if migrated:
        current_app.logger.debug(f"searching reviews from {start_date} to {end_date} from mongodb")
        return mongodb_handler.fetch_reviews_summary(get_mongodb_connection(), start_date, end_date)
    else:
        current_app.logger.debug(f"searching reviews from {start_date} to {end_date} from mariadb")
        return mariadb_handler.fetch_reviews_summary(get_mariadb_connection(), start_date, end_date)


def set_migrated(migrated_value):
    global migrated
    migrated = migrated_value


def get_users():
    if migrated:
        current_app.logger.debug(f"query user mongodb")
        return mongodb_handler.get_users(get_mongodb_connection())
    else:
        current_app.logger.debug(f"query user mariadb")
        return mariadb_handler.get_users(get_mariadb_connection())


def buy_vinyl(user_id, vinyl_id):
    if migrated:
        current_app.logger.debug(f"buying vinyal mongodb")
        return mongodb_handler.buy_vinyl(get_mongodb_connection(), user_id, vinyl_id)
    else:
        current_app.logger.debug(f"buying vinyal mongodb")
        return mariadb_handler.buy_vinyl(get_mariadb_connection(), user_id, vinyl_id)


def get_purchase_overview(artist_name, start_date, end_date, genre):

    if migrated:
        current_app.logger.debug(f"getting overview with mongodb")
        return mongodb_handler.get_purchase_overview(get_mongodb_connection(), artist_name, start_date, end_date, genre)
    else:
        current_app.logger.debug(f"getting overview with mariadb")
        return mariadb_handler.get_purchase_overview(get_mariadb_connection(), artist_name, start_date, end_date, genre)
