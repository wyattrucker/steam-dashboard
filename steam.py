import requests
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIG ---
CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "Steam Dashboard Data"

# --- GOOGLE SHEETS AUTH ---
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# --- HEADERS ---
headers = ["App ID", "Name", "Release Date", "Original Price (USD)", 
           "Current Price (USD)", "Discount %", "Review Score", 
           "Review Count", "Review Summary", "Developer", "Genre"]
sheet.clear()
sheet.append_row(headers)

# --- FETCH 2026 GAMES ---
def get_2026_games():
    url = "https://store.steampowered.com/search/results/"
    params = {
        "sort_by": "Reviews_DESC",
        "json": 1,
        "filter": "released",
        "os": "win",
        "release_time_from": 1735689600,  # Jan 1 2026
        "release_time_to": 1767225600,    # Dec 31 2026
        "count": 50
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    
    print("Raw response keys:", data.keys())
    print("Total results:", data.get("total_count", 0))
    
    items = data.get("items", [])
    print("Items returned:", len(items))
    if items:
        print("First item keys:", items[0].keys())
        print("First item sample:", items[0])
    
    app_ids = []
    for item in items:
        try:
            logo = item.get("logo", "")
            # Extract app ID from URL like .../steam/apps/2420510/capsule...
            parts = logo.split("/apps/")
            if len(parts) > 1:
                aid = int(parts[1].split("/")[0])
                app_ids.append(aid)
        except:
            continue
    
    return app_ids[:20]

# --- FETCH GAME DETAILS ---
def get_game_details(app_id):
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=en"
    response = requests.get(url)
    data = response.json()

    if not data.get(str(app_id), {}).get("success"):
        return None

    game = data[str(app_id)]["data"]

    # Price
    if game.get("is_free"):
        original_price = 0
        current_price = 0
        discount = 0
    elif game.get("price_overview"):
        p = game["price_overview"]
        original_price = p["initial"] / 100
        current_price = p["final"] / 100
        discount = p["discount_percent"]
    else:
        original_price = current_price = discount = "N/A"

    # Reviews
    review_score = game.get("metacritic", {}).get("score", "N/A")

    # Genres
    genres = ", ".join([g["description"] for g in game.get("genres", [])])

    # Developer
    developer = ", ".join(game.get("developers", ["N/A"]))

    # Release date
    release_date = game.get("release_date", {}).get("date", "N/A")

    return [
        app_id,
        game.get("name", "N/A"),
        release_date,
        original_price,
        current_price,
        discount,
        review_score,
        "N/A",  # review count not in appdetails
        "N/A",  # review summary
        developer,
        genres
    ]

# --- MAIN ---
print("Fetching 2026 Steam games...")
app_ids = get_2026_games()
print(f"Found {len(app_ids)} games, fetching details...")

rows = []
for app_id in app_ids:
    row = get_game_details(app_id)
    if row and row[6] != "N/A":  # only keep games with a review score
        rows.append(row)
        print(f"  Added: {row[1]} | Score: {row[6]} | Price: ${row[4]}")
    else:
        print(f"  Skipped: {app_id}")
    time.sleep(1.5)

# Sort by review score, take top 10
rows.sort(key=lambda x: float(x[6]) if x[6] != "N/A" else 0, reverse=True)
top_10 = rows[:10]

for row in top_10:
    sheet.append_row(row)

print(f"\nDone! Added top {len(top_10)} games to your sheet.")