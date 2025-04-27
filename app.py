from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')  # Get the API key from .env
    return render_template('index.html', api_key=api_key)

@app.route('/waste-info', methods=['POST'])
def waste_info():
    data = request.get_json()
    location = data.get('location')

    if not location:
        return jsonify({"error": "Location not provided."}), 400

    try:
        # Step 1: Geocode the location to get lat/lng
        geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geo_params = {
            "address": location,
            "key": GOOGLE_API_KEY
        }
        geo_response = requests.get(geo_url, params=geo_params)
        geo_data = geo_response.json()

        # NEW: Check if status is OK first
        if geo_data.get('status') != "OK":
            return jsonify({"error": "Geocoding failed. Please check the location or try again later."}), 400

        if not geo_data.get('results'):
            return jsonify({"error": "Location not found."}), 404


        lat = geo_data['results'][0]['geometry']['location']['lat']
        lng = geo_data['results'][0]['geometry']['location']['lng']

        # Ensure that we are working with the correct location and it is accurate enough
        if not lat or not lng:
            return jsonify({"error": "Unable to determine location."}), 400

        centers = []

        # Step 2: Use Nearby Search with a larger radius (e.g., 10-15 km) and more inclusive keywords
        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_params = {
            "location": f"{lat},{lng}",
            "radius": 15000,  # 15 km (in case municipal corporations are slightly farther)
            "keyword": (
                "waste disposal OR recycling center OR scrap yard OR reuse center OR junkyard OR salvage yard OR second hand OR municipal corporation OR city hall OR municipality OR municipal council OR local government OR waste segregation OR public sanitation OR solid waste management OR garbage depot OR recycling depot"
                
            ),
            "type": "establishment",  # Ensuring we're looking for establishments
            "key": GOOGLE_API_KEY
        }

        places_response = requests.get(places_url, params=places_params)
        places_data = places_response.json()

        # Check if we have any nearby places for the provided location
        if places_data.get('results'):
            for place in places_data['results']:
                center = {
                    "name": place.get('name', 'Not available'),
                    "address": place.get('vicinity', 'Not available'),
                    "contact": "Not available",  # Phone needs Place Details API (future improvement)
                    "opening_hours": (
                        "Open now" if place.get('opening_hours', {}).get('open_now') else "Closed now"
                    ) if place.get('opening_hours') else "Not available",
                    "description": get_place_description(place)  # Get better description
                }
                centers.append(center)

        # Step 3: If no nearby places were found, return empty result
        if not centers:
            return jsonify({"reply": []})

        return jsonify({"reply": centers})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal server error."}), 500


def get_place_description(place):
    """
    Function to return the most relevant description.
    Prioritize: types, vicinity, and additional details.
    """
    description = []
    
    # Get place types
    if 'types' in place:
        description.extend(place['types'])
    
    # Get vicinity (address)
    if 'vicinity' in place:
        description.append(f"Located at: {place['vicinity']}")

    # Add a generic fallback if no specific description is found
    if not description:
        description.append("No additional description available")

    return ", ".join(description)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
