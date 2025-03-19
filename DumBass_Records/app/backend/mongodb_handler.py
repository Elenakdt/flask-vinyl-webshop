import app.app
from pymongo import MongoClient
from .data.api_extractor import get_data_from_api
from flask import session, current_app
from bson.regex import Regex
from datetime import datetime, date
import json
from pymongo.collection import Collection
from typing import Optional, Tuple, List, Dict, Union
from datetime import datetime


def query_vinyls(mongodb_connection, limit):
    collection = mongodb_connection["vinyls"]
    projection = {
        "vinyl_id": "$_id",
        "artist_id": "$artist._id",
        "artist_name": "$artist.artist_name",
        "nationality": "$artist.nationality",
        "vinyl_title": 1,
        "price": 1,
        "cover_image": 1,
        "release_date": 1,
        "genre": 1,
    }
    current_app.logger.info(collection.find({}, projection))
    return collection.find({}, projection).limit(limit)


def get_orders_for_user(mongodb_connection, user_id):
    try:
        collection = mongodb_connection["orders"]

        query = {"user_id": user_id}

        projection = {
            "oder_id": "$_id",
            "user_id": 1,
            "order_date": 1,
            "payment_method": 1,
            "total_price": 1,
            "vinyls.vinyl_id": 1,
            "vinyls.amount": 1,
            "vinyls.vinyl_details.vinyl_title": 1,
            "vinyls.vinyl_details.price": 1,
            "vinyls.vinyl_details.cover_image": 1,
            "vinyls.vinyl_details.genre": 1,
            "vinyls.artist_details.artist_name": 1,
            "vinyls.artist_details.nationality": 1,
        }

        results = list(collection.find(query, projection).sort([("order_date", -1), ("_id", 1)]))

        orders = []
        for order in results:
            orders.append(
                {
                    "order_id": order["_id"],
                    "order_date": order["order_date"],
                    "payment_method": order["payment_method"],
                    "total_price": order["total_price"],
                    "vinyls": [
                        {
                            "vinyl_id": vinyl.get("vinyl_id"),
                            "vinyl_title": vinyl.get("vinyl_details", {}).get("vinyl_title"),
                            "price": vinyl.get("vinyl_details", {}).get("price"),
                            "cover_image": vinyl.get("vinyl_details", {}).get("cover_image"),
                            "amount": vinyl.get("amount"),
                            "genre": vinyl.get("vinyl_details", {}).get("genre"),
                            "artist_name": vinyl.get("artist_details", {}).get("artist_name"),
                            "nationality": vinyl.get("artist_details", {}).get("nationality"),
                        }
                        for vinyl in order.get("vinyls", [])
                    ],
                }
            )

        current_app.logger.debug(f"Orders for user_id {user_id}: {orders}")
        return orders

    except Exception as e:
        current_app.logger.error(f"Error querying user Orders: {e}")
        return []


def handle_login(mongodb_connection, email, password):
    collection = mongodb_connection["users"]

    user = collection.find_one({"user_email": email})

    if user and user["user_password"] == password:
        user_id = user["_id"]
        user_name = user["user_name"]
        user_role = user["role"]

        current_app.logger.debug(f"mongoDB: user_id: {user_id}, user_name: {user_name}, role: {user_role}")

        if user_role == "admin":
            admin_details = user.get("admin_details", {})
            department = admin_details.get("department", "Unknown")
            session["department"] = department
        elif user_role == "customer":
            customer_details = user.get("customer_details", {})
            address = customer_details.get("address", "Unknown")
            current_app.logger.debug(f"Customer address: {address}")

        session["user_id"] = user_id
        session["user_name"] = user_name
        session["user_role"] = user_role
        current_app.logger.debug("Login successful!")
        return session
    else:
        current_app.logger.debug("Invalid email or password!")


