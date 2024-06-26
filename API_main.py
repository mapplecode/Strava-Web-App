import os
import csv
from flask import Flask, request, jsonify, render_template, redirect, session
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'Strava'
client_id = '124236'
client_secret = 'f91f74dcbc3defbe8b32e7df3b98dad0f752e8d8'

# Function to get CSV file path based on athlete ID
def get_csv_path(athlete_id):
    return f"/home/equinoxagents/mysite/{athlete_id}_activities.csv"
    
def save_activities_to_csv(athlete_id, activities):
    csv_file = get_csv_path(athlete_id)
    existing_activities = get_activities_from_csv(athlete_id)
    new_activities = [activity for activity in activities if activity not in existing_activities]
    print("New activities to be added to CSV:", new_activities)
    with open(csv_file, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['type', 'distance', 'start_date'])
        if os.stat(csv_file).st_size == 0:  # Check if file is empty
            writer.writeheader()  # Write header if file is empty
        for activity in new_activities:
            writer.writerow(activity)

def get_activities_from_csv(athlete_id):
    csv_file = get_csv_path(athlete_id)
    activities = []
    if os.path.exists(csv_file):
        with open(csv_file, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                activities.append(dict(row))
    return activities

def save_tokens_to_file(access_token, refresh_token):
    with open('/home/equinoxagents/mysite/tokens.txt', 'w') as file:
        file.write(f"Access Token: {access_token}\n")
        file.write(f"Refresh Token: {refresh_token}\n")

def get_tokens_from_file():
    with open('/home/equinoxagents/mysite/tokens.txt', 'r') as file:
        lines = file.readlines()
        access_token = lines[0].split(':')[1].strip()
    return access_token

@app.route('/')
def home():
    return render_template('signup.html')

@app.route('/login')
def login():
    redirect_uri = request.base_url + '/callback'
    authorize_url = f'https://www.strava.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=activity:write,activity:read_all'
    return redirect(authorize_url)

@app.route('/login/callback')
def login_callback():
    code = request.args.get('code')
    if code:
        token_url = 'https://www.strava.com/oauth/token'
        payload = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
        }
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            save_tokens_to_file(access_token, refresh_token)
            athlete_id = str(tokens.get('athlete').get('id'))
            activities = get_activities_from_csv(athlete_id)
            if not activities:
                activities = get_activities(access_token)
                save_activities_to_csv(athlete_id, activities)
            return render_template('index.html')
        else:
            return 'Failed to login. Error: ' + response.text
    else:
        return 'Authorization code not received.'


def get_activities(access_token):
    all_activities = []
    url = "https://www.strava.com/api/v3/activities"
    payload = {}
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    page = 1
    per_page = 30

    current_date = datetime.now()
    year_start = datetime(current_date.year, 1, 1)
    while True:
        params = {'page': page, 'per_page': per_page}
        response = requests.get(url, headers=headers, params=params)
        print(response.text)
        if response.status_code == 200:
            activities = response.json()
            if not activities:  # No more activities to fetch
                break
            for activity in activities:
                start_date = datetime.strptime(activity['start_date'], "%Y-%m-%dT%H:%M:%SZ")
                if start_date >= year_start:
                    relevant_fields = {
                        'type': activity['type'],
                        'distance': activity['distance'],
                        'start_date': activity['start_date']
                    }
                    all_activities.append(relevant_fields)
                else:
                    break
            page += 1
        else:
            print("Failed to fetch activities:", response.text)
            break
    return all_activities

def get_distances_by_type_from_csv(athlete_id):
    activities = get_activities_from_csv(athlete_id)
    distances_by_type = {}
    last_4_weeks_avg_by_type = {}

    current_date = datetime.now()
    year_start = datetime(current_date.year, 1, 1)

    for activity in activities:
        activity_type = activity['type']
        distance = float(activity['distance'])
        start_date = datetime.strptime(activity['start_date'], "%Y-%m-%dT%H:%M:%SZ")
        current_date = datetime.now()
        if activity_type in distances_by_type:
            distances_by_type[activity_type]['ytd'] += distance
        else:
            distances_by_type[activity_type] = {'ytd': distance, 'last_4_weeks': 0}
        if start_date >= (current_date - timedelta(weeks=4)):
            distances_by_type[activity_type]['last_4_weeks'] += distance
    for activity_type, distances in distances_by_type.items():
        last_4_weeks_avg_by_type[activity_type] = distances['last_4_weeks'] / 4 if distances['last_4_weeks'] != 0 else 0

    return distances_by_type, last_4_weeks_avg_by_type

