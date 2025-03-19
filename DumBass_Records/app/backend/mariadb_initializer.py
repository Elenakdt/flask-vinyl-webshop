import pymysql
import app.app
import sys
import mariadb
from pymongo import MongoClient
from .data.api_extractor import get_data_from_api
import os
import json
from flask import current_app
import random
from faker import Faker


def create_tables(mariadb_connection):
    try:
        cursor = mariadb_connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Artists (
                Artist_ID INT PRIMARY KEY AUTO_INCREMENT,
                Artist_Name VARCHAR(255) NOT NULL,
                Nationality VARCHAR(255) NOT NULL
            );
            """
        )
        current_app.logger.debug("Table 'Artists' created successfully.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Vinyls (
                Vinyl_ID INT PRIMARY KEY AUTO_INCREMENT,
                Artist_ID INT NOT NULL,
                Vinyl_Name VARCHAR (255) NOT NULL,
                Price DECIMAL(10, 2) DEFAULT 0.00,
                Release_Date DATE NOT NULL,
                Cover_Image VARCHAR(255),
                Genre VARCHAR(255) NOT NULL,
                FOREIGN KEY (Artist_ID) REFERENCES Artists(Artist_ID)
            );
            """
        )
        current_app.logger.debug("Table 'Vinyl' created successfully.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                User_ID INT PRIMARY KEY AUTO_INCREMENT,
                User_Name VARCHAR(255) NOT NULL,
                User_Email VARCHAR(255) NOT NULL,
                User_Password VARCHAR(255) NOT NULL
            );
            """
        )

        current_app.logger.debug("Table 'User' created successfully.")

        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS Admins (
                    User_ID INT PRIMARY KEY,
                    Department ENUM ('IT', 'HR', 'Finance'),
                    FOREIGN KEY (User_ID) REFERENCES Users(User_ID)
                );
                """
        )

        current_app.logger.debug("Table 'Admins' created successfully.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Customers (
                User_ID INT PRIMARY KEY,
                Address VARCHAR (255),
                FOREIGN KEY (User_ID) REFERENCES Users(User_ID)
            );
            """
        )

        current_app.logger.debug("Table 'Customers' created successfully.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Orders (
                Order_ID INT PRIMARY KEY AUTO_INCREMENT,
                User_ID INT NOT NULL,
                Order_Date DATE NOT NULL,
                Zahlungsmethode ENUM ('ApplePay', 'Klarna', 'Kreditkarte') NOT NULL,
                Total_Price DECIMAL(10,2) DEFAULT 0.00,
                FOREIGN KEY (User_ID) REFERENCES Customers(User_ID)
            );
            """
        )

        current_app.logger.debug("Table 'Orders' created successfully.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Order_Vinyl (
                Order_ID INT,
                Vinyl_ID INT,
                PRIMARY KEY (Order_ID, Vinyl_ID),
                Amount INT NOT NULL,
                FOREIGN KEY (Order_ID) REFERENCES Orders(Order_ID),
                FOREIGN KEY (Vinyl_ID) REFERENCES Vinyls(Vinyl_ID)
            );
            """
        )

        current_app.logger.debug("Table 'Order_Vinyl' created successfully.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Reviews (
                Vinyl_ID INT NOT NULL,
                User_ID INT NOT NULL,
                Comment TEXT,
                Rating INT CHECK (0 <= Rating AND Rating <= 5),
                Review_Date DATE NOT NULL,
                PRIMARY KEY (Vinyl_ID, User_ID),
                FOREIGN KEY (User_ID) REFERENCES Customers(User_ID),
                FOREIGN KEY (Vinyl_ID) REFERENCES Vinyls(Vinyl_ID) ON DELETE CASCADE
            );
            """
        )

        current_app.logger.debug("Table 'Reviews' created successfully.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Referrals (
                User_ID INT NOT NULL,
                R_User_ID INT NOT NULL,
                Referral_Count INT DEFAULT 0,
                PRIMARY KEY (User_ID, R_User_ID),
                FOREIGN KEY (User_ID) REFERENCES Customers(User_ID),
                FOREIGN KEY (R_User_ID) REFERENCES Customers(User_ID)
            );
            """
        )

        current_app.logger.debug("Table 'Referrals' created successfully.")

        cursor.execute(
            """
            CREATE TRIGGER Rabatt_Nach_Empfehlung
            BEFORE INSERT ON Orders
            FOR EACH ROW
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM Referrals
                    WHERE User_ID = NEW.User_ID
                      AND Referral_Count > 0
                ) THEN
                    SET NEW.Total_Price = NEW.Total_Price * 0.931;
                    UPDATE Referrals
                    SET Referral_Count = Referral_Count - 1
                    WHERE User_ID = NEW.User_ID
                      AND Referral_Count > 0
                    LIMIT 1;
                END IF;
            END;
            """
        )
        current_app.logger.debug("Trigger 'Rabatt_Nach_Empfehlung' created successfully.")

        cursor.execute(
            """
            CREATE TRIGGER after_order_vinyl_insert
            AFTER INSERT ON Order_Vinyl
            FOR EACH ROW
            BEGIN
                UPDATE Orders
                SET Total_Price = (
                    SELECT IFNULL(SUM(v.Price * ov.Amount), 0)
                    FROM Order_Vinyl ov
                    JOIN Vinyls v ON ov.Vinyl_ID = v.Vinyl_ID
                    WHERE ov.Order_ID = NEW.Order_ID
                )
                WHERE Orders.Order_ID = NEW.Order_ID;
            END;
            """
        )
        current_app.logger.debug("Trigger 'after_order_vinyl_insert' created successfully.")

        cursor.execute(
            """
            CREATE TRIGGER after_order_vinyl_update
            AFTER UPDATE ON Order_Vinyl
            FOR EACH ROW
            BEGIN
                UPDATE Orders
                SET Total_Price = (
                    SELECT IFNULL(SUM(v.Price * ov.Amount), 0)
                    FROM Order_Vinyl ov
                    JOIN Vinyls v ON ov.Vinyl_ID = v.Vinyl_ID
                    WHERE ov.Order_ID = NEW.Order_ID
                )
                WHERE Orders.Order_ID = NEW.Order_ID;
            END;
            """
        )
        current_app.logger.debug("Trigger 'after_order_vinyl_update' created successfully.")

        cursor.execute(
            """
            CREATE TRIGGER after_order_vinyl_delete
            AFTER DELETE ON Order_Vinyl
            FOR EACH ROW
            BEGIN
                UPDATE Orders
                SET Total_Price = (
                    SELECT IFNULL(SUM(v.Price * ov.Amount), 0)
                    FROM Order_Vinyl ov
                    JOIN Vinyls v ON ov.Vinyl_ID = v.Vinyl_ID
                    WHERE ov.Order_ID = OLD.Order_ID
                )
                WHERE Orders.Order_ID = OLD.Order_ID;
            END;
            """
        )
        current_app.logger.debug("Trigger 'after_order_vinyl_delete' created successfully.")

        mariadb_connection.commit()

    except Exception as e:
        current_app.logger.debug(f"Error creating tables: {e}")


def delete_database(mariadb_connection):
    try:
        cursor = mariadb_connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]

        if not database_name:
            print("No database selected!")
            return
        cursor.execute(f"DROP DATABASE IF EXISTS `{database_name}`")
        current_app.logger.debug(f"Database '{database_name}' dropped successfully.")
        cursor.execute(f"CREATE DATABASE `{database_name}`")
        cursor.execute(f"USE `{database_name}`")
        current_app.logger.debug(f"Database '{database_name}' recreated successfully.")

    except Exception as e:
        current_app.logger.Error(f"Error resetting the database: {e}")


def fill_artists(mariadb_connection):
    try:
        file_path = os.path.join(os.path.dirname(__file__), "data/artists.json")

        with open(file_path, "r") as file:
            data = json.load(file)

        cursor = mariadb_connection.cursor()
        for artist in data.get("artists", []):
            name = artist.get("artist")
            nationality = artist.get("nationality")

            if name and nationality:
                cursor.execute(
                    """
                    INSERT INTO Artists (artist_name, Nationality)
                    VALUES (%s, %s)
                """,
                    (name, nationality),
                )

        mariadb_connection.commit()
        current_app.logger.debug("Artists inserted successfully.")

    except Exception as e:
        current_app.logger.info(f"Error inserting artists: {e}")


def fill_vinyls(mariadb_connection):
    try:
        file_path = os.path.join(os.path.dirname(__file__), "data/releases.json")
        with open(file_path, "r") as file:
            releases = json.load(file)

        cursor = mariadb_connection.cursor()
        for release in releases.get("releases", []):
            artist_name = release.get("artist")
            title = release.get("title")[:255]
            year = release.get("year")
            genre = ", ".join(release.get("genre", []))
            cover_image = release.get("cover_image")

            release_date = f"{year}-01-01" if year != "Unknown" else "1999-09-09"

            cursor.execute(
                """
                SELECT artist_id FROM Artists WHERE artist_name = %s
                """,
                (artist_name,),
            )
            result = cursor.fetchone()
            if result:
                artist_id = result[0]
                price = random.choice([19.99, 29.99, 39.99, 49.99])
                cursor.execute(
                    """
                    INSERT INTO Vinyls (artist_id, vinyl_name, price,release_date, cover_image, genre)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (artist_id, title, price, release_date, cover_image, genre),
                )

        mariadb_connection.commit()
        current_app.logger.debug("Vinyls inserted successfully.")

    except Exception as e:
        current_app.logger.info(f"Error inserting vinyls: {e}")


