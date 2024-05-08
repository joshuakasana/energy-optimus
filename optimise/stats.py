from datetime import datetime, timedelta
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)
from werkzeug.exceptions import abort
from sqlalchemy import func

from optimise.auth import login_required
from optimise.db import get_db
from optimise.forms import RegistrationForm, LoginForm, changeExpenseBudget, PreferenceForm

bp = Blueprint('stats', __name__)

bp.route('/data', methods=['POST'])
def receive_data():
    print('Initiated')
    if not request.json:
        abort(400, 'Request body must be in JSON format')

    data = request.json
    required_fields = ['device_id', 'date', 'temperature', 'humidity', 'light', 'motion', 'current', 'energy', 'energy_prediction']
    for field in required_fields:
        if field not in data:
            abort(400, f'Missing required field: {field}')

    # Process and store the received data
            
    device_id = data.get('device_id')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM User WHERE device_id = ?", (device_id,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        user_id = user.id
    else:
        abort(403, 'Unauthorized device')  # Or handle unauthorized device appropriately

    light_detected = bool(data.get('light_value'))
    motion_detected = bool(data.get('motion_value'))

    try:
        converted_datetime = datetime.fromisoformat(data['date'])
    except ValueError:
        abort(400, "Datetime error")


    save_data_to_database(data, user_id, light_detected, motion_detected, converted_datetime)
    return jsonify({'message': 'Data received and stored successfully'}), 200

def save_data_to_database(data, user_id, light, motion, converted_datetime):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""INSERT INTO Stats (user_id, device_id, date, temperature, humidity,
                                        light, motion, current, energy, energy_prediction)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (user_id, data['device_id'], converted_datetime,
                    data['temperature'], data['humidity'], light, motion,
                    data['current'], data['energy'], data['energy_prediction']))
    db.commit()
    cursor.close()


@bp.route('/')
def index():
    return render_template('stats/index.html', title='Satient')

@bp.route('/home', methods=('GET', 'POST'))
@login_required
def home():
    db = get_db()
    user = db.execute("SELECT first_name, budget FROM User WHERE id = ?", (g.user['id'],)).fetchone()
    budget = user['budget']

    hourly_consumptions = average_energy_per_hour_all()
    cumulative_hourly_expenses = cumulative_hourly_costs(hourly_consumptions, cost_per_watt_hour)
    latest_hour, latest_cost = cumulative_hourly_expenses[-1]
   
    month_predict = 13000
    currentMonth_expense = round(latest_cost, 2)
    savings = round((budget - currentMonth_expense), 2)

    expense_form = changeExpenseBudget()
    pform = PreferenceForm()
    

    if expense_form.validate_on_submit():
        cursor = db.cursor()
        cursor.execute("UPDATE User SET budget = ? WHERE id = ?", (expense_form.expense_budget.data, g.user['id'],))
        db.commit()
        cursor.close()
        flash(f'Expense Budget updated successfully!', 'success')
        return redirect(url_for('stats.home'))
    
    if pform.validate_on_submit():
        flash(f'Preferences set successfully!', 'success')
        return redirect(url_for('stats.home'))


    return render_template('stats/home.html', title='Action Center', expense_form=expense_form, pform=pform,
                            first_name=user['first_name'], budget=user['budget'], month_predict=month_predict,
                            currentMonth_expense=currentMonth_expense, savings=savings)

def average_energy_per_hour(target_date):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT STRFTIME('%Y-%m-%d %H:00:00', date) AS hour_truncated,
               AVG(energy) AS average_energy
        FROM Stats
        WHERE DATE(date) = ?
        GROUP BY STRFTIME('%Y-%m-%d %H:00:00', date)
    """, (target_date,))
    average_eph = cursor.fetchall()
    cursor.close()
    return average_eph

def average_energy_per_hour_all():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT STRFTIME('%Y-%m-%d %H:00:00', date) AS hour_truncated,
               AVG(energy) AS average_energy
        FROM Stats
        GROUP BY STRFTIME('%Y-%m-%d %H:00:00', date)
    """)
    hourly_consumptions = cursor.fetchall()
    cursor.close()

    if not hourly_consumptions:
        # Handle the case where hourly_consumptions is empty
        # For example, you can return a default value or raise an exception
        return [('2024-04-19 19:00:00',3.5276382178591)]
    return hourly_consumptions

def cumulative_hourly_costs(hourly_consumptions, cost_per_watt_hour):
    cumulative_costs = []
    cumulative_energy = 0

    for hour, value in hourly_consumptions:
        cumulative_energy += value
        cumulative_cost = cumulative_energy * cost_per_watt_hour
        cumulative_costs.append((hour, cumulative_cost))

    return cumulative_costs



