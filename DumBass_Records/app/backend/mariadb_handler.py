import pymysql
import app.app
from pymongo import MongoClient
from .data.api_extractor import get_data_from_api
from flask import current_app
import json
from flask import session
import datetime


def get_orders_for_user(mariadb_connection, user_id):
    try:
        cursor = mariadb_connection.cursor(pymysql.cursors.DictCursor)
        query = """
            SELECT
                O.Order_ID AS order_id,
                O.Order_Date AS order_date,
                O.Zahlungsmethode AS payment_method,
                O.Total_Price AS total_price,
                V.Vinyl_ID AS vinyl_id,
                V.Vinyl_Name AS vinyl_title,
                V.Price AS price,
                V.Cover_Image AS cover_image,
                V.Release_Date AS release_date,
                V.Genre AS genre,
                A.Artist_Name AS artist_name,
                A.Nationality AS nationality,
                OP.Amount AS amount
            FROM Orders O
            JOIN Order_Vinyl OP ON O.Order_ID = OP.Order_ID
            JOIN Vinyls V ON OP.Vinyl_ID = V.Vinyl_ID
            JOIN Artists A ON V.Artist_ID = A.Artist_ID
            WHERE O.User_ID = %s
            ORDER BY O.Order_Date DESC, O.Order_ID, V.Vinyl_Name;
        """
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        current_app.logger.debug(f"Orders for user_id {user_id}: {results}")

        orders = {}
        for row in results:
            order_id = row["order_id"]
            if order_id not in orders:
                orders[order_id] = {
                    "order_id": order_id,
                    "order_date": row["order_date"],
                    "payment_method": row["payment_method"],
                    "total_price": float(row["total_price"]),
                    "vinyls": [],
                }
            orders[order_id]["vinyls"].append(
                {
                    "vinyl_id": row["vinyl_id"],
                    "vinyl_title": row["vinyl_title"],
                    "price": float(row["price"]),
                    "cover_image": row["cover_image"],
                    "amount": row["amount"],
                    "release_date": row["release_date"],
                    "genre": row["genre"],
                    "artist_name": row["artist_name"],
                    "nationality": row["nationality"],
                }
            )
        orders_list = list(orders.values())

        mariadb_connection.close()
        return orders_list

    except Exception as e:
        current_app.logger.info(f"Error querying user Orders: {e}")
        return []


def query_review_by_user(connection, user_id, vinyl_id):
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        query = """
                SELECT 
                    Comment AS comment,
                    Rating AS rating,
                    Review_Date AS review_date
                FROM 
                    Reviews 
                WHERE 
                    User_ID = %s AND Vinyl_ID = %s
                LIMIT 1;
            """
        cursor.execute(query, (user_id, vinyl_id))
        review = cursor.fetchone()

        current_app.logger.debug(f"review found through mariadb {review}")
        return review
    except Exception as e:
        current_app.logger.debug(f"Error querying reviews: {e}")
        return None

    finally:
        connection.close()


def insert_review_for_vinyl(connection, user_id, vinyl_id, rating, review_text):
    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO Reviews (Vinyl_ID, User_ID, Rating, Comment, Review_Date)
            VALUES(%s,%s,%s,%s, CURDATE())
        """
        cursor.execute(query, (vinyl_id, user_id, rating, review_text))
        connection.commit()
    except Exception as e:
        current_app.logger.debug(
            f"Error isnerting into review user_id {user_id}, vinyl_id {vinyl_id} rating {rating}, review_text {review_text}: {e}"
        )
    finally:
        connection.close()
        cursor.close()


def delete_review(connection, user_id, vinyl_id):
    try:
        cursor = connection.cursor()
        query = """
            DELETE FROM Reviews
            WHERE User_ID = %s AND Vinyl_ID = %s
        """
        cursor.execute(query, (user_id, vinyl_id))
        affected_rows = cursor.rowcount
        connection.commit()

        if affected_rows > 0:
            return True
        else:
            return False
    except Exception as e:
        current_app.logger.error(f"Error deleting review for user_id {user_id}, vinyl_id {vinyl_id}: {e}")
        return False
    finally:
        cursor.close()
        connection.close()


def insert_vinyl(connection, artist_id, vinyl_name, vinyl_price, release_date, cover_image, genre):
    cursor = connection.cursor()
    query = """
            INSERT INTO Vinyls (Artist_ID, Vinyl_Name, Price, Release_Date, Cover_Image, Genre)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
    cursor.execute(query, (artist_id, vinyl_name, vinyl_price, release_date, cover_image, genre))
    connection.commit()
    current_app.logger.debug("Vinyl inserted successfully with MariaDB.")
    connection.close()