def fill_users(mariadb_connection):
    faker = Faker()
    cursor = mariadb_connection.cursor()
    try:
        for i in range(100):
            user_name = faker.name()
            user_email = faker.email()
            user_password = faker.password()

            cursor.execute(
                """
                INSERT INTO Users (User_Name, User_Email, User_Password)
                VALUES (%s, %s, %s)
                """,
                (user_name, user_email, user_password),
            )
            user_id = cursor.lastrowid

            if i < 3:
                department = random.choice(["IT", "HR", "Finance"])
                cursor.execute(
                    """
                    INSERT INTO Admins (User_ID, Department)
                    VALUES (%s, %s)
                    """,
                    (user_id, department),
                )
            else:
                address = faker.address()
                cursor.execute(
                    """
                    INSERT INTO Customers (User_ID, Address)
                    VALUES (%s, %s)
                    """,
                    (user_id, address),
                )

        cursor.execute(
            """
            INSERT INTO Users (User_Name, User_Email, User_Password)
            VALUES (%s, %s, %s)
            """,
            ("admin", "admin@admin.com", "password"),
        )
        admin_user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Admins (User_ID, Department)
            VALUES (%s, %s)
            """,
            (admin_user_id, "IT"),
        )

        cursor.execute(
            """
            INSERT INTO Users (User_Name, User_Email, User_Password)
            VALUES (%s, %s, %s)
            """,
            ("User Userowski", "user@user.com", "password"),
        )
        user_userowki_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO Customers (User_ID, Address)
            VALUES (%s, %s)
            """,
            (user_userowki_id, "User Street 12"),
        )

        mariadb_connection.commit()
        current_app.logger.debug("Users inserted successfully.")

    except Exception as e:
        current_app.logger.info(f"Error inserting users: {e}")
    finally:
        cursor.close()


