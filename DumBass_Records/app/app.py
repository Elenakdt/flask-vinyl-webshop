from app.backend import mariadb_handler
from app.backend import mariadb_initializer
from app.backend import mongodb_initializer
from app.backend import database_handler
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import mariadb
from datetime import datetime
import pymysql
import sys
from flask import request
from pymongo import MongoClient

app = Flask(__name__)

# MARIADB Credentials
app.config["MARIADB"] = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "name": os.getenv("DB_NAME", "my_database"),
    "user": os.getenv("DB_USER", "my_user"),
    "password": os.getenv("DB_PASSWORD", "my_password"),
}

# MONGODB Credentials
app.config["MONGODB"] = {
    "host": os.getenv("MONGO_HOST", "localhost"),
    "port": int(os.getenv("MONGO_PORT", 27017)),
    "db": os.getenv("MONGO_DB", "my_mongo_database"),
}

app.secret_key = "funny_secret_key"


def get_mariadb_connection():
    try:
        mariadb_config = app.config["MARIADB"]
        connection = pymysql.connect(
            host=mariadb_config["host"],
            port=mariadb_config["port"],
            user=mariadb_config["user"],
            password=mariadb_config["password"],
            database=mariadb_config["name"],
        )
        return connection
    except pymysql.MySQLError as e:
        app.logger.error(f"MARIADB Database Error: {e}")
        sys.exit(1)


def get_mongodb_connection():
    mongo_config = app.config["MONGODB"]
    client = MongoClient(host=mongo_config["host"], port=mongo_config["port"])
    app.logger.info(f"Connected to MongoDB database '{mongo_config['db']}' successfully.")
    db = client[mongo_config["db"]]
    return db


initialized = False
migrated = False


@app.route("/")
def display_home():
    app.logger.info("Handling request to '/'")
    database_handler.initialize_db()
    vinyls = database_handler.query_vinyls(100)
    return render_template("views/home.html", vinyls=vinyls)


@app.route("/migrate_to_no_sql", methods=["POST"])
def migrate_to_no_sql():
    app.logger.info("Migrating to No SQL")
    try:
        database_handler.handle_migration()
        return jsonify({"success": "successfully migrated data"}), 200
    except Exception as e:
        return jsonify({"error": f"error while migrating {e}"}), 500


@app.route("/erase_and_fill_db", methods=["POST"])
def erase_and_fill_db():
    app.logger.info("Handling: Erase and fill DB")
    database_handler.erase_and_fill_db()
    return {"message": "Database erased and filled successfully!"}, 200


@app.route("/shop")
def vinyl_list():
    vinyls = database_handler.query_vinyls(100)
    return render_template("views/shop.html", vinyls=vinyls)