@bp.route('/get_current_data', methods=['GET'])
@login_required
def get_current_data():
    # Query the database for the latest temperature and humidity data
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT temperature, humidity
        FROM Stats
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT 1
    """, (g.user['id'],))
    stat = cursor.fetchone()

    if stat:
        temperature, humidity = stat
    else:
        # If no data is available, set default values
        temperature = 25
        humidity = 75

    cursor.close()

    # Return the current time, temperature, and humidity as JSON
    return jsonify({
        'temperature': temperature,
        'humidity': humidity
    })


@bp.route('/get_energy_consumption', methods=['GET'])
@login_required
def get_energy_consumption():
    # Get the current datetime
    current_datetime = datetime.now()

    # Calculate the datetime for yesterday and today
    yesterday_datetime = current_datetime - timedelta(days=1)

    # Extract date part from datetime objects
    current_date = current_datetime.date()
    yesterday_date = yesterday_datetime.date()

    # Calculate the start and end of yesterday
    yesterday_start = datetime.combine(yesterday_date, datetime.min.time())
    yesterday_end = datetime.combine(yesterday_date, datetime.max.time())

    # Calculate the start of today
    today_start = datetime.combine(current_date, datetime.min.time())
    today_end = datetime.combine(current_date, datetime.max.time())

    db = get_db()
    cursor = db.cursor()

    # Query for energy consumption yesterday
    cursor.execute("""
        SELECT SUM(energy) AS total_energy_yesterday, COUNT(*) AS num_records_yesterday
        FROM Stats
        WHERE user_id = ? AND date BETWEEN ? AND ?
    """, (g.user['id'], yesterday_start, yesterday_end))
    energy_yesterday = cursor.fetchone()
    total_energy_yesterday = energy_yesterday['total_energy_yesterday'] if energy_yesterday else 0
    num_records_yesterday = energy_yesterday['num_records_yesterday'] if energy_yesterday else 0

    # Query for energy consumption today
    cursor.execute("""
        SELECT SUM(energy) AS total_energy_today, COUNT(*) AS num_records_today
        FROM Stats
        WHERE user_id = ? AND date BETWEEN ? AND ?
    """, (g.user['id'], today_start, today_end))
    energy_today = cursor.fetchone()
    total_energy_today = energy_today['total_energy_today'] if energy_today else 0
    num_records_today = energy_today['num_records_today'] if energy_today else 0

    cursor.close()

    # Calculate the average energy consumption for yesterday and today
    average_energy_yesterday = round(total_energy_yesterday / num_records_yesterday, 2) if num_records_yesterday > 0 else 0
    average_energy_today = round(total_energy_today / num_records_today, 2) if num_records_today > 0 else 0

    return jsonify({
        'average_energy_yesterday': average_energy_yesterday,
        'average_energy_today': average_energy_today
    })

# Assuming the cost per Watt-hour is UGX 250
cost_per_watt_hour = 250

@bp.route('/track_energy_cost', methods=['GET'])
@login_required
def track_energy_cost():
    db = get_db()
    user = db.execute("SELECT first_name, budget FROM User WHERE id = ?", (g.user['id'],)).fetchone()

    hourly_consumptions = average_energy_per_hour_all()
    cumulative_hourly_expenses = cumulative_hourly_costs(hourly_consumptions, cost_per_watt_hour)

    target_expense = user['budget'] # Set value by user from User model

    data = {
        'target_expense': target_expense,
        'cumulative_hourly_costs': cumulative_hourly_expenses
    }
    return jsonify(data)



@bp.route('/get_energy_data', methods=['GET'])
@login_required
def get_energy_data():
    db = get_db()
    cursor = db.cursor()

    # Query the Stats table for energy and predicted energy data
    cursor.execute("""
        SELECT date, energy, energy_prediction
        FROM Stats
        WHERE user_id = ?
        ORDER BY date
    """, (g.user['id'],))
    stats = cursor.fetchall()

    # Extract timestamps and energy values
    timestamps = [stat['date'].strftime("%a %H:%M:%S") for stat in stats]
    energy_values = [stat['energy'] for stat in stats]
    predicted_energy_values = [stat['energy_prediction'] for stat in stats]

    cursor.close()

    # Prepare data to send back to the client
    data = {
        'timestamps': timestamps,
        'energy_values': energy_values,
        'predicted_energy_values': predicted_energy_values
    }

    return jsonify(data)
