# flask-vinyl-webshop
# DumBass Records

![Project Logo]

![image](https://github.com/user-attachments/assets/be64c6e9-4373-49e5-b29a-8fd96061f1cd)


DumbAss Records is a Flask-based web application built as a university project. It simulates a vinyl record store with both user and admin interfaces. The application utilizes a dual-database architecture by allowing users to switch between SQL (MariaDB) and NoSQL (MongoDB) backends, all within a containerized environment using Docker. Additionally, a custom API scraper was used to download vinyls from discogs.com. The data used in no-sql and sql is partially scraped and partially randomly generated.

## Table of Contents
- [Features](#features)
- [Installation and Setup](#installation-and-setup)
- [Usage](#usage)
- [Custom API Scraper](#custom-api-scraper)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Features
- *Dual Database Support:*  
  The web app supports both SQL (MariaDB) and NoSQL (MongoDB) databases. A built-in switch lets users toggle between the two modes.
- *User and Admin Access:*  
  Regular users can browse and purchase vinyl records, while administrators have access to detailed statistics and management features.
- *Vinyl Storefront:*  
  An intuitive shopping experience for vinyl records including browsing, adding to cart, and purchasing.
- *Custom API Scraper:*  
  A dedicated API scraper automatically fetches vinyl record data from Discogs, ensuring the catalog remains current.
- *Containerized Deployment:*  
  The entire application—including the Flask app, MariaDB, and MongoDB—is containerized using Docker, streamlining deployment and environment consistency.

## Installation and Setup
1. *Clone the repository:*
   bash
   git clone https://github.com/Elenakdt/flask-vinyl-webshop
   cd DumBass_Records
   
2. *Ensure Docker is installed on your machine.*
3. *Build and run the containers:*
   - The Python packages and application dependencies are managed via Dockerfiles.
     bash
     docker-compose up --build
     
4. *Access the application:*
   - Once all containers are up and running, open your browser and navigate to http://localhost:8000

## Usage
- *Switching Databases:*
  - Use the database switch on the website to migrate MariaDB (SQL) to MongoDB (NoSQL).  
    ![image](https://github.com/user-attachments/assets/4ef1c9fe-e0ad-4975-8f20-c66a4a19141b)

- *Purchasing Vinyls:*
  - Browse the vinyl collection, add records to your shopping cart, and complete your purchase using the integrated checkout process.
  ![image](https://github.com/user-attachments/assets/ed27a91d-cab6-466e-8ce7-a8a4ad98103c)
 
  ![image](https://github.com/user-attachments/assets/be031745-074a-4c9e-8513-bde7202c3592)

- *Admin Panel:*
  - Admin users can log in to access a dedicated admin panel for viewing sales statistics and managing inventory.
 ![image](https://github.com/user-attachments/assets/dee06673-0540-4c79-94e9-785c88ae578a)
![image](https://github.com/user-attachments/assets/0bb1dc6e-bbcf-4932-b372-d9057b1aea02)
![image](https://github.com/user-attachments/assets/a6b3c8d9-0397-4f86-95d6-b0c9722e21fb)

## Custom API Scraper
The vinyls used in this project are from discogs.com. Special thanks to them for the awesome API.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