def get_distances_by_type_from_csv(athlete_id):
    activities = get_activities_from_csv(athlete_id)
    distances_by_type = {}
    last_4_weeks_avg_by_type = {}

    current_date = datetime.now()
    year_start = datetime(current_date.year, 1, 1)

    for activity in activities:
        activity_type = activity['type']
        distance = float(activity['distance'])
        start_date = datetime.strptime(activity['start_date'], "%Y-%m-%dT%H:%M:%SZ")
        current_date = datetime.now()
        if activity_type in distances_by_type:
            distances_by_type[activity_type]['ytd'] += distance
        else:
            distances_by_type[activity_type] = {'ytd': distance, 'last_4_weeks': 0}
        if start_date >= (current_date - timedelta(weeks=4)):
            distances_by_type[activity_type]['last_4_weeks'] += distance
    for activity_type, distances in distances_by_type.items():
        last_4_weeks_avg_by_type[activity_type] = distances['last_4_weeks'] / 4 if distances['last_4_weeks'] != 0 else 0

    return distances_by_type, last_4_weeks_avg_by_type

def update_description(activity_id, athlete_id, activities):
    new_activity = []
    distances_by_type, last_4_weeks_avg_by_type = get_distances_by_type_from_csv(athlete_id)

    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    access_token = get_tokens_from_file()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    # Get activity details
    response = requests.get(url, headers=headers)
    activity_data = response.json()

    try:
        relevant_fields = {
            'type': activity_data['type'],
            'distance': activity_data['distance'],
            'start_date': activity_data['start_date']
        }
        new_activity.append(relevant_fields)
        print("---------------------------------------------------------------------------------", new_activity)
        save_activities_to_csv(athlete_id, new_activity)
        if 'description' not in activity_data or not activity_data['description']:
            activity_type = activity_data.get('type')
            if activity_type:
                distances = distances_by_type.get(activity_type)
                if distances:
                    ytd_distance_km = distances['ytd'] / 1000  # Convert meters to kilometers
                    last_4_weeks_avg_km = last_4_weeks_avg_by_type[activity_type] / 1000  # Convert meters to kilometers

                    description = f"{activity_type}:\n"
                    description += f"Year to date: {ytd_distance_km:.2f} km\n"
                    description += f"Last 4 weeks avg: {last_4_weeks_avg_km:.2f} km\n"
                    description += "Try for free at https://racestats.com/"

                    payload = {'description': description}
                    response = requests.put(url, headers=headers, data=payload)
                    print(response.text)
                else:
                    print(f"No distance data available for activity type: {activity_type}")
            else:
                print("Activity type not found in the response, skipping update.")
        else:
            print("Description already exists, skipping update.")
    except Exception as e:
        print("Exception occurred in update function:", e)

@app.route('/webhook', methods=['POST'])
def handle_strava_webhook():
    event_data = request.json
    if 'owner_id' in event_data and 'object_id' in event_data:
        athlete_id = str(event_data['owner_id'])
        activity_id = str(event_data['object_id'])
        print("New activity recieved",event_data)
        url = f"https://www.strava.com/api/v3/activities/{activity_id}"
        access_token = get_tokens_from_file()
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(url, headers=headers)
        activity_data = response.json()
        print("Received activity update for activity ID:", activity_data)
        activities = get_activities_from_csv(athlete_id)
        print("+++++++++++++++++++++++++++++", activities)
        try:
            activities_with_type = [activity for activity in activities if 'type' in activity]
            update_description(activity_id, athlete_id, activities_with_type)
        except Exception as e:
            print("Exception Occurred:", e)
        print("Description updated for activity ID:", activity_id)
        return jsonify({"status": "success"}), 200
    else:
        print("Webhook event does not contain required data")
        return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(port=3000)