def insert_TestUser_data(mariadb_connection):
    try:
        cursor = mariadb_connection.cursor()
        cursor.execute(
            """
                SELECT User_ID
                FROM Users
                WHERE User_Name = %s
                AND User_Email = %s
                Limit 1
                """,
            ("User Userowski", "user@user.com"),
        )
        result = cursor.fetchone()
        if not result:
            current_app.logger.info("User 'User Userowski' wurde nicht gefunden")
            return
        user_id = result[0]

        cursor.execute(
            """
            SELECT Vinyl_ID
            FROM Vinyls
            LIMIT 4
            """
        )
        vinyl_row = cursor.fetchall()
        vinyl_ids = [row[0] for row in vinyl_row]

        cursor.execute(
            """
            INSERT INTO Orders (User_ID, Order_Date, Zahlungsmethode, Total_Price)
            VALUES (%s, CURDATE(), %s, 0.00)
            """,
            (user_id, "ApplePay"),
        )
        order_id_1 = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Order_Vinyl (Order_ID, Vinyl_ID, Amount)
            VALUES (%s, %s, %s)
            """,
            (order_id_1, vinyl_ids[0], 1),
        )
        cursor.execute(
            """
            INSERT INTO Order_Vinyl (Order_ID, Vinyl_ID, Amount)
            VALUES (%s, %s, %s)
            """,
            (order_id_1, vinyl_ids[1], 3),
        )

        cursor.execute(
            """
            INSERT INTO Orders (User_ID, Order_Date, Zahlungsmethode, Total_Price)
            VALUES (%s, CURDATE(), %s, 0.00)
            """,
            (user_id, "Klarna"),
        )
        order_id_2 = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Order_Vinyl (Order_ID, Vinyl_ID, Amount)
            VALUES (%s, %s, %s)
            """,
            (order_id_2, vinyl_ids[2], 1),
        )
        cursor.execute(
            """
            INSERT INTO Order_Vinyl (Order_ID, Vinyl_ID, Amount)
            VALUES (%s, %s, %s)
            """,
            (order_id_2, vinyl_ids[3], 1),
        )

        cursor.execute(
            """
            INSERT INTO Reviews (Vinyl_ID, User_ID, Comment, Rating, Review_Date)
            VALUES (%s, %s, %s, %s, CURDATE())
            """,
            (
                vinyl_ids[0],
                user_id,
                "Tolles Vinyl, super Klang!",
                1,
            ),
        )
        cursor.execute(
            """
            INSERT INTO Reviews (Vinyl_ID, User_ID, Comment, Rating, Review_Date)
            VALUES (%s, %s, %s, %s, CURDATE())
            """,
            (vinyl_ids[1], user_id, "Spiel ich heute Abend Meiner Mama", 5),
        )

        mariadb_connection.commit()
        current_app.logger.debug("For 'User Userowski' 2 Orders and 2 Reviews added successfully.")

    except Exception as e:
        current_app.logger.info(f"Fehler beim Einfügen der Debug-Daten: {e}")


