import os
import csv
from flask import Flask, request, jsonify, render_template, redirect, session
import requests, json
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = 'Strava'

# Replace these values with your Strava application's client_id and client_secret
client_id = '124236'
client_secret = 'f91f74dcbc3defbe8b32e7df3b98dad0f752e8d8'

# Function to get CSV file path based on athlete ID
def get_csv_path(athlete_id):
    return f"/home/equinoxagents/mysite/{athlete_id}_activities.csv"

# Function to get activities from CSV file
def get_activities_from_csv(athlete_id):
    csv_file = get_csv_path(athlete_id)
    activities = []
    if os.path.exists(csv_file):
        with open(csv_file, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                activities.append(dict(row))
    return activities

# Function to save activities to CSV file
def save_activities_to_csv(athlete_id, activities):
    csv_file = get_csv_path(athlete_id)
    existing_activities = get_activities_from_csv(athlete_id)

    # Filter out activities that already exist in the CSV file
    new_activities = [activity for activity in activities if activity not in existing_activities]
    # Print the new activities before saving them
    print("New activities to be added to CSV:", new_activities)
    # Write activities to the CSV file
    with open(csv_file, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['activity_id', 'type', 'distance', 'start_date'])
        if os.stat(csv_file).st_size == 0:  # Check if file is empty
            writer.writeheader()  # Write header if file is empty
        for activity in new_activities:
            writer.writerow(activity)
def save_tokens_to_file(access_token, refresh_token):
    with open('/home/equinoxagents/mysite/tokens.txt', 'w') as file:
        file.write(f"Access Token: {access_token}\n")
        file.write(f"Refresh Token: {refresh_token}\n")

def delete_activity_from_csv(athlete_id, activity_id):
    csv_file = get_csv_path(athlete_id)
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='') as file:
            reader = csv.DictReader(file)
            activities = list(reader)

        # Filter out the activity with the given activity_id
        updated_activities = [activity for activity in activities if activity['activity_id'] != activity_id]

        # Write the updated list back to the CSV
        with open(csv_file, 'w', newline='') as file:
            fieldnames = ['activity_id', 'type', 'distance', 'start_date']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_activities)

        print(f"Activity {activity_id} deleted from CSV for athlete {athlete_id}.")
    else:
        print(f"CSV file for athlete {athlete_id} does not exist.")
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

@app.route('/save_checkbox_states', methods=['POST'])
def save_checkbox_states():
    checkbox_data = request.json
    activity_type_checked = checkbox_data.get('activity_type_checked', False)
    average_distance_checked = checkbox_data.get('average_distance_checked', False)

    # Store checkbox states in a text file
    with open('/home/equinoxagents/mysite/checkbox_states.txt', 'w') as file:
        file.write(f"activity_type_checked: {activity_type_checked}\n")
        file.write(f"average_distance_checked: {average_distance_checked}\n")

    print('Stored checkbox states:', {
        'activity_type_checked': activity_type_checked,
        'average_distance_checked': average_distance_checked
    })
    return jsonify({"status": "success"})


@app.route('/deauthorize')
def deauthorize():
    access_token = session.get('access_token')
    if access_token:
        deauthorize_url = 'https://www.strava.com/oauth/deauthorize'
        response = requests.post(deauthorize_url, data={'access_token': access_token})
        if response.status_code == 200:
            session.pop('access_token', None)
            session.pop('refresh_token', None)
            return redirect('/')
        else:
            return 'Failed to deauthorize. Error: ' + response.text
    else:
        return redirect('/')

def get_checkbox_states():
    # Read checkbox states from the text file
    checkbox_states = {}
    with open('/home/equinoxagents/mysite/checkbox_states.txt', 'r') as file:
        for line in file:
            key, value = line.strip().split(': ')
            checkbox_states[key] = True if value == 'True' else False
    return checkbox_states

def get_activities(access_token):
    all_activities = []
    url = "https://www.strava.com/api/v3/activities"
    payload = {}
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    # Uncomment the pagination code if needed
    page = 1
    per_page = 30  # Adjust per_page as needed

    current_date = datetime.now()
    year_start = datetime(current_date.year, 1, 1)

    # Fetch activities of the current year with pagination
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
                    # Filter only relevant fields
                    relevant_fields = {
                        'activity_id': activity['id'],
                        'type': activity['type'],
                        'distance': activity['distance'],
                        'start_date': activity['start_date']
                    }
                    all_activities.append(relevant_fields)
                else:
                    # Since activities are ordered by date, once we encounter an activity
                    # before the start of the current year, we can stop fetching.
                    break
            page += 1
        else:
            print("Failed to fetch activities:", response.text)
            break

    return all_activities


