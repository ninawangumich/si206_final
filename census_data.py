import sqlite3
import requests
import json
from visualizations import create_visualizations

def init_db():
    """Initialize the database with tables"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    # Create regions table if it doesn't exist
    cursor.execute('''DROP TABLE IF EXISTS regions''')
    cursor.execute('''
    CREATE TABLE regions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  country_code TEXT,
                  state_name TEXT,
                  us_region TEXT,
                  state_code TEXT,
                  population INTEGER,
                  gdp_per_capita REAL,
                  UNIQUE(country_code, state_code))
    ''')
    
    conn.commit()
    conn.close()

def fetch_population_data():
    """Fetch population data from Census API and store in database"""
    # Census API endpoint and key
    api_key = "9e943855717059bb35eddd4b296651c010db664a"
    base_url = "https://api.census.gov/data/2021/pep/population"
    
    # Parameters for the API request
    params = {
        "get": "NAME,POP_2021",
        "for": "state:*",
        "key": api_key
    }
    
    try:
        # Make the API request
        response = requests.get(base_url, params=params)
        print("\nFetching Census Population Estimates data...")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("\nData received successfully!")
            data = response.json()
            
            # Process the data
            conn = sqlite3.connect('movies.db')
            cursor = conn.cursor()
            
            print("\nProcessing state data...")
            
            # Define US regions with full state names
            state_info = {
                'Alabama': ('AL', 'South'),
                'Alaska': ('AK', 'West'),
                'Arizona': ('AZ', 'West'),
                'Arkansas': ('AR', 'South'),
                'California': ('CA', 'West'),
                'Colorado': ('CO', 'West'),
                'Connecticut': ('CT', 'Northeast'),
                'Delaware': ('DE', 'South'),
                'Florida': ('FL', 'South'),
                'Georgia': ('GA', 'South'),
                'Hawaii': ('HI', 'West'),
                'Idaho': ('ID', 'West'),
                'Illinois': ('IL', 'Midwest'),
                'Indiana': ('IN', 'Midwest'),
                'Iowa': ('IA', 'Midwest'),
                'Kansas': ('KS', 'Midwest'),
                'Kentucky': ('KY', 'South'),
                'Louisiana': ('LA', 'South'),
                'Maine': ('ME', 'Northeast'),
                'Maryland': ('MD', 'South'),
                'Massachusetts': ('MA', 'Northeast'),
                'Michigan': ('MI', 'Midwest'),
                'Minnesota': ('MN', 'Midwest'),
                'Mississippi': ('MS', 'South'),
                'Missouri': ('MO', 'Midwest'),
                'Montana': ('MT', 'West'),
                'Nebraska': ('NE', 'Midwest'),
                'Nevada': ('NV', 'West'),
                'New Hampshire': ('NH', 'Northeast'),
                'New Jersey': ('NJ', 'Northeast'),
                'New Mexico': ('NM', 'West'),
                'New York': ('NY', 'Northeast'),
                'North Carolina': ('NC', 'South'),
                'North Dakota': ('ND', 'Midwest'),
                'Ohio': ('OH', 'Midwest'),
                'Oklahoma': ('OK', 'South'),
                'Oregon': ('OR', 'West'),
                'Pennsylvania': ('PA', 'Northeast'),
                'Rhode Island': ('RI', 'Northeast'),
                'South Carolina': ('SC', 'South'),
                'South Dakota': ('SD', 'Midwest'),
                'Tennessee': ('TN', 'South'),
                'Texas': ('TX', 'South'),
                'Utah': ('UT', 'West'),
                'Vermont': ('VT', 'Northeast'),
                'Virginia': ('VA', 'South'),
                'Washington': ('WA', 'West'),
                'West Virginia': ('WV', 'South'),
                'Wisconsin': ('WI', 'Midwest'),
                'Wyoming': ('WY', 'West')
            }
            
            # Process each state's data
            region_populations = {'Northeast': 0, 'Midwest': 0, 'South': 0, 'West': 0}
            
            # Skip header row
            for row in data[1:]:
                full_state_name = row[0]
                population = int(row[1])
                
                # Get the state name without any extra text
                state_name = full_state_name.split(',')[0]
                
                if state_name in state_info:
                    state_code, region = state_info[state_name]
                    # Insert or update the region data
                    cursor.execute('''
                    INSERT OR REPLACE INTO regions 
                    (country_code, state_name, us_region, state_code, population)
                    VALUES (?, ?, ?, ?, ?)
                    ''', ('US', state_name, region, state_code, population))
                    
                    region_populations[region] += population
            
            conn.commit()
            
            # Print summary of population by region
            print("\nPopulation Estimates by Region (2021):")
            print("-" * 50)
            total_population = 0
            
            for region in ['Northeast', 'Midwest', 'South', 'West']:
                total = region_populations[region]
                print(f"\n{region} Region:")
                print(f"Total Population: {total:,}")
                print("States:")
                cursor.execute('''
                SELECT state_name, population, state_code
                FROM regions 
                WHERE us_region = ?
                ORDER BY state_name
                ''', (region,))
                states = cursor.fetchall()
                for state_name, pop, state_code in states:
                    print(f"  {state_name} ({state_code}): {pop:,}")
                total_population += total
            
            print(f"\nTotal US Population: {total_population:,}")
            
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