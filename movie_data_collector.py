import os
import sqlite3
import requests
from tmdbv3api import TMDb, Movie, Discover
from datetime import datetime
import time
import json

# API Configuration
TMDB_API_KEY = "f42508b09981d14214b0ab42e41df36f"
OMDB_API_KEY = "76eadd13"
OMDB_BASE_URL = "http://www.omdbapi.com/"

# Initialize TMDB
tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
movie = Movie()
discover = Discover()

def init_db():
    """Initialize the database with updated schema"""
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    
    # Create movies table for TMDB data
    c.execute('''CREATE TABLE IF NOT EXISTS movies
                 (id INTEGER PRIMARY KEY,
                  title TEXT NOT NULL,
                  release_date TEXT,
                  revenue REAL,
                  region TEXT,
                  UNIQUE(id))''')
    
    # Drop existing movie_ratings table to update schema
    c.execute('DROP TABLE IF EXISTS movie_ratings')
    
    # Create ratings table with combined data
    c.execute('''CREATE TABLE IF NOT EXISTS movie_ratings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  movie_id INTEGER,
                  tmdb_rating REAL,
                  tmdb_votes INTEGER,
                  tmdb_popularity REAL,
                  rotten_tomatoes_rating TEXT,
                  box_office TEXT,
                  awards TEXT,
                  revenue REAL,
                  budget REAL,
                  FOREIGN KEY (movie_id) REFERENCES movies(id),
                  UNIQUE(movie_id))''')
    
    conn.commit()
    conn.close()