# Function to get distances by activity type and calculate last 4 weeks average
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

        # Calculate year-to-date (YTD) distance
        if activity_type in distances_by_type:
            distances_by_type[activity_type]['ytd'] += distance
        else:
            distances_by_type[activity_type] = {'ytd': distance, 'last_4_weeks': 0}

        # Calculate distance for the past 4 weeks
        if start_date >= (current_date - timedelta(weeks=4)):
            distances_by_type[activity_type]['last_4_weeks'] += distance

    # Calculate last 4 weeks average distance
    for activity_type, distances in distances_by_type.items():
        last_4_weeks_avg_by_type[activity_type] = distances['last_4_weeks'] / 4 if distances['last_4_weeks'] != 0 else 0

    return distances_by_type, last_4_weeks_avg_by_type

# Function to update description
def update_description(activity_id, athlete_id, activities, activity_type_checked, average_distance_checked):
    new_activity = []
    # Recalculate distances by type and last 4 weeks averages
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
        if 'type' not in activity_data:
            print("Activity type not found in the response, skipping update.")
            return

        relevant_fields = {
            'activity_id': activity_data['id'],
            'type': activity_data['type'],
            'distance': activity_data['distance'],
            'start_date': activity_data['start_date']
        }
        new_activity.append(relevant_fields)
        print("---------------------------------------------------------------------------------", new_activity)
        save_activities_to_csv(athlete_id, new_activity)

        # Check if description exists
        if 'description' not in activity_data or not activity_data['description']:
            description = ""

            # Update description based on checkbox states
            if activity_type_checked:
                activity_type = activity_data.get('type')
                if activity_type:
                    distances = distances_by_type.get(activity_type)
                    if distances:
                        ytd_distance_km = distances['ytd'] / 1000  # Convert meters to kilometers
                        description += f"{activity_type}:\n"
                        description += f"Year to date: {ytd_distance_km:.2f} km\n"

            if average_distance_checked:
                activity_type = activity_data.get('type')
                if activity_type:
                    distances = distances_by_type.get(activity_type)
                    if distances:
                        last_4_weeks_avg_km = last_4_weeks_avg_by_type[activity_type] / 1000  # Convert meters to kilometers
                        if description:  # Append newline if description already has content
                            description += "\n"
                        description += f"Last 4 weeks avg: {last_4_weeks_avg_km:.2f} km\n"

            # Add call to action at the end of the description
            if description:
                description += "Try for free at https://racestats.com/"
                payload = {'description': description}
                response = requests.put(url, headers=headers, data=payload)
                print(response.text)
        else:
            print("Description already exists, skipping update.")
    except Exception as e:
        print("Exception occurred in update function:", e)



@app.route('/webhook', methods=['POST'])
def handle_strava_webhook():
    event_data = request.json
    print("Received webhook event:", event_data)

    if 'owner_id' in event_data and 'object_id' in event_data:
        athlete_id = str(event_data['owner_id'])
        activity_id = str(event_data['object_id'])
        if event_data['aspect_type'] == 'delete':
            # Handle delete event
            delete_activity_from_csv(athlete_id, activity_id)
            print(f"Deleted activity {activity_id} for athlete {athlete_id} from CSV.")
            return jsonify({"status": "success"}), 200

        url = f"https://www.strava.com/api/v3/activities/{activity_id}"
        access_token = get_tokens_from_file()
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(url, headers=headers)
        activity_data = response.json()
        print("Activity data:", activity_data)

        activities = get_activities_from_csv(athlete_id)
        print("Existing activities for athlete:", activities)

        try:
            print("Before update function")
            # Retrieve checkbox states from the text file
            checkbox_states = get_checkbox_states()
            activity_type_checked = checkbox_states.get('activity_type_checked', True)
            average_distance_checked = checkbox_states.get('average_distance_checked', True)

            print(f"Checkbox states - Activity Type Checked: {activity_type_checked}, Average Distance Checked: {average_distance_checked}")

            activities_with_type = [activity for activity in activities if 'type' in activity]
            update_description(activity_id, athlete_id, activities_with_type, activity_type_checked, average_distance_checked)
        except Exception as e:
            print("Exception Occurred:", e)
            return jsonify({"status": "error", "message": "Exception during update"}), 500

        print("Description updated for activity ID:", activity_id)
        return jsonify({"status": "success"}), 200
    else:
        print("Webhook event does not contain required data")
        return jsonify({"status": "error", "message": "Invalid webhook event data"}), 400


# Run the app
if __name__ == '__main__':
    app.run(port=3000)