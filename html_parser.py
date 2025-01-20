from bs4 import BeautifulSoup
import pandas as pd
import datetime
import pytz

def parse_html_file(html_content):
    """Parse the HTML content and extract game data from the specific table."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the section with "Copy of Your Data"
    data_section = soup.find('h1', string="Copy of Your Data")
    if not data_section:
        raise ValueError("Could not find Copy of Your Data section")
        
    # Find the Call of Duty section
    cod_heading = data_section.find_next('h1', string=" Call of Duty: Black Ops 6")
    if not cod_heading:
        raise ValueError("Could not find Call of Duty: Black Ops 6 heading")
        
    # Find the h2 heading for multiplayer data
    mp_heading = cod_heading.find_next('h2', string="Multiplayer Match Data (reverse chronological)")
    if not mp_heading:
        raise ValueError("Could not find Multiplayer Match Data heading")
    
    # Get the first table after the multiplayer heading
    table = mp_heading.find_next('table')
    if not table:
        raise ValueError("Could not find match data table")
    
    # Get headers from first row
    headers = []
    for th in table.find_all('th'):
        headers.append(th.text.strip())
    
    # Get data rows
    data = []
    for row in table.find_all('tr')[1:]:  # Skip header row
        cols = row.find_all('td')
        if len(cols) > 0:
            row_data = {}
            for i, col in enumerate(cols):
                row_data[headers[i]] = col.text.strip()
            data.append(row_data)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Convert numeric columns
    numeric_columns = ['Score', 'Kills', 'Deaths', 'Shots', 'Hits', 
                      'Headshots', 'Damage Done', 'Damage Taken',
                      'Longest Streak', 'Lifetime Kills', 'Lifetime Deaths',
                      'Lifetime Time Played', 'Assists', 'Executions', 'Suicides',
                      'Armor Collected', 'Armor Equipped', 'Armor Destroyed',
                      'Ground Vehicles Used', 'Air Vehicles Used',
                      'Total XP', 'Score XP', 'Challenge XP', 'Match XP',
                      'Medal XP', 'Bonus XP', 'Misc XP', 'Accolade XP',
                      'Weapon XP', 'Operator XP', 'Clan XP', 'Battle Pass XP',
                      'Rank at Start', 'Rank at End', 'XP at Start', 'XP at End',
                      'Score at Start', 'Score at End', 'Prestige at Start', 'Prestige at End',
                      'Lifetime Wall Bangs', 'Lifetime Games Played', 'Lifetime Wins',
                      'Lifetime Losses', 'Lifetime Hits', 'Lifetime Misses', 'Lifetime Near Misses']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Convert UTC timestamps
    timestamp_columns = ['UTC Timestamp', 'Match Start Timestamp', 'Match End Timestamp']
    for col in timestamp_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    # Convert Skill to float
    if 'Skill' in df.columns:
        df['Skill'] = df['Skill'].astype(float)
    
    # Convert percentage strings to floats
    if 'Percentage Of Time Moving' in df.columns:
        df['Percentage Of Time Moving'] = df['Percentage Of Time Moving'].str.rstrip('%').astype(float) / 100
    
    return df
