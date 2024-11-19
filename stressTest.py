import concurrent.futures
import requests

def simulate_request(filter_text, page):
    url = f"http://localhost:5000/api/movies?filter={filter_text}&page={page}"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}, Response: {response.json()}")
    except Exception as e:
        print(f"Error during request: {e}")

# Configuración de prueba de estrés
FILTER_TEXT = "BATMAN"
PAGES = range(1, 6)
NUM_USERS = 50

with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_USERS) as executor:
    futures = [
        executor.submit(simulate_request, FILTER_TEXT, page)
        for page in PAGES for _ in range(NUM_USERS // len(PAGES))
    ]

# Esperar a que todas las solicitudes se completen
concurrent.futures.wait(futures)
