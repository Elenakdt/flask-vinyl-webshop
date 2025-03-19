import json
from datetime import datetime
import os
import pymysql
from pymongo import errors, ASCENDING, ASCENDING
from flask import current_app
import pymongo


def create_collections_with_schemas(mongodb_connection):
    drop_mongo_db(mongodb_connection)
    schemas = load_schemas()
    for schema in schemas:
        try:
            mongodb_connection.create_collection(
                schema, validator=schemas[schema], validationLevel="strict", validationAction="error"
            )
            current_app.logger.info(f"Collection {schema} created.")
        except errors.CollectionInvalid as e:
            current_app.logger.info(f"failed to create {schema} {e}")


def drop_mongo_db(mongodb_connection):
    client = mongodb_connection.client
    client.drop_database(mongodb_connection.name)
    current_app.logger.info(f"Database {mongodb_connection.name} has been dropped successfully.")


def load_schemas():
    schemas = {}
    schemas["vinyls"] = load_schema("vinyls_artists")
    schemas["users"] = load_schema("users")
    schemas["orders"] = load_schema("orders")
    schemas["reviews"] = load_schema("reviews")
    return schemas


def load_schema(schema_name):
    file_path = os.path.join(os.path.dirname(__file__), f"mongodb_schema/{schema_name}.json")
    with open(file_path, "r") as file:
        return json.load(file)


def fill_mongodb(mongodb_connection, mariadb_connection):
    artists = fetch_artist(mariadb_connection)
    vinyls = fetch_vinyls(mariadb_connection)
    users = fetch_users(mariadb_connection)
    orders = fetch_orders(mariadb_connection)
    reviews = fetch_reviews(mariadb_connection)
    transformed_vinyls = transform_vinyls(vinyls, artists)
    insert_vinyls(mongodb_connection, transformed_vinyls)
    transformed_users = transform_users(users, mariadb_connection)
    insert_users(mongodb_connection, transformed_users)
    transformed_orders = transform_orders(orders, mariadb_connection)
    insert_orders(mongodb_connection, transformed_orders)
    transformed_reviews = transform_reviews(reviews)
    insert_reviews(mongodb_connection, transformed_reviews)


def insert_users(mongodb_connection, users):
    if not users:
        current_app.logger.warning("No users to insert.")
        return
    mongodb_connection.users.insert_many(users, ordered=False)
    current_app.logger.info(f"Inserted {len(users)} users into MongoDB.")


def insert_vinyls(mongodb_connection, vinyls):
    if not vinyls:
        current_app.logger.error("No vinyls to insert.")
        return
    mongodb_connection.vinyls.insert_many(vinyls, ordered=False)
    current_app.logger.debug(f"Inserted {len(vinyls)} vinyls into MongoDB.")


def transform_vinyls(vinyls, artists_dict):
    transformed = []
    for vinyl in vinyls:
        artist = artists_dict.get(vinyl["Artist_ID"], {})

        release_date = vinyl["Release_Date"]
        release_date = datetime.combine(release_date, datetime.min.time())

        vinyl_doc = {
            "_id": int(vinyl.get("Vinyl_ID")),
            "vinyl_title": vinyl.get("Vinyl_Name"),
            "price": float(vinyl.get("Price", 0.0)),
            "release_date": release_date,
            "cover_image": vinyl.get("Cover_Image"),
            "genre": vinyl.get("Genre"),
            "artist": {
                "_id": int(vinyl.get("Artist_ID")),
                "artist_name": artist.get("Artist_Name"),
                "nationality": artist.get("Nationality"),
            },
        }
        transformed.append(vinyl_doc)
    return transformed


def transform_users(users, mariadb_connection):
    transformed = []
    for user in users:
        user_id = int(user["User_ID"])
        user_name = user["User_Name"]
        user_email = user["User_Email"]
        user_password = user["User_Password"]
        admin_details = fetch_admin_details(user_id, mariadb_connection)
        customer_details = fetch_customer_details(user_id, mariadb_connection)

        if admin_details:
            role = "admin"
        elif customer_details:
            role = "customer"
        else:
            role = "unknown"
        user_doc = {
            "_id": int(user.get("User_ID")),
            "user_name": user_name,
            "user_email": user_email,
            "user_password": user_password,
            "role": role,
        }

        if role == "admin" and admin_details:
            user_doc["admin_details"] = admin_details
        else:
            user_doc["customer_details"] = customer_details

        transformed.append(user_doc)
    return transformed


