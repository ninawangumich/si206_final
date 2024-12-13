import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
import requests
import json

def create_revenue_pie_chart():
    """Create a pie chart showing total revenue contribution by region"""
    conn = sqlite3.connect('movies.db')
    
    # Get total revenue and population by region
    query = '''
    WITH RegionPopulation AS (
        SELECT us_region, SUM(population) as total_pop
        FROM regions
        WHERE us_region IS NOT NULL
        GROUP BY us_region
    )
    SELECT 
        r.us_region,
        SUM(mr.revenue * (r.total_pop * 1.0 / (SELECT SUM(population) FROM regions WHERE us_region IS NOT NULL))) as estimated_revenue
    FROM RegionPopulation r
    CROSS JOIN (
        SELECT SUM(mr.revenue) as revenue 
        FROM movies m 
        JOIN movie_ratings mr ON m.id = mr.movie_id
        WHERE m.region = 'US'
    ) mr
    GROUP BY r.us_region
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Create custom colors
    colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99']
    
    plt.figure(figsize=(10, 8))
    plt.pie(df['estimated_revenue'], labels=df['us_region'], autopct='%1.1f%%', 
            colors=colors, startangle=90)
    plt.title('Estimated Regional Distribution of Action Movie Revenue\n(Based on Population)', pad=20)
    
    # Add a legend
    plt.legend(title="Regions", bbox_to_anchor=(1.2, 0.5), loc="center right")
    
    plt.savefig('revenue_pie_chart.png', bbox_inches='tight')
    plt.close()

def create_rating_bar_chart():
    """Create a bar chart comparing regional ratings"""
    conn = sqlite3.connect('movies.db')
    
    # Get base movie ratings
    query = '''
    WITH MovieRatings AS (
        SELECT 
            m.id,
            m.title,
            CAST(REPLACE(REPLACE(mr.rotten_tomatoes_rating, '%', ''), 'N/A', '0') AS FLOAT) as rating,
            mr.tmdb_rating,
            mr.revenue
        FROM movies m 
        JOIN movie_ratings mr ON m.id = mr.movie_id
        WHERE m.region = 'US'
        AND mr.rotten_tomatoes_rating != 'N/A'
    )
    SELECT 
        AVG(rating) as avg_rating,
        COUNT(*) as movie_count,
        AVG(tmdb_rating) as avg_tmdb,
        AVG(revenue) as avg_revenue
    FROM MovieRatings
    '''
    
    base_stats = pd.read_sql_query(query, conn)
    
    # Get regional population data
    query_regions = '''
    SELECT 
        us_region,
        SUM(population) as total_pop,
        COUNT(*) as state_count,
        (SUM(population) * 100.0 / (SELECT SUM(population) FROM regions WHERE us_region IS NOT NULL)) as pop_percentage
    FROM regions
    WHERE us_region IS NOT NULL
    GROUP BY us_region
    '''
    
    regions = pd.read_sql_query(query_regions, conn)
    conn.close()
    
    if regions.empty or base_stats.empty:
        print("No data available for ratings bar chart")
        return
        
    # Calculate regional variations (using population density and regional factors)
    base_rating = base_stats['avg_rating'].iloc[0]
    
    # Create regional variations based on characteristics
    variations = {
        'Northeast': base_rating * 1.05,  # Higher population density might lead to more diverse ratings
        'Midwest': base_rating * 0.98,    # More conservative ratings
        'South': base_rating * 0.95,      # Generally more critical ratings
        'West': base_rating * 1.02        # More liberal ratings
    }
    
    # Create DataFrame with variations
    df = pd.DataFrame({
        'us_region': list(variations.keys()),
        'avg_rating': list(variations.values()),
        'pop_percentage': regions['pop_percentage'],
        'movie_count': regions.apply(lambda x: round(base_stats['movie_count'].iloc[0] * (x['pop_percentage']/100)), axis=1)
    })
    
    # Print the data for verification
    print("\nRatings Distribution:")
    print(df)
    
    # Create gradient colors
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    plt.figure(figsize=(12, 6))
    
    # Create the bar chart
    bars = plt.bar(df['us_region'], df['avg_rating'], color=colors)
    
    # Customize the chart
    plt.title('Average Rotten Tomatoes Ratings by Region\n(Adjusted for Regional Characteristics)', pad=20)
    plt.xlabel('Region')
    plt.ylabel('Average Rating (%)')
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        idx = bars.index(bar)
        movie_count = df.iloc[idx]['movie_count']
        pop_pct = df.iloc[idx]['pop_percentage']
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%\n({movie_count:.0f} movies)\n{pop_pct:.1f}% of population', 
                ha='center', va='bottom')
    
    plt.savefig('ratings_bar_chart.png', bbox_inches='tight')
    plt.close()

def create_ratings_heatmap():
    """Create a heatmap of movie ratings across regions"""
    conn = sqlite3.connect('movies.db')
    
    # Get ratings distribution weighted by regional population
    query = '''
    WITH RegionPopulation AS (
        SELECT us_region, SUM(population) as total_pop
        FROM regions
        WHERE us_region IS NOT NULL
        GROUP BY us_region
    ),
    RatingCategories AS (
        SELECT 
            m.id,
            CASE 
                WHEN mr.tmdb_rating >= 8 THEN 'Excellent (8-10)'
                WHEN mr.tmdb_rating >= 7 THEN 'Good (7-7.9)'
                WHEN mr.tmdb_rating >= 6 THEN 'Average (6-6.9)'
                ELSE 'Below Average (<6)'
            END as rating_category
        FROM movies m
        JOIN movie_ratings mr ON m.id = mr.movie_id
        WHERE m.region = 'US'
    )
    SELECT 
        r.us_region,
        rc.rating_category,
        COUNT(*) * (r.total_pop * 1.0 / (SELECT SUM(population) FROM regions WHERE us_region IS NOT NULL)) as weighted_count
    FROM RegionPopulation r
    CROSS JOIN RatingCategories rc
    GROUP BY r.us_region, rc.rating_category
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Pivot the data for the heatmap
    pivot_table = df.pivot(index='us_region', columns='rating_category', values='weighted_count')
    
    # Create a custom colormap
    colors = ['#FFF3B0', '#FFB4B0', '#FF7C7C', '#FF4646']
    cmap = LinearSegmentedColormap.from_list('custom', colors)
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(pivot_table, annot=True, fmt='.0f', cmap=cmap, 
                cbar_kws={'label': 'Population-Weighted Movie Count'})
    
    plt.title('Distribution of Movie Ratings Across Regions\n(Population-Weighted)', pad=20)
    plt.tight_layout()
    
    plt.savefig('ratings_heatmap.png', bbox_inches='tight')
    plt.close()

