import sqlite3
import requests
import json
from visualizations import create_visualizations

def init_db():
    """Initialize the database with normalized tables"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    
    cursor.execute('''DROP TABLE IF EXISTS regions''')
    cursor.execute('''DROP TABLE IF EXISTS state_lookup''')
    cursor.execute('''DROP TABLE IF EXISTS region_lookup''')
    
    
    cursor.execute('''
    CREATE TABLE state_lookup
                 (state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  state_name TEXT UNIQUE,
                  state_code TEXT UNIQUE)
    ''')
    
    
    cursor.execute('''
    CREATE TABLE region_lookup
                 (region_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  region_name TEXT UNIQUE)
    ''')
    
    
    cursor.execute('''
    CREATE TABLE regions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  state_id INTEGER,
                  region_id INTEGER,
                  population INTEGER,
                  age_group TEXT,
                  age_population INTEGER,
                  percentage_of_state REAL,
                  FOREIGN KEY (state_id) REFERENCES state_lookup(state_id),
                  FOREIGN KEY (region_id) REFERENCES region_lookup(region_id),
                  UNIQUE(state_id, age_group))
    ''')
    
    
    unique_regions = {'Northeast', 'Midwest', 'South', 'West'}
    for region in unique_regions:
        cursor.execute('INSERT INTO region_lookup (region_name) VALUES (?)', (region,))
    
    
    for state_name, (state_code, _) in state_info.items():
        cursor.execute('INSERT INTO state_lookup (state_name, state_code) VALUES (?, ?)',
                      (state_name, state_code))
    
    conn.commit()
    conn.close()


age_groups = {
    'Age Under 5': ('0-4', 6.1),
    'Age 5-9': ('5-9', 6.2),
    'Age 10-14': ('10-14', 6.4),
    'Age 15-17': ('15-17', 3.8),
    'Age 18-19': ('18-19', 2.5)
}


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

def fetch_population_data():
    """Fetch population data from Census API and store in database"""
    api_key = "9e943855717059bb35eddd4b296651c010db664a"
    base_url = "https://api.census.gov/data/2021/pep/population"
    
    chunk_size = 25
    all_data = []
    
    try:
        params = {
            "get": "NAME,POP_2021",
            "for": "state:*",
            "key": api_key
        }
        
        response = requests.get(base_url, params=params)
        print("\nFetching Census Population Estimates data...")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("\nData received successfully!")
            data = response.json()
            
            state_chunks = [data[i:i + chunk_size] for i in range(1, len(data), chunk_size)]
            
            conn = sqlite3.connect('movies.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT state_id, state_name FROM state_lookup')
            state_id_map = {name: id for id, name in cursor.fetchall()}
            
            cursor.execute('SELECT region_id, region_name FROM region_lookup')
            region_id_map = {name: id for id, name in cursor.fetchall()}
            
            print("\nProcessing state data in chunks...")
            
            region_populations = {'Northeast': 0, 'Midwest': 0, 'South': 0, 'West': 0}
            state_populations = {}
            total_us_population = 0
            rows_processed = 0
            
            for chunk_index, chunk in enumerate(state_chunks):
                print(f"\nProcessing chunk {chunk_index + 1} ({len(chunk)} states)...")
                
                for row in chunk:
                    full_state_name = row[0]
                    state_population = int(row[1])
                    state_name = full_state_name.split(',')[0]
                    
                    if state_name in state_info:
                        state_code, region = state_info[state_name]
                        region_populations[region] += state_population
                        state_populations[state_name] = state_population
                        total_us_population += state_population
                        
                        state_id = state_id_map[state_name]
                        region_id = region_id_map[region]
                        
                        for age_group, (_, percentage) in age_groups.items():
                            age_pop = int(state_population * (percentage / 100))
                            cursor.execute('''
                            INSERT OR REPLACE INTO regions 
                            (state_id, region_id, population, age_group, age_population, percentage_of_state)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ''', (state_id, region_id, state_population, age_group, age_pop, percentage))
                            rows_processed += 1
                
                conn.commit()
                print(f"Processed {len(chunk)} states in chunk {chunk_index + 1}")
            
            
            cursor.execute('''
                SELECT r.*, sl.state_name, sl.state_code, rl.region_name 
                FROM regions r
                JOIN state_lookup sl ON r.state_id = sl.state_id
                JOIN region_lookup rl ON r.region_id = rl.region_id
            ''')
            
            cursor.execute('SELECT COUNT(*) FROM regions')
            total_rows = cursor.fetchone()[0]
            print(f"\nTotal rows stored in database: {total_rows}")
            print(f"Total rows processed in this run: {rows_processed}")
            
            
            with open('census_analysis.txt', 'w') as f:
                f.write("Regional Population Analysis with Demographics (2021)\n")
                f.write("===============================================\n\n")
                f.write(f"Total US Population: {total_us_population:,}\n")
                f.write("-" * 50 + "\n\n")
                
                
                f.write("Regional Population Summary:\n")
                f.write("-" * 50 + "\n")
                for region in ['Northeast', 'Midwest', 'South', 'West']:
                    region_total = region_populations[region]
                    region_percentage = (region_total / total_us_population) * 100
                    f.write(f"{region}: {region_total:,} ({region_percentage:.1f}% of US)\n")
                
                
                f.write("\nDetailed Population and Demographic Breakdown by Region:\n")
                f.write("=" * 70 + "\n")
                
                for region in ['Northeast', 'Midwest', 'South', 'West']:
                    region_total = region_populations[region]
                    f.write(f"\n{region} Region:\n")
                    f.write(f"Total Population: {region_total:,}\n\n")
                    f.write("States and Demographics:\n")
                    
                    
                    states_in_region = [(name, code) for name, (code, reg) in state_info.items() if reg == region]
                    for state_name, state_code in sorted(states_in_region):
                        state_pop = state_populations[state_name]
                        state_percentage = (state_pop / region_total) * 100
                        f.write(f"\n  {state_name} ({state_code}):\n")
                        f.write(f"  Total Population: {state_pop:,} ({state_percentage:.1f}% of region)\n")
                        
                        
                        f.write("  Age Demographics:\n")
                        for age_group, (_, percentage) in age_groups.items():
                            age_pop = int(state_pop * (percentage / 100))
                            f.write(f"    {age_group}: {age_pop:,} ({percentage:.1f}%)\n")
            
            conn.commit()
            print(f"Demographic analysis has been written to 'demographic_analysis.txt'")
            print(f"Total US Population: {total_us_population:,}")
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