import sqlite3
import requests
import json
from visualizations import create_visualizations

def init_db():
    """Initialize the database with tables"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    cursor.execute('''DROP TABLE IF EXISTS regions''')
    cursor.execute('''
    CREATE TABLE regions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  country_code TEXT,
                  state_name TEXT,
                  us_region TEXT,
                  state_code TEXT,
                  population INTEGER,
                  age_group TEXT,
                  age_population INTEGER,
                  percentage_of_state REAL,
                  UNIQUE(country_code, state_code, age_group))
    ''')
    
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
    
    params = {
        "get": "NAME,POP_2021",
        "for": "state:*",
        "key": api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        print("\nFetching Census Population Estimates data...")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("\nData received successfully!")
            data = response.json()
            
            conn = sqlite3.connect('movies.db')
            cursor = conn.cursor()
            
            print("\nProcessing state data...")
            
            
            region_populations = {'Northeast': 0, 'Midwest': 0, 'South': 0, 'West': 0}
            state_populations = {}
            total_us_population = 0
            
            
            for row in data[1:]:  
                full_state_name = row[0]
                state_population = int(row[1])
                state_name = full_state_name.split(',')[0]
                
                if state_name in state_info:
                    state_code, region = state_info[state_name]
                    region_populations[region] += state_population
                    state_populations[state_name] = state_population
                    total_us_population += state_population
            
           
            with open('demographic_analysis.txt', 'w') as f:
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
                            
                            
                            cursor.execute('''
                            INSERT OR REPLACE INTO regions 
                            (country_code, state_name, us_region, state_code, population, age_group, age_population, percentage_of_state)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', ('US', state_name, region, state_code, state_pop, age_group, age_pop, percentage))
                
                
                f.write("\nUS Age Demographics Summary:\n")
                f.write("=" * 50 + "\n")
                for age_group, (_, percentage) in age_groups.items():
                    us_age_pop = int(total_us_population * (percentage / 100))
                    f.write(f"{age_group}: {us_age_pop:,} ({percentage:.1f}% of total population)\n")
            
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