def search_vinyls(connection, query):
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        """
        SELECT 
            v.Vinyl_ID AS vinyl_id, 
            v.Vinyl_Name AS vinyl_title, 
            v.Price AS price, 
            v.Cover_Image AS cover_image, 
            a.Artist_Name AS artist_name,
            a.Artist_ID AS artist_id,
            v.Release_Date AS release_date, 
            v.Genre AS genre, 
            a.Nationality AS nationality
        FROM Vinyls v
        JOIN Artists a ON v.Artist_ID = a.Artist_ID
        WHERE 
            LOWER(v.Vinyl_Name) LIKE %s OR
            LOWER(a.Artist_Name) LIKE %s OR
            LOWER(v.Genre) LIKE %s
        LIMIT 20;
        """,
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    )
    results = cursor.fetchall()
    connection.close()
    return results


def search_vinyls_admin(connection, genre, artist, min_price, max_price, id):
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    query = """
            SELECT 
            v.Vinyl_ID AS vinyl_id, 
            v.Vinyl_Name AS vinyl_title,
            v.Price AS price,
            v.Cover_Image AS cover_image,
            a.Artist_Name AS artist_name,
            a.Artist_ID AS artist_id,
            v.Release_Date AS release_date,
            v.Genre AS genre,
            a.Nationality AS nationality
            FROM Vinyls v
            JOIN Artists a ON v.Artist_ID = a.Artist_ID
            WHERE (%s = '' OR v.Genre LIKE %s)
            AND (%s = '' OR a.Artist_Name LIKE %s)
        """
    params = [genre, f"%{genre}%", artist, f"%{artist}%"]

    if min_price:
        query += " AND v.Price >= %s"
        params.append(float(min_price))
    if max_price:
        query += " AND v.Price <= %s"
        params.append(float(max_price))

    if id:
        query += " AND v.Vinyl_ID = %s"
        params.append(int(id))

    cursor.execute(query, params)
    vinyls = cursor.fetchall()

    cursor.execute("SELECT DISTINCT Genre FROM Vinyls")
    genres = [row["Genre"] for row in cursor.fetchall()]
    connection.close()
    return vinyls, genres


def handle_login(connection, email, password):

    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Users WHERE User_Email = %s", (email,))
    user = cursor.fetchone()

    if user and user["User_Password"] == password:
        user_id = user["User_ID"]
        user_name = user["User_Name"]
        current_app.logger.debug(f"use_id {user_id}, user_name {user_name}")
        cursor.execute("SELECT * FROM Admins WHERE User_ID = %s", (user_id,))
        admin = cursor.fetchone()

        if admin:
            user_role = "admin"
            department = admin["Department"]
            session["department"] = department
        else:
            user_role = "customer"

        session["user_id"] = user_id
        session["user_name"] = user_name
        session["user_role"] = user_role

        current_app.logger.debug("Login successful!")
        return session
    else:
        current_app.logger.debug("Invalid email or password!")