@app.route("/search", methods=["GET"])
def search():
    app.logger.info("Handling search query")
    query = request.args.get("q", "").lower()
    results = database_handler.search_vinyls(query)
    return {"results": results}, 200


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    try:
        app.logger.info(f"cought information from login  {email}, {password}")
        app.session = database_handler.handle_login(email, password)
        if app.session["user_role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("user_dashboard"))

    except Exception as e:
        app.logger.error(f"Error while logging in: {e}")
        flash(f"An error occurred: {e}", "danger")
    return redirect(url_for("display_home"))


@app.route("/admin_dashboard", methods=["GET"])
def admin_dashboard():
    if "user_role" not in session or session["user_role"] != "admin":
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for("display_home"))

    genre = request.args.get("genre", "").strip()
    artist = request.args.get("artist", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    id = request.args.get("id", "").strip()

    try:
        vinyls, genres = database_handler.search_vinyls_admin(genre, artist, min_price, max_price, id)
    except Exception as e:
        app.logger.error(f"Error while retrieving admin data: {e}")
        vinyls, genres = [], []
    return render_template("views/admin_dashboard.html", vinyls=vinyls, genres=genres)


@app.route("/add_vinyl", methods=["POST"])
def add_vinyl():
    artist_id = request.form.get("artist_id")
    vinyl_name = request.form.get("vinyl_name")
    vinyl_price = request.form.get("vinyl_price")
    release_date = request.form.get("release_date")
    cover_image = request.form.get("cover_image")
    genre = request.form.get("genre")

    app.logger.debug(f"{artist_id}, {vinyl_name}, {vinyl_price}, {release_date}, {cover_image}, {genre}")
    if not artist_id or not vinyl_name or not vinyl_price or not release_date or not cover_image or not genre:
        return jsonify({"error": "Missing required fields."}), 400
    try:
        database_handler.insert_vinyl(artist_id, vinyl_name, vinyl_price, release_date, cover_image, genre)
        return jsonify({"success": "insert successfull"}), 200
    except Exception as e:
        app.logger.error(f"exception in add_vinyl {e}")
        return jsonify({"error": f"insert failed"}), 500


@app.route("/user_dashboard")
def user_dashboard():
    user_id = session["user_id"]
    role = session["user_role"]
    app.logger.debug(f"User ID {user_id}, user_role {role} ")
    if "user_role" not in session or session["user_role"] != "customer":
        return redirect(url_for("display_home"))

    orders = database_handler.get_orders_for_user(session["user_id"])
    return render_template("views/user_dashboard.html", orders=orders)


@app.route("/submit_review", methods=["POST"])
def submit_review():
    data = request.get_json()
    vinyl_id = data.get("vinyl_id")
    user_id = session["user_id"]
    rating = data.get("rating")
    review_text = data.get("review_text")
    if not user_id or not vinyl_id or not rating or not review_text:
        return jsonify({"error": "Missing required fields."}), 400

    app.logger.info(f"Review received: Vinyl ID={vinyl_id}, Rating={rating}, Review Text={review_text}")

    try:
        existing_review = database_handler.query_review_by_user(user_id, vinyl_id)

        if existing_review:
            return jsonify({"error": "You have already reviewed this vinyl."}), 400

        database_handler.insert_review_for_vinyl(user_id, vinyl_id, rating, review_text)

        return jsonify({"message": "Review submitted successfully!"}), 200
    except Exception as e:
        app.logger.error(f"Error submitting review for user_id {user_id}, vinyl_id {vinyl_id}: {e}")
        return jsonify({"error": "An error occurred while submitting your review."}), 500


@app.route("/check_review", methods=["GET"])
def check_review():
    user_id = session.get("user_id")
    vinyl_id = request.args.get("vinyl_id")
    app.logger.debug(f"userId {user_id}, vinylId {vinyl_id}")

    if not user_id or not vinyl_id:
        return jsonify({"error": "Missing user_id or vinyl_id"}), 400
    try:
        review = database_handler.query_review_by_user(user_id, vinyl_id)
        if review:
            return (
                jsonify(
                    {
                        "review_exists": True,
                        "comment": review["comment"],
                        "rating": review["rating"],
                        "review_date": review["review_date"],
                    }
                ),
                200,
            )
        else:
            return jsonify({"review_exists": False}), 200
    except Exception as e:
        return jsonify({"error": f"Some exception in check review, im tired, boss {e}"})


@app.route("/delete_review", methods=["POST"])
def delete_review():
    user_id = session.get("user_id")
    vinyl_id = request.get_json().get("vinyl_id")
    app.logger.debug(f"ddelete review userId {user_id}, vinylId {vinyl_id}")

    if not user_id or not vinyl_id:
        return jsonify({"error": "Missing user_id or vinyl_id"}), 400
    try:
        deletion = database_handler.delete_review(user_id, vinyl_id)
        if deletion:
            return jsonify({"success": "Deleted the review, thanks for nothing, man."}), 200
        else:
            return jsonify({"error": "Didnt delete review, how sad..."}), 501
    except Exception as e:
        return jsonify({"error": f"Delete Failed {e}"}), 500


def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@app.route("/best_rated", methods=["GET"])
def best_rated():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    start_date = validate_date(start_date)
    end_date = validate_date(end_date)

    try:
        results = database_handler.fetch_reviews_summary(start_date, end_date)
        app.logger.debug(f"Fetched results: {results}")
        return render_template(
            "views/best_rated.html",
            results=results,
        )
    except Exception as e:
        app.logger.error(f"Error fetching reviews summary: {e}")
        return render_template("views/best_rated.html", results=[]), 500


@app.route("/buy_vinyl", methods=["POST"])
def buy_vinyl():
    vinyl_id = request.get_json().get("vinyl_id")
    user_id = session.get("user_id")
    app.logger.info(f"user_id {user_id}")
    if user_id is None:
        return jsonify({"warning": "Please Log in before purchasing an item. Who do you think you are?"})

    if app.session["user_role"] == "admin":
        return jsonify({"warning": "Hey you are an admin you cant buy a vinyl, listen to spotify or relog as user"})
    app.logger.info(f"ITEM ID ITEM ID: {vinyl_id}")
    try:
        database_handler.buy_vinyl(user_id, vinyl_id)
    except Exception as e:
        return jsonify({"error": f"something silly going one here, here is the error message {e}"}), 500
    finally:
        return jsonify({"success": "yay it worked i guess..."})


@app.route("/logout", methods=["GET"])
def logout():
    if session.get("user_id") is None:
        return jsonify({"warning": "Man, you havent even logged in yet, who you trying to logout ?"}), 500
    session.clear()
    return jsonify({"success": "Succesfully logged out."}), 420


@app.route("/purchase_overview", methods=["GET", "POST"])
def purchase_overview():
    if request.method == "POST":
        artist_name = request.form.get("artist_name", "").strip() or None
        start_date = request.form.get("start_date", "").strip() or None
        end_date = request.form.get("end_date", "").strip() or None
        genre = request.form.get("genre", "").strip() or None

        try:
            summary_data, details_data = database_handler.get_purchase_overview(
                artist_name, start_date, end_date, genre
            )
            return render_template("views/purchase_overview.html", sales_data=summary_data, vinyl_sales=details_data)
        except Exception as e:
            app.logger.error(f"Error retrieving purchase overview: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        return render_template("views/purchase_overview.html", sales_data=None, vinyl_sales=None)


@app.route("/insert_vinyl", methods=["GET"])
def insert_vinyl_page():
    return render_template("views/insert_vinyl.html")