def transform_orders(orders, mariadb_connection):
    transformed = []
    all_vinyls = fetch_vinyls(mariadb_connection)
    vinyls_dict = {vinyl["Vinyl_ID"]: vinyl for vinyl in all_vinyls}

    artists_dict = fetch_artist(mariadb_connection)

    for order in orders:
        order_id = int(order["Order_ID"])
        user_id = int(order["User_ID"])
        order_date = order["Order_Date"]
        payment_method = order["Zahlungsmethode"]
        total_price = float(order.get("Total_Price", 0.0))

        order_date = datetime.combine(order_date, datetime.min.time())

        vinyls = fetch_order_vinyls(order_id, mariadb_connection)
        transformed_vinyls = []
        for vinyl in vinyls:
            vinyl_id = int(vinyl["Vinyl_ID"])
            amount = int(vinyl["Amount"])
            vinyl_info = vinyls_dict.get(vinyl_id, {})
            artist_info = artists_dict.get(vinyl_info.get("Artist_ID"), {})
            transformed_vinyls.append(
                {
                    "vinyl_id": vinyl_id,
                    "amount": amount,
                    "vinyl_details": {
                        "vinyl_title": vinyl_info.get("Vinyl_Name", "Unknown Title"),
                        "price": float(vinyl_info.get("Price", 0.0)),
                        "cover_image": vinyl_info.get("Cover_Image"),
                        "genre": vinyl_info.get("Genre"),
                    },
                    "artist_details": {
                        "artist_id": int(artist_info.get("Artist_ID", 0)),
                        "artist_name": artist_info.get("Artist_Name", "Unknown Artist"),
                        "nationality": artist_info.get("Nationality", "Unknown"),
                    },
                }
            )
        order_doc = {
            "_id": order_id,
            "user_id": user_id,
            "order_date": order_date,
            "payment_method": payment_method,
            "total_price": total_price,
            "vinyls": transformed_vinyls,
        }
        transformed.append(order_doc)
    return transformed


def transform_reviews(reviews):
    transformed = []
    for review in reviews:
        user_id = int(review["User_ID"])
        vinyl_id = int(review["Vinyl_ID"])
        comment = review.get("Comment", "")
        rating = int(review["Rating"])
        review_date = review["Review_Date"]

        review_date = datetime.combine(review_date, datetime.min.time())

        review_doc = {
            "user_id": int(user_id),
            "vinyl_id": int(vinyl_id),
            "comment": comment,
            "rating": int(rating),
            "review_date": review_date,
        }
        transformed.append(review_doc)
    return transformed


def insert_orders(mongodb_connection, orders):
    if not orders:
        current_app.logger.warning("No orders to insert.")
        return
    mongodb_connection.orders.insert_many(orders, ordered=False)
    current_app.logger.info(f"Inserted {len(orders)} orders into MongoDB.")


def insert_reviews(mongodb_connection, reviews):
    if not reviews:
        current_app.logger.warning("No reviews to insert.")
        return
    mongodb_connection.reviews.insert_many(reviews, ordered=False)
    current_app.logger.info(f"Inserted {len(reviews)} reviews into MongoDB.")
    mongodb_connection.reviews.create_index(
        [("user_id", pymongo.ASCENDING), ("vinyl_id", pymongo.ASCENDING)], unique=True
    )


def fetch_artist(mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM Artists")
        artists = cursor.fetchall()
    return {artist["Artist_ID"]: artist for artist in artists}


def fetch_vinyls(mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM Vinyls")
        return cursor.fetchall()


def fetch_users(mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM Users")
        users = cursor.fetchall()
    return users


def fetch_admin_details(user_id, mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT Department FROM Admins WHERE User_ID = %s", (user_id,))
        admin = cursor.fetchone()
    if admin:
        return {"department": admin["Department"]}
    return None


def fetch_customer_details(user_id, mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT Address FROM Customers WHERE User_ID = %s", (user_id,))
        customer = cursor.fetchone()
    if customer:
        return {"address": customer["Address"]}
    return None


def fetch_orders(mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM Orders")
        orders = cursor.fetchall()
    return orders


def fetch_order_vinyls(order_id, mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM Order_Vinyl WHERE Order_ID = %s", (order_id,))
        order_vinyls = cursor.fetchall()
    return order_vinyls


def fetch_reviews(mariadb_connection):
    with mariadb_connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM Reviews")
        reviews = cursor.fetchall()
    return reviews