def query_vinyls(connection, limit):
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        """
        SELECT 
            v.Vinyl_ID AS vinyl_id, 
            v.Vinyl_Name AS vinyl_title, 
            v.Price AS price, 
            v.Cover_Image AS cover_image, 
            a.Artist_Name AS artist_name,
            a.Artist_ID AS artist_id,
            v.Release_Date AS release_date, 
            v.Genre AS genre, 
            a.Nationality AS nationality
        FROM Vinyls v
        JOIN Artists a ON v.Artist_ID = a.Artist_ID
        ORDER BY RAND()
        LIMIT %s
        """,
        (limit,),
    )
    vinyls = cursor.fetchall()
    connection.close()
    return vinyls


def fetch_reviews_summary(mariadb_connection, start_date=None, end_date=None):
    try:
        cursor = mariadb_connection.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT
                v.Vinyl_ID AS vinyl_id,
                v.Vinyl_Name AS vinyl_title,
                v.Genre AS genre,
                a.Artist_Name AS artist_name,
                COUNT(r.Rating) AS amount_reviews,
                ROUND(AVG(r.Rating), 2) AS average_rating,
                SUM(CASE WHEN r.Rating = 1 THEN 1 ELSE 0 END) AS stars_1,
                SUM(CASE WHEN r.Rating = 2 THEN 1 ELSE 0 END) AS stars_2,
                SUM(CASE WHEN r.Rating = 3 THEN 1 ELSE 0 END) AS stars_3,
                SUM(CASE WHEN r.Rating = 4 THEN 1 ELSE 0 END) AS stars_4,
                SUM(CASE WHEN r.Rating = 5 THEN 1 ELSE 0 END) AS stars_5,
                JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'user_id', r.User_ID,
                        'rating', r.Rating,
                        'review_text', r.Comment,
                        'review_date', DATE_FORMAT(r.Review_Date, '%%Y-%%m-%%d')
                    )
                ) AS reviews_json
            FROM
                Vinyls v
            JOIN
                Reviews r ON v.Vinyl_ID = r.Vinyl_ID
            JOIN
                Artists a ON v.Artist_ID = a.Artist_ID
            WHERE
                (%s IS NULL OR r.Review_Date >= %s) AND
                (%s IS NULL OR r.Review_Date <= %s)
            GROUP BY
                v.Vinyl_ID, v.Vinyl_Name, v.Genre, a.Artist_Name
            HAVING
                COUNT(r.Rating) > 0
            ORDER BY
                average_rating DESC,
                amount_reviews DESC;
        """

        cursor.execute(query, (start_date, start_date, end_date, end_date))
        results = cursor.fetchall()

        for result in results:
            if isinstance(result["reviews_json"], str):
                try:
                    result["reviews_json"] = json.loads(result["reviews_json"])
                except json.JSONDecodeError as e:
                    current_app.logger.error(f"Error decoding JSON: {e}")
                    result["reviews_json"] = []

        return results

    except Exception as e:
        current_app.logger.error(f"Error querying review summary: {e}")
        return []

    finally:
        cursor.close()
        mariadb_connection.close()


def get_users(mariadb_connection):
    try:
        cursor = mariadb_connection.cursor(pymysql.cursors.DictCursor)

        query_admins = """
            SELECT 
                u.User_ID AS user_id,
                u.User_Name AS user_name,
                u.User_Email AS user_email,
                u.User_Password AS user_password,
                'admin' AS role,
                a.Department AS department
            FROM Users u
            JOIN Admins a ON u.User_ID = a.User_ID;
        """
        cursor.execute(query_admins)
        admins = cursor.fetchall()

        query_customers = """
            SELECT 
                u.User_ID AS user_id,
                u.User_Name AS user_name,
                u.User_Email AS user_email,
                u.User_Password AS user_password,
                'customer' AS role,
                c.Address AS address
            FROM Users u
            JOIN Customers c ON u.User_ID = c.User_ID;
        """
        cursor.execute(query_customers)
        customers = cursor.fetchall()

        users = {"admins": admins, "customers": customers}

        current_app.logger.debug(f"Fetched users: {users}")
        return users

    except Exception as e:
        current_app.logger.error(f"Error fetching users: {e}")
        return {"admins": [], "customers": []}

    finally:
        cursor.close()


def buy_vinyl(mariadb_connection, user_id, vinyl_id, amount=1):
    try:
        now = datetime.datetime.utcnow()
        cursor = mariadb_connection.cursor(pymysql.cursors.DictCursor)

        query = "SELECT Price FROM Vinyls WHERE Vinyl_ID = %s"
        cursor.execute(query, (vinyl_id,))
        vinyl = cursor.fetchone()

        if not vinyl:
            current_app.logger.error(f"Vinyl with ID {vinyl_id} not found.")
            return {"error": "Vinyl not found"}

        vinyl_price = vinyl["Price"]
        total_price = vinyl_price * amount

        query = """
            INSERT INTO Orders (User_ID, Order_Date, Zahlungsmethode, Total_Price)
            VALUES (%s, CURDATE(), %s, %s)
        """
        cursor.execute(query, (user_id, "Kreditkarte", total_price))
        order_id = cursor.lastrowid

        query = """
            INSERT INTO Order_Vinyl (Order_ID, Vinyl_ID, Amount)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (order_id, vinyl_id, amount))

        mariadb_connection.commit()

        cursor.close()
        return {"success": f"Order {order_id} placed successfully"}

    except Exception as e:
        mariadb_connection.rollback()
        current_app.logger.error(f"Error buying vinyl: {e}")
        return {"error": str(e)}

    finally:
        if cursor:
            cursor.close()
        if mariadb_connection:
            mariadb_connection.close()