def insert_random_reviews(mariadb_connection):
    try:
        faker = Faker()
        cursor = mariadb_connection.cursor()
        cursor.execute(
            """
            SELECT Vinyl_ID 
            FROM Vinyls
            ORDER BY Vinyl_ID ASC
            LIMIT 20;
        """
        )
        vinyl_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT User_ID 
            FROM Customers;
        """
        )
        customer_ids = [row[0] for row in cursor.fetchall()]

        if not vinyl_ids or not customer_ids:
            current_app.logger.debug("No vinyls or customers found for review insertion.")
            return

        for _ in range(100):
            vinyl_id = random.choice(vinyl_ids)
            user_id = random.choice(customer_ids)
            rating = random.randint(1, 5)
            comment = faker.sentence(nb_words=10)
            review_date = faker.date_between(start_date="-5y", end_date="today")

            cursor.execute(
                """
                INSERT INTO Reviews (Vinyl_ID, User_ID, Comment, Rating, Review_Date)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    Comment = VALUES(Comment),
                    Rating = VALUES(Rating),
                    Review_Date = VALUES(Review_Date);
                """,
                (vinyl_id, user_id, comment, rating, review_date),
            )

        mariadb_connection.commit()
        current_app.logger.debug("100 randomized reviews with varying dates inserted successfully.")

    except Exception as e:
        current_app.logger.error(f"Error inserting randomized reviews: {e}")

    finally:
        cursor.close()


def erase_and_fill_maria_db(mariadb_connection):
    delete_database(mariadb_connection)
    create_tables(mariadb_connection)
    fill_artists(mariadb_connection)
    fill_vinyls(mariadb_connection)
    fill_users(mariadb_connection)
    insert_TestUser_data(mariadb_connection)
    insert_random_reviews(mariadb_connection)
