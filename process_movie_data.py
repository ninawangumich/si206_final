import sqlite3
import pandas as pd
from datetime import datetime

def calculate_movie_stats():
    """Calculate various statistics from the movie data"""
    conn = sqlite3.connect('movies.db')
    
    # Calculate average ratings and revenue stats using JOIN
    query = '''
    SELECT 
        strftime('%Y', m.release_date) as release_year,
        COUNT(*) as movie_count,
        AVG(r.tmdb_rating) as avg_rating,
        AVG(r.revenue) as avg_revenue,
        AVG(r.budget) as avg_budget,
        SUM(CASE WHEN r.revenue > r.budget THEN 1 ELSE 0 END) as profitable_movies
    FROM movies m
    JOIN movie_ratings r ON m.id = r.movie_id
    WHERE m.release_date IS NOT NULL
    GROUP BY release_year
    ORDER BY release_year DESC
    '''
    
    yearly_stats = pd.read_sql_query(query, conn)
    
    # Calculate Rotten Tomatoes stats
    rt_query = '''
    SELECT 
        CASE 
            WHEN CAST(REPLACE(REPLACE(r.rotten_tomatoes_rating, '%', ''), 'N/A', '0') AS INTEGER) >= 75 THEN 'Fresh (75-100)'
            WHEN CAST(REPLACE(REPLACE(r.rotten_tomatoes_rating, '%', ''), 'N/A', '0') AS INTEGER) >= 60 THEN 'Fresh (60-74)'
            ELSE 'Rotten (<60)'
        END as rating_category,
        COUNT(*) as movie_count,
        AVG(r.revenue) as avg_revenue
    FROM movies m
    JOIN movie_ratings r ON m.id = r.movie_id
    WHERE r.rotten_tomatoes_rating != 'N/A'
    GROUP BY rating_category
    '''
    
    rt_stats = pd.read_sql_query(rt_query, conn)
    
    # Calculate box office performance by rating
    performance_query = '''
    SELECT 
        CASE 
            WHEN r.tmdb_rating >= 8 THEN 'Excellent (8-10)'
            WHEN r.tmdb_rating >= 7 THEN 'Good (7-7.9)'
            WHEN r.tmdb_rating >= 6 THEN 'Average (6-6.9)'
            ELSE 'Below Average (<6)'
        END as rating_category,
        COUNT(*) as movie_count,
        AVG(r.revenue) as avg_revenue,
        AVG(r.budget) as avg_budget,
        AVG(CASE WHEN r.revenue > 0 AND r.budget > 0 
            THEN CAST(r.revenue AS FLOAT) / CAST(r.budget AS FLOAT) 
            ELSE NULL END) as avg_roi
    FROM movies m
    JOIN movie_ratings r ON m.id = r.movie_id
    GROUP BY rating_category
    ORDER BY rating_category
    '''
    
    performance_stats = pd.read_sql_query(performance_query, conn)
    
    # Get US market analysis
    us_query = '''
    SELECT 
        reg.population,
        reg.gdp_per_capita,
        COUNT(m.id) as total_movies,
        AVG(r.revenue) as avg_revenue,
        AVG(r.budget) as avg_budget,
        AVG(r.tmdb_rating) as avg_rating,
        SUM(r.revenue) as total_revenue
    FROM regions reg
    LEFT JOIN movies m ON m.region = reg.country_code
    LEFT JOIN movie_ratings r ON m.id = r.movie_id
    WHERE reg.country_code = 'US'
    '''
    
    us_stats = pd.read_sql_query(us_query, conn)
    
    # Add US regional analysis
    regional_query = '''
    SELECT 
        COALESCE(r.us_region, 'National') as region,
        COUNT(DISTINCT m.id) as movie_count,
        AVG(mr.tmdb_rating) as avg_rating,
        AVG(mr.revenue) as avg_revenue,
        AVG(mr.budget) as avg_budget,
        SUM(mr.revenue) as total_revenue,
        r.population
    FROM regions r
    LEFT JOIN movies m ON m.region = r.country_code
    LEFT JOIN movie_ratings mr ON m.id = mr.movie_id
    WHERE r.country_code = 'US'
    GROUP BY r.us_region
    ORDER BY 
        CASE 
            WHEN r.us_region IS NULL THEN 0 
            ELSE 1 
        END,
        r.us_region
    '''
    
    regional_stats = pd.read_sql_query(regional_query, conn)
    
    conn.close()
    
    # Write results to file
    with open('movie_analysis_results.txt', 'w') as f:
        f.write("US Action Movies Analysis Results\n")
        f.write("===============================\n\n")
        
        f.write("1. Yearly Statistics\n")
        f.write("-----------------\n")
        for _, row in yearly_stats.iterrows():
            f.write(f"\nYear: {row['release_year']}\n")
            f.write(f"Number of Movies: {row['movie_count']}\n")
            f.write(f"Average TMDB Rating: {row['avg_rating']:.2f}\n")
            f.write(f"Average Revenue: ${row['avg_revenue']:,.2f}\n")
            f.write(f"Average Budget: ${row['avg_budget']:,.2f}\n")
            f.write(f"Profitable Movies: {row['profitable_movies']}\n")
        
        f.write("\n\n2. Rotten Tomatoes Analysis\n")
        f.write("-------------------------\n")
        for _, row in rt_stats.iterrows():
            f.write(f"\nRating Category: {row['rating_category']}\n")
            f.write(f"Number of Movies: {row['movie_count']}\n")
            f.write(f"Average Revenue: ${row['avg_revenue']:,.2f}\n")
        
        f.write("\n\n3. Performance Analysis by TMDB Rating\n")
        f.write("----------------------------------\n")
        for _, row in performance_stats.iterrows():
            f.write(f"\nRating Category: {row['rating_category']}\n")
            f.write(f"Number of Movies: {row['movie_count']}\n")
            f.write(f"Average Revenue: ${row['avg_revenue']:,.2f}\n")
            f.write(f"Average Budget: ${row['avg_budget']:,.2f}\n")
            if pd.notnull(row['avg_roi']):
                f.write(f"Average ROI: {(row['avg_roi'] - 1) * 100:.1f}%\n")
            else:
                f.write("Average ROI: Not available\n")
        
        f.write("\n\n4. US Market Analysis (with Geonames Data)\n")
        f.write("---------------------------------------\n")
        if not us_stats.empty:
            row = us_stats.iloc[0]
            f.write(f"Total Movies: {row['total_movies']}\n")
            f.write(f"Population: {row['population']:,}\n")
            f.write(f"GDP per capita: ${row['gdp_per_capita']:,.2f}\n")
            f.write(f"Average Movie Rating: {row['avg_rating']:.2f}\n")
            f.write(f"Average Movie Revenue: ${row['avg_revenue']:,.2f}\n")
            f.write(f"Average Movie Budget: ${row['avg_budget']:,.2f}\n")
            f.write(f"Total Box Office Revenue: ${row['total_revenue']:,.2f}\n")
            # Calculate per capita metrics
            movies_per_million = (row['total_movies'] / row['population']) * 1000000
            revenue_per_capita = row['total_revenue'] / row['population']
            f.write(f"Movies per Million People: {movies_per_million:.2f}\n")
            f.write(f"Box Office Revenue per Capita: ${revenue_per_capita:.2f}\n")
        
        f.write("\n\n4. US Regional Analysis\n")
        f.write("--------------------\n")
        for _, row in regional_stats.iterrows():
            f.write(f"\nRegion: {row['region']}\n")
            if pd.notnull(row['population']) and row['population'] > 0:
                f.write(f"Population: {row['population']:,}\n")
            f.write(f"Number of Movies: {row['movie_count']}\n")
            f.write(f"Average Rating: {row['avg_rating']:.2f}\n")
            f.write(f"Average Revenue: ${row['avg_revenue']:,.2f}\n")
            f.write(f"Average Budget: ${row['avg_budget']:,.2f}\n")
            f.write(f"Total Revenue: ${row['total_revenue']:,.2f}\n")
            
            if pd.notnull(row['population']) and row['population'] > 0:
                movies_per_million = (row['movie_count'] / row['population']) * 1000000
                revenue_per_capita = row['total_revenue'] / row['population']
                f.write(f"Movies per Million People: {movies_per_million:.2f}\n")
                f.write(f"Revenue per Capita: ${revenue_per_capita:.2f}\n")
    
    print("Analysis complete! Results written to 'movie_analysis_results.txt'")

if __name__ == "__main__":
    calculate_movie_stats() 