def search_vinyls(mongodb_connection, query):
    collection = mongodb_connection["vinyls"]
    regex_pattern = Regex(f".*{query}.*", "i")
    query = {"$or": [{"vinyl_title": regex_pattern}, {"artist.artist_name": regex_pattern}, {"genre": regex_pattern}]}

    projection = {
        "vinyl_id": "$_id",
        "artist_id": "$artist._id",
        "artist_name": "$artist.artist_name",
        "nationality": "$artist.nationality",
        "vinyl_title": 1,
        "price": 1,
        "cover_image": 1,
        "release_date": 1,
        "genre": 1,
    }

    current_app.logger.info(f"query results found: {len(list(collection.find(query,projection)))}")
    return list(collection.find(query, projection))


def search_vinyls_admin(mongodb_connection, genre, artist, min_price, max_price, vinyl_id):
    collection = mongodb_connection["vinyls"]
    query = {}

    if genre:
        query["genre"] = {"$regex": f".*{genre}.*", "$options": "i"}
    if artist:
        query["artist.artist_name"] = {"$regex": f".*{artist}.*", "$options": "i"}
    if min_price and min_price.strip():
        query["price"] = {"$gte": float(min_price)}

    if max_price and max_price.strip():
        query.setdefault("price", {}).update({"$lte": float(max_price)})
    if vinyl_id:
        query["_id"] = int(vinyl_id)

    projection = {
        "vinyl_id": "$_id",
        "artist_id": "$artist._id",
        "artist_name": "$artist.artist_name",
        "nationality": "$artist.nationality",
        "vinyl_title": 1,
        "price": 1,
        "cover_image": 1,
        "release_date": 1,
        "genre": 1,
    }

    current_app.logger.info(f"Executing query: {query}")
    vinyls = list(collection.find(query, projection))
    genres = collection.distinct("genre")
    return vinyls, genres


def insert_vinyl(mongodb_connection, artist_id, vinyl_name, vinyl_price, release_date, cover_image, genre):
    collection = mongodb_connection["vinyls"]

    existing_artist = collection.find_one(
        {"artist._id": int(artist_id)}, {"artist.artist_name": 1, "artist.nationality": 1}
    )

    formatted_release_date = datetime.strftime("%Y-%m-%d", release_date)

    if not existing_artist:
        current_app.logger.error(f"Artist with ID {artist_id} not found in Vinyls collection.")
        raise ValueError(f"Artist with ID {artist_id} not found in Vinyls collection.")

    artist_name = existing_artist["artist"]["artist_name"]
    nationality = existing_artist["artist"]["nationality"]

    vinyl_document = {
        "artist": {
            "_id": artist_id,
            "artist_name": artist_name,
            "nationality": nationality,
        },
        "vinyl_title": vinyl_name,
        "price": float(vinyl_price),
        "release_date": formatted_release_date,
        "cover_image": cover_image,
        "genre": genre,
    }

    result = collection.insert_one(vinyl_document)
    current_app.logger.debug(f"Vinyl inserted successfully. Inserted ID: {result.inserted_id}")

    return result.inserted_id


def insert_review_for_vinyl(mongodb_connection, user_id, vinyl_id, rating, review_text):
    reviews_collection = mongodb_connection["reviews"]
    review = {
        "vinyl_id": int(vinyl_id),
        "user_id": int(user_id),
        "rating": int(rating),
        "comment": review_text,
        "review_date": datetime.utcnow(),
    }
    reviews_collection.insert_one(review)
    current_app.logger.debug(f"Review inserted: {review}")


def query_review_by_user(mongodb_connection, user_id, vinyl_id):
    reviews_collection = mongodb_connection["reviews"]
    query = {"user_id": int(user_id), "vinyl_id": int(vinyl_id)}
    review = reviews_collection.find_one(query, {"_id": 0, "comment": 1, "rating": 1, "review_date": 1})
    current_app.logger.debug(f"review found through mongodb {review}")
    return review


def delete_review(mongodb_connection, user_id, vinyl_id):
    try:
        reviews_collection = mongodb_connection["reviews"]
        query = {"user_id": int(user_id), "vinyl_id": int(vinyl_id)}
        result = reviews_collection.delete_one(query)
        if result.deleted_count > 0:
            current_app.logger.info(f"Review deleted for user_id {user_id}, vinyl_id {vinyl_id}")
            return True
        else:
            current_app.logger.info(f"No review found for user_id {user_id}, vinyl_id {vinyl_id}")
            return False

    except Exception as e:
        current_app.logger.error(f"Error deleting review for user_id {user_id}, vinyl_id {vinyl_id}: {e}")
        return False


