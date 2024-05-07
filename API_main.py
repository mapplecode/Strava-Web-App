# A very simple Flask Hello World app for you to get started with...
import requests, csv, configparser
from flask import Flask, request, jsonify, render_template, redirect, session
from datetime import datetime, timedelta


app = Flask(__name__)

app.secret_key = 'Strava'

def save_tokens_to_file(access_token, refresh_token):
    with open('/home/equinoxagents/mysite/tokens.txt', 'w') as file:
        file.write(f"Access Token: {access_token}\n")
        file.write(f"Refresh Token: {refresh_token}\n")
# Replace these values with your Strava application's client_id and client_secret
config = configparser.ConfigParser()
config.read('config.ini')

# Access the values from the config.ini file
client_id = config['Strava']['client_id']
client_secret = config['Strava']['client_secret']

def get_tokens_from_file():
    with open('/home/equinoxagents/mysite/tokens.txt', 'r') as file:
        lines = file.readlines()
        access_token = lines[0].split(':')[1].strip()
        print("000000000000000000000000000000000000000000000",access_token)
    return access_token

@app.route('/')
def home():
    return render_template('signup.html')

@app.route('/login')
def login():
    redirect_uri = request.base_url + '/callback'
  # Define the scope as per your requirements
    authorize_url = f'https://www.strava.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=activity:write,activity:read_all'
    response = requests.post(url = authorize_url)
    print("RESPONSE...........",response.text)
    return redirect(authorize_url)


def get_activities(access_token):
    access_token = get_tokens_from_file()
    print("GET ACTIVITIES...............GET ACTIVITIES", access_token)
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
        if response.status_code == 200:
            activities = response.json()
            if not activities:  # No more activities to fetch
                break
            for activity in activities:
                start_date = datetime.strptime(activity['start_date'], "%Y-%m-%dT%H:%M:%SZ")
                if start_date >= year_start:
                    all_activities.append(activity)
                else:
                    # Since activities are ordered by date, once we encounter an activity
                    # before the start of the current year, we can stop fetching.
                    break
            page += 1
        else:
            print("Failed to fetch activities:", response.text)
            break

    # Writing data to CSV file
    csv_file = "/home/equinoxagents/mysite/activities.csv"
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=all_activities[0].keys())
        writer.writeheader()
        for activity in all_activities:
            writer.writerow(activity)

    print("Data written to", csv_file)

    return all_activities

dicts_here  = dict()

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
            # return "Login Successfull. Access Token: {} Refresh Token: {}".format(access_token, refresh_token)
            return render_template('index.html')
        else:
            return 'Failed to login. Error: ' + response.text
    else:
        return 'Authorization code not received.'

@app.route('/free_features')
def free_feature_page():
    access_token = get_tokens_from_file()
    if access_token:
        activities = get_activities(access_token)
        if activities:
            return render_template('free_feature.html', activities=activities)
        else:
            return 'Failed to fetch activities.'
    else:
        return 'Access token not found. Please log in again.'

#  Function ot extract the  distances from filtered_data() function
def get_distances_by_type(activities):
    distances_by_type = {}
    last_4_weeks_avg_by_type = {}

    for activity in activities:
        activity_type = activity['type']
        distance = activity['distance']
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
def update_description(activity_id):
    access_token = get_tokens_from_file()
    activities = get_activities(access_token)
    # Recalculate distances by type and last 4 weeks averages
    distances_by_type, last_4_weeks_avg_by_type = get_distances_by_type(activities)

    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    # Get activity details
    response = requests.get(url, headers=headers)
    activity_data = response.json()

    # Check if description exists
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

                # Update description
                response = requests.put(url, headers=headers, data=payload)
                print(response.text)
            else:
                print(f"No distance data available for activity type: {activity_type}")
        else:
            print("Activity type not found in the response, skipping update.")
    else:
        print("Description already exists, skipping update.")


@app.route('/webhook', methods=['GET', 'POST'])
def handle_strava_webhook():
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if verify_token == "STRAVA":
            return jsonify({"hub.challenge": challenge}), 200
        else:
            return "Invalid verify token", 403

    elif request.method == 'POST':
        # Handle incoming webhook event
        event_data = request.json  # Assuming the payload is in JSON format
        print(f"Received webhook event: {event_data}")
        if 'owner_id' in event_data and 'object_id' in event_data:
            activity_id = event_data['object_id']
            print("Received activity update for activity ID:", activity_id)
            update_description(activity_id)
            print("Description updated for activity ID:", activity_id)
        else:
            print("Webhook event does not contain required data")

        return jsonify({"status": "success"}), 200



if __name__ == '__main__':
    app.run(port = 3000)