def get_omdb_data(title, year=None):
    """Get movie data from OMDB API"""
    params = {
        'apikey': OMDB_API_KEY,
        't': title,
        'type': 'movie'
    }
    if year:
        params['y'] = year
    
    try:
        response = requests.get(OMDB_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'True':
            return {
                'rotten_tomatoes_rating': next((rating['Value'] for rating in data.get('Ratings', []) 
                                              if rating['Source'] == 'Rotten Tomatoes'), 'N/A'),
                'box_office': data.get('BoxOffice', 'N/A'),
                'awards': data.get('Awards', 'N/A')
            }
        else:
            print(f"No OMDB data found for: {title}")
            return None
            
    except Exception as e:
        print(f"Error fetching OMDB data for {title}: {str(e)}")
        return None

def get_tmdb_movies(page=1):
    """Get action movies from TMDB"""
    movies = discover.discover_movies({
        'with_genres': 28,  # Action genre ID
        'sort_by': 'popularity.desc',
        'page': page,
        'region': 'US'  # Limit to US region
    })
    return movies

def save_movie_data(movies, conn, limit=25):
    """Save movie data from both APIs"""
    c = conn.cursor()
    count = 0
    ratings_count = 0
    
    for movie_data in movies:
        if count >= limit:
            break
            
        try:
            # Get detailed movie info from TMDB
            details = movie.details(movie_data.id)
            
            # Get TMDB movie data
            tmdb_title = movie_data.title
            tmdb_release_date = movie_data.release_date
            tmdb_revenue = getattr(details, 'revenue', 0)
            
            # Extract year for OMDB search
            year = tmdb_release_date[:4] if tmdb_release_date else None
            
            c.execute('''INSERT OR IGNORE INTO movies (id, title, release_date, revenue, region)
                        VALUES (?, ?, ?, ?, ?)''',
                     (movie_data.id, tmdb_title, tmdb_release_date,
                      tmdb_revenue, 'US'))
            
            if c.rowcount > 0:
                count += 1
                print(f"Saved TMDB movie: {tmdb_title}")
                
                # Get OMDB data using TMDB title
                omdb_data = get_omdb_data(tmdb_title, year)
                
                # Save combined data
                c.execute('''INSERT OR IGNORE INTO movie_ratings 
                           (movie_id, tmdb_rating, tmdb_votes, tmdb_popularity,
                            rotten_tomatoes_rating, box_office, awards,
                            revenue, budget)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (movie_data.id, 
                         getattr(details, 'vote_average', 0),
                         getattr(details, 'vote_count', 0),
                         getattr(details, 'popularity', 0),
                         omdb_data['rotten_tomatoes_rating'] if omdb_data else 'N/A',
                         omdb_data['box_office'] if omdb_data else 'N/A',
                         omdb_data['awards'] if omdb_data else 'N/A',
                         tmdb_revenue,
                         getattr(details, 'budget', 0)))
                
                if c.rowcount > 0:
                    ratings_count += 1
                    print(f"Saved ratings and data for TMDB movie: {tmdb_title}")
                
                time.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            print(f"Error saving TMDB movie {movie_data.title}: {str(e)}")
            continue
    
    conn.commit()
    return count, ratings_count

def main():
    print("Initializing database...")
    init_db()
    conn = sqlite3.connect('movies.db')
    
    # Get current count of movies
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM movies")
    current_count = c.fetchone()[0]
    print(f"Current TMDB movie count: {current_count}")
    
    # Since we dropped the ratings table, we need to collect data for all movies
    print("\nCollecting data for all existing TMDB movies...")
    c.execute("SELECT id, title, release_date FROM movies")
    all_movies = c.fetchall()
    
    total_processed = 0
    for movie_id, tmdb_title, release_date in all_movies:
        try:
            details = movie.details(movie_id)
            year = release_date[:4] if release_date else None
            omdb_data = get_omdb_data(tmdb_title, year)
            
            c.execute('''INSERT OR REPLACE INTO movie_ratings 
                       (movie_id, tmdb_rating, tmdb_votes, tmdb_popularity,
                        rotten_tomatoes_rating, box_office, awards,
                        revenue, budget)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (movie_id, 
                     getattr(details, 'vote_average', 0),
                     getattr(details, 'vote_count', 0),
                     getattr(details, 'popularity', 0),
                     omdb_data['rotten_tomatoes_rating'] if omdb_data else 'N/A',
                     omdb_data['box_office'] if omdb_data else 'N/A',
                     omdb_data['awards'] if omdb_data else 'N/A',
                     getattr(details, 'revenue', 0),
                     getattr(details, 'budget', 0)))
            
            total_processed += 1
            print(f"Updated data for TMDB movie: {tmdb_title} ({total_processed}/{current_count})")
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"Error updating TMDB movie {tmdb_title}: {str(e)}")
    
    conn.commit()
    
    # Print summary
    c.execute("SELECT COUNT(*) FROM movies")
    movie_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM movie_ratings")
    ratings_count = c.fetchone()[0]
    
    print(f"\nFinal Summary:")
    print(f"Total TMDB movies collected: {movie_count}")
    print(f"Total ratings collected: {ratings_count}")
    
    # Print sample data
    print("\nSample of TMDB movies with combined stats:")
    c.execute('''
        SELECT 
            m.title, 
            r.tmdb_rating,
            r.rotten_tomatoes_rating,
            r.box_office,
            r.awards,
            r.revenue,
            r.budget
        FROM movies m 
        JOIN movie_ratings r ON m.id = r.movie_id 
        ORDER BY r.tmdb_popularity DESC 
        LIMIT 5
    ''')
    for row in c.fetchall():
        print(f"\nTMDB Movie: {row[0]}")
        print(f"  TMDB Rating: {row[1]}")
        print(f"  Rotten Tomatoes: {row[2]}")
        print(f"  Box Office: {row[3]}")
        print(f"  Awards: {row[4]}")
        revenue = "${:,.2f}".format(row[5]) if row[5] > 0 else "N/A"
        budget = "${:,.2f}".format(row[6]) if row[6] > 0 else "N/A"
        print(f"  Revenue: {revenue}")
        print(f"  Budget: {budget}")
    
    conn.close()

if __name__ == "__main__":
    main() 