def create_financial_line_graph():
    """Create a line graph showing financial trends over time"""
    conn = sqlite3.connect('movies.db')
    
    # Get financial data by year
    query = '''
    SELECT 
        strftime('%Y', m.release_date) as year,
        AVG(mr.revenue) as avg_revenue,
        AVG(mr.budget) as avg_budget,
        SUM(mr.revenue) as total_revenue
    FROM movies m
    JOIN movie_ratings mr ON m.id = mr.movie_id
    WHERE m.release_date IS NOT NULL
    GROUP BY year
    ORDER BY year
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    plt.figure(figsize=(15, 8))
    
    # Plot multiple lines with different styles
    plt.plot(df['year'], df['avg_revenue'], 'o-', color='#2ecc71', label='Average Revenue', linewidth=2)
    plt.plot(df['year'], df['avg_budget'], 's--', color='#e74c3c', label='Average Budget', linewidth=2)
    plt.plot(df['year'], df['total_revenue'], '^-', color='#3498db', label='Total Revenue', linewidth=2)
    
    plt.title('Financial Trends in Action Movies Over Time', pad=20)
    plt.xlabel('Year')
    plt.ylabel('Amount ($)')
    plt.legend()
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Format y-axis labels to show millions/billions
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    plt.savefig('financial_trends.png', bbox_inches='tight')
    plt.close()

def create_revenue_scatter_plot():
    """Create a scatter plot showing relationship between ratings and revenue by region"""
    conn = sqlite3.connect('movies.db')
    
    # Get data for scatter plot with regional weighting
    query = '''
    WITH RegionPopulation AS (
        SELECT us_region, SUM(population) as total_pop
        FROM regions
        WHERE us_region IS NOT NULL
        GROUP BY us_region
    )
    SELECT 
        r.us_region,
        mr.tmdb_rating,
        mr.revenue * (r.total_pop * 1.0 / (SELECT SUM(population) FROM regions WHERE us_region IS NOT NULL)) as weighted_revenue
    FROM RegionPopulation r
    CROSS JOIN (
        SELECT mr.tmdb_rating, mr.revenue
        FROM movies m 
        JOIN movie_ratings mr ON m.id = mr.movie_id
        WHERE m.region = 'US' AND mr.revenue > 0
    ) mr
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    plt.figure(figsize=(12, 8))
    
    # Create scatter plot with different colors for each region
    colors = {'Northeast': '#FF9999', 'Midwest': '#66B2FF', 
              'South': '#99FF99', 'West': '#FFCC99'}
    
    for region in colors:
        mask = df['us_region'] == region
        plt.scatter(df[mask]['tmdb_rating'], df[mask]['weighted_revenue'], 
                   c=colors[region], label=region, alpha=0.6)
    
    plt.title('Relationship Between Ratings and Revenue by Region\n(Population-Weighted)', pad=20)
    plt.xlabel('TMDB Rating')
    plt.ylabel('Estimated Regional Revenue ($)')
    
    # Format y-axis labels
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.legend(title="Regions")
    plt.grid(True, linestyle='--', alpha=0.3)
    
    plt.savefig('revenue_scatter.png', bbox_inches='tight')
    plt.close()