def fetch_reviews_summary(mongodb_connection, start_date=None, end_date=None):
    pipeline = []

    if isinstance(start_date, date):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, date):
        end_date = end_date.strftime("%Y-%m-%d")
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            date_filter["$lte"] = datetime.strptime(end_date, "%Y-%m-%d")
        pipeline.append({"$match": {"review_date": date_filter}})

    pipeline.extend(
        [
            {
                "$lookup": {
                    "from": "vinyls",
                    "localField": "vinyl_id",
                    "foreignField": "_id",
                    "as": "vinyl_details",
                }
            },
            {"$unwind": {"path": "$vinyl_details", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "artists",
                    "localField": "vinyl_details.artist._id",
                    "foreignField": "_id",
                    "as": "artist_details",
                }
            },
            {"$unwind": {"path": "$artist_details", "preserveNullAndEmptyArrays": True}},
        ]
    )

    pipeline.append(
        {
            "$group": {
                "_id": "$vinyl_id",
                "vinyl_title": {"$first": "$vinyl_details.vinyl_title"},
                "artist_name": {"$first": "$artist_details.artist_name"},
                "genre": {"$first": "$vinyl_details.genre"},
                "amount_reviews": {"$sum": 1},
                "average_rating": {"$avg": "$rating"},
                "stars_1": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}},
                "stars_2": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}},
                "stars_3": {"$sum": {"$cond": [{"$eq": ["$rating", 3]}, 1, 0]}},
                "stars_4": {"$sum": {"$cond": [{"$eq": ["$rating", 4]}, 1, 0]}},
                "stars_5": {"$sum": {"$cond": [{"$eq": ["$rating", 5]}, 1, 0]}},
                "reviews_json": {
                    "$push": {
                        "user_id": "$user_id",
                        "rating": "$rating",
                        "review_text": "$comment",
                        "review_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$review_date"}},
                    }
                },
            }
        }
    )

    pipeline.extend(
        [
            {"$match": {"amount_reviews": {"$gt": 0}}},
            {"$sort": {"average_rating": -1, "amount_reviews": -1}},
        ]
    )

    try:
        reviews_collection = mongodb_connection["reviews"]
        results = list(reviews_collection.aggregate(pipeline))

        for result in results:
            result["average_rating"] = round(float(result["average_rating"]), 2) if result["average_rating"] else 0.0

        return results
    except Exception as e:
        current_app.logger.error(f"Error executing MongoDB pipeline: {e}")
        return []


