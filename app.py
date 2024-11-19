from flask import Flask, render_template, request, jsonify
import requests
import json
import sqlite3

def init_db():
    with sqlite3.connect("cache.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS Movie (
                       imdbID TEXT PRIMARY KEY,
                       title TEXT, 
                       year TEXT,
                       details TEXT 
                       )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS Country (
                       country_name TEXT PRIMARY KEY,
                       flag_url TEXT 
                       )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS MovieCountry (
                            movie_id TEXT,
                            country_name TEXT,
                            FOREIGN KEY (movie_id) REFERENCES Movie(imdbID),
                            FOREIGN KEY (country_name) REFERENCES Country(country_name),
                            PRIMARY KEY (movie_id, country_name)
                          )''')
        conn.commit()
app = Flask(__name__)
apikey = "1ffc252e"

country_code_to_name = {
    "USA":"United States",
    "UK":"United Kingdom"
}

def searchfilms(search_text, page=1):

    url = f"https://www.omdbapi.com/?s={search_text}&page={page}&apikey={apikey}"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve search results.")
        return None
        
    
def getmoviedetails(movie):
    imdbID = movie["imdbID"]
    with sqlite3.connect("cache.db") as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT details FROM Movie WHERE imdbID=?", (imdbID,))
            cached_movie = cursor.fetchone()
            if cached_movie:
                return json.loads(cached_movie[0])
            else: 
                url = "https://www.omdbapi.com/?i=" + movie["imdbID"] + "&apikey=" + apikey
                response = requests.get(url)
                if response.status_code == 200:
                    moviedetails = response.json()
                    conn.execute("BEGIN")
                    cursor.execute("INSERT OR REPLACE INTO Movie (imdbID, title, year, details) VALUES (?,?,?,?)",
                               (imdbID, moviedetails["Title"], moviedetails["Year"],json.dumps(moviedetails)))
                    countries = [country.strip() for country in moviedetails["Country"].split(",")] if "Country" in moviedetails else []
                    #print(f"Countries for movie {moviedetails['Title']}: {countries}")

                    for country in countries:
                        cursor.execute("INSERT OR IGNORE INTO MovieCountry (movie_id, country_name) VALUES (?, ?)", (imdbID, country))
                        #print(f"Inserted country '{country}' for movie '{imdbID}'")
                    conn.commit()
                    return moviedetails
                else:
                    print("Failed to retrieve search results.")
                    return None
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return None
    
    

def get_country_flag(fullname):
    if fullname in country_code_to_name:
        fullname = country_code_to_name[fullname]
    with sqlite3.connect("cache.db") as conn:
        try: 
            cursor = conn.cursor()
            cursor.execute("SELECT flag_url FROM Country WHERE country_name=?", (fullname,))
            cached_flag = cursor.fetchone()
            if cached_flag:
                return cached_flag[0]
            else:
                url = f"https://restcountries.com/v3.1/name/{fullname}?fullText=true"
                response = requests.get(url)
                if response.status_code == 200:
                    country_data = response.json()
                    conn.execute("BEGIN")
                    if country_data:
                        flag_url = country_data[0].get("flags",{}).get("svg",None)
                        if flag_url:
                            #print(f"Flag URL for {fullname}: {flag_url}")  # Verifica la URL de la bandera
                            cursor.execute("INSERT OR REPLACE INTO Country (country_name, flag_url) VALUES(?,?)",(fullname,flag_url))
                            conn.commit()
                            return flag_url
                else:
                    print(f"Failed to retrieve flag for country: {fullname}")
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return None

def merge_data_with_flags(filter, page):
    filmssearch = searchfilms(filter,page)
    if not filmssearch or "Search" not in filmssearch:
        return[] 
    moviesdetailswithflags = []
    for movie in filmssearch["Search"]:
         moviedetails = getmoviedetails(movie)
         if moviedetails:
            countriesNames = moviedetails["Country"].split(",")
            countries = []
            for country in countriesNames:
                c_fullname=country.strip()
                flag_url = get_country_flag(c_fullname)
                countrywithflag = {
                    "name" : c_fullname,
                    "flag" : flag_url
                }
                countries.append(countrywithflag)
            with sqlite3.connect("cache.db") as conn:
                cursor = conn.cursor()
                cursor.execute('''SELECT c.country_name, c.flag_url
                               FROM MovieCountry mc
                               JOIN Country c ON mc.country_name = c.country_name
                               WHERE mc.movie_id=?                               
                               ''', (moviedetails["imdbID"],))
                countries = [{"name": row[0],"flag":row[1]} for row in cursor.fetchall()]
                #print(f"Countries for movie {moviedetails['Title']}: {countries}")
            moviewithflags = {
                "title": moviedetails["Title"],
                "year": moviedetails["Year"],
                "countries": countries
            }
            moviesdetailswithflags.append(moviewithflags)
    #print(moviesdetailswithflags)
    return moviesdetailswithflags

@app.route("/")
def index():
    filter = request.args.get("filter", "").upper()
    page = int(request.args.get("page", 1))
    movies = merge_data_with_flags(filter,page)
    total_result = 50
    results_per_page = 10
    total_pages = (total_result//results_per_page)+(1 if total_result%results_per_page else 0)
    return render_template("index.html", movies=movies, total_pages=total_pages, current_page=page)

@app.route("/api/movies")
def api_movies():
    filter = request.args.get("filter", "")
    page=int(request.args.get("page",1))

    movies = merge_data_with_flags(filter,page)
    return jsonify({"movies":movies})    

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

