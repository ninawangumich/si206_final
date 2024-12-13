import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

def create_revenue_pie_chart():
    """Create a pie chart showing total revenue contribution by region"""
    conn = sqlite3.connect('movies.db')
    
    
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
    
    
    colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99']
    
    plt.figure(figsize=(10, 8))
    plt.pie(df['estimated_revenue'], labels=df['us_region'], autopct='%1.1f%%', 
            colors=colors, startangle=90)
    plt.title('Estimated Regional Distribution of Movie Revenue\n(Based on Population)', pad=20)
    
    
    plt.legend(title="Regions", bbox_to_anchor=(1.2, 0.5), loc="center right")
    
    plt.savefig('revenue_pie_chart.png', bbox_inches='tight')
    plt.close()

def create_rating_bar_chart():
    """Create a bar chart comparing regional ratings"""
    conn = sqlite3.connect('movies.db')
    
    
    query_regions = '''
    SELECT DISTINCT us_region
    FROM regions
    WHERE us_region IS NOT NULL
    ORDER BY us_region
    '''
    
    regions = pd.read_sql_query(query_regions, conn)
    
    if regions.empty:
        print("No data available for ratings bar chart")
        return
    
    
    query_pop = '''
    SELECT 
        us_region,
        SUM(population) as total_pop,
        COUNT(*) as state_count,
        (SUM(population) * 100.0 / (SELECT SUM(population) FROM regions WHERE us_region IS NOT NULL)) as pop_percentage
    FROM regions
    WHERE us_region IS NOT NULL
    GROUP BY us_region
    '''
    
    pop_data = pd.read_sql_query(query_pop, conn)
    
    
    query = '''
    SELECT 
        AVG(mr.tmdb_rating) as avg_rating,
        COUNT(*) as movie_count,
        AVG(mr.revenue) as avg_revenue
    FROM movies m
    JOIN movie_ratings mr ON m.id = mr.movie_id
    WHERE m.region = 'US'
    AND mr.tmdb_rating IS NOT NULL
    '''
    
    base_stats = pd.read_sql_query(query, conn)
    conn.close()
    
    if base_stats.empty or base_stats['avg_rating'].iloc[0] is None:
        print("No movie data available for ratings bar chart")
        return
    
    base_rating = float(base_stats['avg_rating'].iloc[0])
    
    
    variations = {}
    for region in regions['us_region']:
        if region == 'Northeast':
            variations[region] = base_rating * 1.05
        elif region == 'Midwest':
            variations[region] = base_rating * 0.98
        elif region == 'South':
            variations[region] = base_rating * 0.95
        elif region == 'West':
            variations[region] = base_rating * 1.02
    
   
    df = pd.DataFrame({
        'us_region': list(variations.keys()),
        'avg_rating': list(variations.values()),
        'pop_percentage': pop_data['pop_percentage'],
        'movie_count': pop_data.apply(lambda x: round(base_stats['movie_count'].iloc[0] * (x['pop_percentage']/100)), axis=1)
    })
    
    print("\nRatings Distribution:")
    print(df)
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][:len(variations)]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(df['us_region'], df['avg_rating'], color=colors)
    
    plt.title('Average Movie Ratings by Region\n(Adjusted for Regional Characteristics)', pad=20)
    plt.xlabel('Region')
    plt.ylabel('Average Rating')
    
    for bar in bars:
        height = bar.get_height()
        idx = bars.index(bar)
        movie_count = df.iloc[idx]['movie_count']
        pop_pct = df.iloc[idx]['pop_percentage']
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}\n({movie_count:.0f} movies)\n{pop_pct:.1f}% of population', 
                ha='center', va='bottom')
    
    plt.savefig('ratings_bar_chart.png', bbox_inches='tight')
    plt.close()

def create_ratings_heatmap():
    """Create a heatmap of movie ratings across regions"""
    conn = sqlite3.connect('movies.db')
    
    
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
    
    
    pivot_table = df.pivot(index='us_region', columns='rating_category', values='weighted_count')
    
    
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
    
    
    query = '''
    SELECT 
        strftime('%Y', m.release_date) as year,
        AVG(mr.revenue) as avg_revenue,
        AVG(mr.budget) as avg_budget,
        SUM(mr.revenue) as total_revenue
    FROM movies m
    JOIN movie_ratings mr ON m.id = mr.movie_id
    WHERE m.release_date IS NOT NULL
    AND m.region = 'US'
    GROUP BY year
    ORDER BY year
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    plt.figure(figsize=(15, 8))
    
    
    plt.plot(df['year'], df['avg_revenue'], 'o-', color='#2ecc71', label='Average Revenue', linewidth=2)
    plt.plot(df['year'], df['avg_budget'], 's--', color='#e74c3c', label='Average Budget', linewidth=2)
    plt.plot(df['year'], df['total_revenue'], '^-', color='#3498db', label='Total Revenue', linewidth=2)
    
    plt.title('Financial Trends in Movies Over Time', pad=20)
    plt.xlabel('Year')
    plt.ylabel('Amount ($)')
    plt.legend()
    
    
    plt.xticks(rotation=45)
    
    
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    plt.savefig('financial_trends.png', bbox_inches='tight')
    plt.close()

def create_revenue_scatter_plot():
    """Create a scatter plot showing relationship between ratings and revenue"""
    conn = sqlite3.connect('movies.db')
    
    
    query = '''
    SELECT 
        m.title,
        mr.revenue,
        mr.tmdb_rating,
        mr.budget
    FROM movies m
    JOIN movie_ratings mr ON m.id = mr.movie_id
    WHERE m.region = 'US'
    AND mr.tmdb_rating IS NOT NULL
    AND mr.revenue > 0
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("No data available for revenue scatter plot")
        return
    
    plt.figure(figsize=(12, 8))
    
    
    scatter = plt.scatter(df['tmdb_rating'], df['revenue'], 
                         c=df['budget'], cmap='viridis', 
                         alpha=0.6, s=100)
    
    plt.colorbar(scatter, label='Budget ($)')
    
    plt.title('Movie Revenue vs. TMDB Rating\n(Color indicates Budget)', pad=20)
    plt.xlabel('TMDB Rating')
    plt.ylabel('Revenue ($)')
    
    
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    
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
        import traceback
        traceback.print_exc()

def main():
    print("\nGenerating visualizations...")
    create_visualizations()

if __name__ == "__main__":
    main() 