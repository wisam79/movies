import os
import requests

TMDB_API_KEY = os.getenv("TMDB_KEY")
BASE_URL = "https://api.themoviedb.org/3"

def get_movies_by_genre(genre_id):
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "with_genres": genre_id,
        "language": "ar",
        "sort_by": "popularity.desc"
    }
    response = requests.get(url, params=params)
    return response.json().get("results", [])

def search_movie(query):
    url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "ar"
    }
    response = requests.get(url, params=params)
    return response.json().get("results", [])

def get_movie_details(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ar"
    }
    response = requests.get(url, params=params)
    return response.json()