def get_purchase_overview(mariadb_connection, artist_name=None, start_date=None, end_date=None, genre=None):
    try:
        cursor = mariadb_connection.cursor(pymysql.cursors.DictCursor)

        query_summary = """
            SELECT
                v.Genre,
                COUNT(DISTINCT v.Vinyl_ID) AS vinyl_count,
                SUM(ov.Amount) AS total_purchase,
                SUM(ov.Amount * v.Price) AS total_revenue
            FROM Vinyls v
            JOIN Artists a ON v.Artist_ID = a.Artist_ID
            JOIN Order_Vinyl ov ON v.Vinyl_ID = ov.Vinyl_ID
            JOIN Orders o ON ov.Order_ID = o.Order_ID
            WHERE (%s IS NULL OR a.Artist_Name = %s)
            AND (%s IS NULL OR o.Order_Date BETWEEN %s AND %s)
            AND (%s IS NULL OR v.Genre = %s)
            GROUP BY v.Genre
            ORDER BY total_purchase DESC;
        """
        params_summary = [artist_name, artist_name, start_date, start_date, end_date, genre, genre]
        cursor.execute(query_summary, params_summary)
        summary_data = cursor.fetchall()

        query_details = """
            SELECT
                v.Vinyl_Name,
                a.Artist_Name,
                v.Genre,
                SUM(ov.Amount) AS Total_Sales,
                SUM(ov.Amount * v.Price) AS Total_Revenue
            FROM Vinyls v
            JOIN Artists a ON v.Artist_ID = a.Artist_ID
            JOIN Order_Vinyl ov ON v.Vinyl_ID = ov.Vinyl_ID
            JOIN Orders o ON ov.Order_ID = o.Order_ID
            WHERE (%s IS NULL OR a.Artist_Name = %s)
            AND (%s IS NULL OR o.Order_Date BETWEEN %s AND %s)
            AND (%s IS NULL OR v.Genre = %s)
            GROUP BY v.Vinyl_ID, a.Artist_Name
            ORDER BY Total_Sales DESC;
        """
        params_details = [artist_name, artist_name, start_date, start_date, end_date, genre, genre]
        cursor.execute(query_details, params_details)
        details_data = cursor.fetchall()

        return summary_data, details_data

    except Exception as e:
        current_app.logger.error(f"Error in get_purchase_overview: {e}")
        return [], []

    finally:
        cursor.close()
