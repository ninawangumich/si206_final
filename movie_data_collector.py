import os
import sqlite3
import requests
from tmdbv3api import TMDb, Movie, Discover
from datetime import datetime
import time
import json


TMDB_API_KEY = "f42508b09981d14214b0ab42e41df36f"
OMDB_API_KEY = "76eadd13"
OMDB_BASE_URL = "http://www.omdbapi.com/"


tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
movie = Movie()
discover = Discover()

def init_db():
    """Initialize database with completely separate tables for each API"""
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    
    
    c.execute('''CREATE TABLE IF NOT EXISTS tmdb_movies
                 (tmdb_id INTEGER PRIMARY KEY,
                  title TEXT NOT NULL,
                  release_date TEXT,
                  revenue REAL,
                  budget REAL,
                  tmdb_rating REAL,
                  tmdb_votes INTEGER,
                  tmdb_popularity REAL,
                  region TEXT,
                  UNIQUE(tmdb_id))''')
    
    
    c.execute('''CREATE TABLE IF NOT EXISTS omdb_movies
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  imdb_id TEXT UNIQUE,
                  title TEXT,
                  year TEXT,
                  rotten_tomatoes_rating TEXT,
                  metacritic_rating TEXT,
                  awards TEXT,
                  box_office TEXT,
                  director TEXT,
                  UNIQUE(imdb_id))''')
    
    conn.commit()
    conn.close()

def fetch_tmdb_data(limit=25):
    """Fetch TMDB movies focusing on financial data"""
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    count = 0
    
    
    movies = discover.discover_movies({
        'with_genres': '28',  
        'sort_by': 'popularity.desc'
    })
    
    for movie_data in movies:
        if count >= limit:
            break
            
        try:
            
            details = movie.details(movie_data.id)
            
            c.execute('''
            INSERT OR IGNORE INTO tmdb_movies 
            (tmdb_id, title, release_date, revenue, budget, 
             tmdb_rating, tmdb_votes, tmdb_popularity, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                details.id,
                details.title,
                details.release_date,
                getattr(details, 'revenue', 0),
                getattr(details, 'budget', 0),
                getattr(details, 'vote_average', 0),
                getattr(details, 'vote_count', 0),
                getattr(details, 'popularity', 0),
                'US'
            ))
            
            if c.rowcount > 0:
                count += 1
                print(f"Added TMDB movie: {details.title} ({count}/{limit})")
                
        except Exception as e:
            print(f"Error adding TMDB movie: {str(e)}")
            continue
            
        time.sleep(0.5)  
    
    conn.commit()
    
    
    c.execute("SELECT COUNT(*) FROM tmdb_movies")
    total = c.fetchone()[0]
    print(f"\nTotal TMDB movies in database: {total}")
    
    conn.close()
    return count

def fetch_omdb_data(limit=25):
    """Fetch OMDB movies focusing on ratings and awards"""
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    count = 0
    
    
    current_year = datetime.now().year
    for year in range(current_year, current_year-10, -1):
        if count >= limit:
            break
            
        params = {
            'apikey': OMDB_API_KEY,
            'type': 'movie',
            'y': str(year),
            's': 'action'
        }
        
        try:
            response = requests.get(OMDB_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('Search'):
                for movie in data['Search']:
                    if count >= limit:
                        break
                    
                    
                    detail_params = {
                        'apikey': OMDB_API_KEY,
                        'i': movie['imdbID']
                    }
                    
                    detail_response = requests.get(OMDB_BASE_URL, detail_params)
                    detail_response.raise_for_status()
                    movie_data = detail_response.json()
                    
                    
                    rt_rating = 'N/A'
                    metacritic = 'N/A'
                    for rating in movie_data.get('Ratings', []):
                        if rating['Source'] == 'Rotten Tomatoes':
                            rt_rating = rating['Value']
                        elif rating['Source'] == 'Metacritic':
                            metacritic = rating['Value']
                    
                    try:
                        c.execute('''
                        INSERT OR IGNORE INTO omdb_movies 
                        (imdb_id, title, year, rotten_tomatoes_rating, 
                         metacritic_rating, awards, box_office, director)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            movie_data['imdbID'],
                            movie_data['Title'],
                            movie_data['Year'],
                            rt_rating,
                            metacritic,
                            movie_data.get('Awards', 'N/A'),
                            movie_data.get('BoxOffice', 'N/A'),
                            movie_data.get('Director', 'N/A')
                        ))
                        
                        if c.rowcount > 0:
                            count += 1
                            print(f"Added OMDB movie: {movie_data['Title']} ({count}/{limit})")
                    
                    except Exception as e:
                        print(f"Error adding OMDB movie: {str(e)}")
                    
                    time.sleep(1)  
                    
        except Exception as e:
            print(f"Error fetching OMDB data: {str(e)}")
            continue
    
    conn.commit()
    
    
    c.execute("SELECT COUNT(*) FROM omdb_movies")
    total = c.fetchone()[0]
    print(f"\nTotal OMDB movies in database: {total}")
    
    conn.close()
    return count

def main():
    print("Initializing database...")
    init_db()
    
    print("\nCollecting TMDB financial data...")
    fetch_tmdb_data()
    
    print("\nCollecting OMDB ratings and awards data...")
    fetch_omdb_data()

if __name__ == "__main__":
    main() 