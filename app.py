from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)
apikey = "1ffc252e"

countryFlags = {}

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
    url = "https://www.omdbapi.com/?i=" + movie["imdbID"] + "&apikey=" + apikey
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve search results.")
        return None

def get_country_flag(fullname):

    if fullname in country_code_to_name:
        fullname = country_code_to_name[fullname]

    if fullname in countryFlags:
        return countryFlags[fullname]
    
    url = f"https://restcountries.com/v3.1/name/{fullname}?fullText=true"
    response = requests.get(url)

    if response.status_code == 200:
        country_data = response.json()
        if country_data:
            countryFlags[fullname] = country_data[0].get("flags", {}).get("svg", None)
            return countryFlags[fullname]
    print(f"Failed to retrieve flag for country code: {fullname}")
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
                countrywithflag = {
                    "name": country.strip(),
                    "flag": get_country_flag(country.strip())
                }
                countries.append(countrywithflag)
            moviewithflags = {
                "title": moviedetails["Title"],
                "year": moviedetails["Year"],
                "countries": countries
            }
            moviesdetailswithflags.append(moviewithflags)

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
    app.run(debug=True)

