import discogs_client
from dotenv import load_dotenv
import os
import requests
import json
import urllib.parse

load_dotenv()

API_SECRET_KEY = os.getenv("API_SECRET_KEY")
API_PUBLIC_KEY = os.getenv("API_PUBLIC_KEY")
APP_NAME = os.getenv("APP_NAME")

BASE_URL = "https://api.discogs.com"

GENRES = [
    "Blues",
    "Children's",
    "Classical",
    "Electronic",
    "Folk, World, & Country",
    "Funk / Soul",
    "Hip Hop",
    "Jazz",
    "Pop",
    "Rock",
    "Stage & Screen",
]


def init_client():
    d = discogs_client.Client(APP_NAME, consumer_key=API_PUBLIC_KEY, consumer_secret=API_SECRET_KEY)
    print("Please authorize the application by visiting the following URL:")
    print(d.get_authorize_url())

    verifier = input("Enter the verifier code: ")
    d.get_access_token(verifier)
    print("Authenticated as:", d.identity())
    return d


def extract_vinyls_interactive():
    d = discogs_client.Client(APP_NAME, consumer_key=API_PUBLIC_KEY, consumer_secret=API_SECRET_KEY)
    print("Please authorize the application by visiting the following URL:")
    print(d.get_authorize_url())

    verifier = input("Enter the verifier code: ")
    d.get_access_token(verifier)
    print("Authenticated as:", d.identity())

    while True:
        query = input("\nEnter your search query (or type 'exit' to quit): ")
        if query.lower() == "exit":
            print("Exiting the program.")
            break

        results = d.search(query, type="release")
        releases = results.page(1)
        print(dir(releases[0]))
        if releases:
            print(f"\nSearch Results for '{query}':")
            for idx, release in enumerate(releases, start=1):
                artists = ", ".join(artist.name for artist in release.artists)
                print(f"{idx}. {release.title} by {artists}, Genre: {release.genres}, ")
                if not GENRES.__contains__(release.genres):
                    GENRES.append(release.genres)
                    release.g
        else:
            print(f"No results found for '{query}'.")

        print(GENRES)


def extract_releases():
    client = init_client()
    all_results = []  # List to store all simplified releases
    unique_artists = {}  # Dictionary to store unique artists and their nationality

    max_page = 5  # Number of pages to iterate through for each genre

    for genre in GENRES:
        encoded_genre = urllib.parse.quote(genre)

        for page in range(1, max_page + 1):
            # Fix the URL by adding '=' after 'page'
            url = f"{BASE_URL}/database/search?genre={encoded_genre}&type=release&page={page}&per_page=100"
            try:
                response = client._get(url)
                data = response
            except Exception as e:
                print(f"Error fetching data for genre '{genre}' on page {page}: {e}")
                continue

            releases = data.get("results", [])
            print(f"Processing {len(releases)} releases for genre '{genre}' on page {page}.")

            for release in releases:
                full_title = release.get("title", "Untitled")

                if " - " in full_title:
                    artist, title = full_title.split(" - ", 1)
                    artist = artist.strip()
                    title = title.strip()
                else:
                    print(f"Skipping title '{full_title}'")
                    title = full_title
                    artist = "Unknown Artist"

                if artist not in unique_artists:
                    nationality = release.get("country", "Unknown")
                    unique_artists[artist] = nationality
                    print(f"Adding Artist: {artist}")
                else:
                    print(f"Skipping already known artist: {artist}")

                simplified_release = {
                    "artist": artist,
                    "country": release.get("country", "Unknown"),
                    "year": release.get("year", "Unknown"),
                    "genre": release.get("genre", []),
                    "cover_image": release.get("cover_image", ""),
                    "title": title,
                }
                all_results.append(simplified_release)

    # Save simplified releases to JSON
    with open("releases.json", "w", encoding="utf-8") as f:
        json.dump({"releases": all_results}, f, indent=4)

    unique_artists_list = [{"artist": artist, "nationality": nat} for artist, nat in unique_artists.items()]
    with open("artists.json", "w", encoding="utf-8") as f:
        json.dump({"artists": unique_artists_list}, f, indent=4)

    print(f"Unique artists extracted: {len(unique_artists_list)}. Saved to 'artists.json'.")
    print(f"\nExtraction complete. {len(all_results)} releases saved to 'releases.json'.")


if __name__ == "__main__":
    extract_releases()