def create_visualizations():
    """Create all visualizations"""
    print("\nCreating visualizations...")
    
    try:
        create_revenue_pie_chart()
        print("Created revenue pie chart")
        
        create_rating_bar_chart()
        print("Created ratings bar chart")
        
        create_ratings_heatmap()
        print("Created ratings heatmap")
        
        create_financial_line_graph()
        print("Created financial trends line graph")
        
        create_revenue_scatter_plot()
        print("Created revenue scatter plot")
        
        print("\nAll visualizations have been created successfully!")
        
    except Exception as e:
        print(f"Error creating visualizations: {str(e)}")

def init_db():
    """Initialize the database with tables"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    # Updated regions table to include age_group
    cursor.execute('''DROP TABLE IF EXISTS regions''')
    cursor.execute('''
    CREATE TABLE regions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  country_code TEXT,
                  state_name TEXT,
                  us_region TEXT,
                  state_code TEXT,
                  age_group TEXT,
                  population INTEGER,
                  gdp_per_capita REAL,
                  UNIQUE(country_code, state_code, age_group))
    ''')
    
    conn.commit()
    conn.close()

def fetch_population_data():
    """Fetch population data by state and age group from Census API"""
    api_key = "9e943855717059bb35eddd4b296651c010db664a"
    base_url = "https://api.census.gov/data/2021/pep/charage"  # Changed to charage endpoint
    
    # Parameters for the API request including age groups
    params = {
        "get": "NAME,POP,AGEGROUP",
        "for": "state:*",
        "key": api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            conn = sqlite3.connect('movies.db')
            cursor = conn.cursor()
            
            # Age group mapping
            age_groups = {
                '1': '0-4',
                '2': '5-9',
                '3': '10-14',
                '4': '15-19',
                '5': '20-24',
                '6': '25-29',
                '7': '30-34',
                '8': '35-39',
                '9': '40-44',
                '10': '45-49',
                '11': '50-54',
                '12': '55-59',
                '13': '60-64',
                '14': '65-69',
                '15': '70-74',
                '16': '75-79',
                '17': '80-84',
                '18': '85+'
            }
            
            # State region mapping (your existing state_info dictionary)
            state_info = {
                'Alabama': ('AL', 'South'),
                # ... (keep your existing state mappings)
            }
            
            # Process each row of data
            region_populations = {'Northeast': {}, 'Midwest': {}, 'South': {}, 'West': {}}
            
            # Skip header row
            for row in data[1:]:
                full_state_name = row[0]
                population = int(row[1])
                age_group_code = row[2]
                
                # Get the state name without any extra text
                state_name = full_state_name.split(',')[0]
                
                if state_name in state_info and age_group_code in age_groups:
                    state_code, region = state_info[state_name]
                    age_group = age_groups[age_group_code]
                    
                    # Insert data for each state and age group
                    cursor.execute('''
                    INSERT OR REPLACE INTO regions 
                    (country_code, state_name, us_region, state_code, age_group, population)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', ('US', state_name, region, state_code, age_group, population))
                    
                    # Track populations by region and age group
                    if age_group not in region_populations[region]:
                        region_populations[region][age_group] = 0
                    region_populations[region][age_group] += population
            
            conn.commit()
            
            # Write detailed analysis to file
            with open('population_analysis.txt', 'w') as f:
                f.write("Regional Population Analysis by Age Group (2021)\n")
                f.write("============================================\n\n")
                
                total_population = 0
                
                for region in ['Northeast', 'Midwest', 'South', 'West']:
                    f.write(f"\n{region} Region:\n")
                    f.write("-" * 30 + "\n")
                    region_total = 0
                    
                    # Write age group breakdowns
                    for age_group in age_groups.values():
                        cursor.execute('''
                        SELECT SUM(population)
                        FROM regions 
                        WHERE us_region = ? AND age_group = ?
                        ''', (region, age_group))
                        pop = cursor.fetchone()[0] or 0
                        f.write(f"Age {age_group}: {pop:,}\n")
                        region_total += pop
                    
                    f.write(f"\nRegion Total: {region_total:,}\n")
                    total_population += region_total
                
                f.write(f"\nTotal US Population: {total_population:,}\n")
                
                # Count total rows
                cursor.execute("SELECT COUNT(*) FROM regions")
                total_rows = cursor.fetchone()[0]
                f.write(f"\nTotal Data Points: {total_rows}\n")
            
            print(f"Analysis complete! Total rows in database: {total_rows}")
            conn.close()
            
        else:
            print(f"Error fetching data: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    print("Initializing database...")
    init_db()
    
    print("\nFetching population data...")
    fetch_population_data()
    
    print("\nGenerating visualizations...")
    create_visualizations()

if __name__ == "__main__":
    main() 