def get_purchase_overview(
    mongodb_connection: MongoClient,
    artist_name: Optional[str] = None,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    genre: Optional[str] = None,
) -> Tuple[List[Dict], List[Dict]]:
    try:
        orders_col = mongodb_connection["orders"]

        # **Fix empty strings from form**
        if not start_date or start_date.strip() == "":
            start_date = None
        if not end_date or end_date.strip() == "":
            end_date = None

        # **Ensure Dates Are in BSON Format**
        formated_start_date = None
        formated_end_date = None
        try:
            if start_date:
                formated_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                formated_end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            current_app.logger.error(f"Invalid date format: {e}")
            return [], []  # Return empty results if the dates are invalid

        # **Log formatted dates instead of raw inputs**
        current_app.logger.info(f"Time filter: {formated_start_date} - {formated_end_date}")

        # **Build Query**
        match_criteria = {}
        if artist_name and artist_name.strip():
            match_criteria["vinyls.artist_details.artist_name"] = artist_name.strip()
        if genre and genre.strip():
            match_criteria["vinyls.vinyl_details.genre"] = genre.strip()
        if formated_start_date or formated_end_date:
            order_date_filter = {}
            if formated_start_date:
                order_date_filter["$gte"] = formated_start_date
            if formated_end_date:
                order_date_filter["$lte"] = formated_end_date
            match_criteria["order_date"] = order_date_filter

        # **Summary Pipeline**
        summary_pipeline = [
            {"$unwind": "$vinyls"},
            {"$match": match_criteria},
            {
                "$group": {
                    "_id": "$vinyls.vinyl_details.genre",
                    "vinyl_count": {"$push": "$vinyls.vinyl_id"},
                    "total_purchase": {"$sum": "$vinyls.amount"},
                    "total_revenue": {"$sum": {"$multiply": ["$vinyls.amount", "$vinyls.vinyl_details.price"]}},
                }
            },
            {
                "$project": {
                    "Genre": "$_id",
                    "vinyl_count": {"$size": "$vinyl_count"},
                    "total_purchase": 1,
                    "total_revenue": 1,
                    "_id": 0,
                }
            },
            {"$sort": {"total_purchase": -1}},
        ]

        summary_data = list(orders_col.aggregate(summary_pipeline))

        # **Details Pipeline**
        details_pipeline = [
            {"$unwind": "$vinyls"},
            {"$match": match_criteria},
            {
                "$group": {
                    "_id": {
                        "vinyl_id": "$vinyls.vinyl_id",
                        "Vinyl_name": "$vinyls.vinyl_details.vinyl_title",
                        "Artist_name": "$vinyls.artist_details.artist_name",
                        "Genre": "$vinyls.vinyl_details.genre",
                    },
                    "Total_Sales": {"$sum": "$vinyls.amount"},
                    "Total_Revenue": {"$sum": {"$multiply": ["$vinyls.amount", "$vinyls.vinyl_details.price"]}},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "Vinyl_Name": "$_id.Vinyl_name",
                    "Artist_Name": "$_id.Artist_name",
                    "Genre": "$_id.Genre",
                    "Total_Sales": 1,
                    "Total_Revenue": 1,
                }
            },
            {"$sort": {"Total_Sales": -1}},
        ]

        details_data = list(orders_col.aggregate(details_pipeline))

        return summary_data, details_data

    except Exception as e:
        current_app.logger.error(f"Error in get_purchase_overview: {e}")
        return [], []


from bson.objectid import ObjectId


def buy_vinyl(mongodb_connection, user_id, vinyl_id, amount=1):
    try:
        vinyls_col = mongodb_connection["vinyls"]
        orders_col = mongodb_connection["orders"]

        # Fetch the vinyl document to get the price
        vinyl = vinyls_col.find_one({"_id": int(vinyl_id)})
        if not vinyl:
            current_app.logger.error(f"Vinyl with ID {vinyl_id} not found.")
            return {"error": "Vinyl not found"}

        vinyl_price = vinyl["price"]
        total_price = vinyl_price * amount

        last_order = orders_col.find_one({}, sort=[("_id", -1)])
        current_app.logger.error(f"last {last_order['_id']}")
        last_id = last_order["_id"]
        new_id = int(last_id) + 1
        order_document = {
            "_id": int(new_id),
            "user_id": int(user_id),
            "order_date": datetime.utcnow(),
            "payment_method": "Kreditkarte",  # Hardcoded as per original function
            "total_price": total_price,
            "vinyls": [
                {
                    "vinyl_id": int(vinyl_id),
                    "amount": amount,
                    "vinyl_details": {
                        "price": vinyl_price,
                        "vinyl_title": vinyl["vinyl_title"],
                        "cover_image": vinyl["cover_image"],
                        "genre": vinyl["genre"],
                    },
                    "artist_details": {
                        "artist_id": int(vinyl["artist"]["_id"]),
                        "artist_name": vinyl["artist"]["artist_name"],
                        "nationality": vinyl["artist"]["nationality"],
                    },
                }
            ],
        }

        # Insert the order into the Orders collection
        result = orders_col.insert_one(order_document)
        order_id = result.inserted_id

        current_app.logger.debug(f"Order {order_id} placed successfully.")

        return {"success": f"Order {order_id} placed successfully"}

    except Exception as e:
        current_app.logger.error(f"Error buying vinyl: {e}")
        return {"error": str(e)}
