import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import mysql.connector
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
import json
from os import getenv
from mysql.connector import pooling
from pathlib import Path

load_dotenv()

if os.path.exists(".env"):
    load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


required = {
    "SECRET_KEY": SECRET_KEY,
    "DB_HOST": DB_HOST,
    "DB_USER": DB_USER,
    "DB_PASS": DB_PASS,
    "DB_NAME": DB_NAME
}



missing = [k for k,v in (("SECRET_KEY",SECRET_KEY),("DB_HOST",DB_HOST),("DB_USER",DB_USER),("DB_PASS",DB_PASS),("DB_NAME",DB_NAME)) if not v]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)

# DB helpers
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "homimeet_db")
    )

def fetchall_dict(query, params=()):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetchone_dict(query, params=()):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def execute(query, params=()):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()
    conn.close()

# Flask-Login user
class User(UserMixin):
    def __init__(self, id, username):
        self.id = str(id)
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    row = fetchone_dict("SELECT * FROM users WHERE id = %s", (user_id,))
    if row:
        return User(row['id'], row['username'])
    return None

# Simple auth routes (login/signup)
@app.route("/")
def home():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT NOW()")
        current_time = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return f"✅ Database connected! Server time: {current_time}"
    except Exception as e:
        return f"❌ DB Connection failed: {e}"

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        flash('Account created!')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = fetchone_dict("SELECT * FROM users WHERE username = %s", (username,))
        if user and bcrypt.check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username']))
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    row = fetchone_dict("SELECT AVG(score) AS avg_score FROM punctuality_logs WHERE user_id = %s", (current_user.id,))
    avg_score = row['avg_score'] if row and row['avg_score'] is not None else 0
    return render_template('dashboard.html', username=current_user.username, avg_score=round(avg_score, 2))

# Create group (simple)
@app.route('/create_group', methods=['GET','POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group_name = request.form['group_name']
        execute("INSERT INTO user_groups (name, created_by) VALUES (%s, %s)", (group_name, current_user.id))
        flash("Group created successfully!")
        return redirect(url_for('dashboard'))
    return "<form method='post'><input name='group_name' placeholder='Group Name'><input type='submit'></form>"

# Legacy schedule meetup (used in some flows)
@app.route("/schedule_meetup", methods=["POST"])
@login_required
def schedule_meetup():
    location = request.form.get('location') or request.form.get('title')
    scheduled_time = request.form.get('scheduled_time')
    lat = request.form.get('lat')
    lng = request.form.get('lng')

    if not lat or not lng:
        flash("Location not set on the map. Please click the map.")
        return redirect(url_for('my_meetups'))

    try:
        lat = float(lat); lng = float(lng)
    except:
        flash("Invalid coordinates.")
        return redirect(url_for('my_meetups'))

    execute("""
        INSERT INTO meetups (user_id, location, scheduled_time, lat, lng, status, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (current_user.id, location, scheduled_time, lat, lng, 'scheduled', current_user.id))

    flash("Meetup successfully scheduled!")
    return redirect(url_for('my_meetups'))

# Punctuality
@app.route('/submit_punctuality', methods=['GET','POST'])
@login_required
def submit_punctuality():
    if request.method == 'POST':
        user_id = request.form['user_id']
        meetup_id = request.form['meetup_id']
        status = request.form['status']
        score_map = {'on_time':3,'late':-1,'absent':-3}
        score = score_map.get(status,0)
        execute("INSERT INTO punctuality_logs (user_id, meetup_id, status, score) VALUES (%s,%s,%s,%s)",
                (user_id, meetup_id, status, score))
        flash('Punctuality recorded.')
        return redirect(url_for('dashboard'))
    return "<form method='post'>User ID: <input name='user_id'><br>Meetup ID: <input name='meetup_id'><br>Status: <select name='status'><option value='on_time'>On Time</option><option value='late'>Late</option><option value='absent'>Absent</option></select><br><input type='submit'></form>"

# Leaderboard
@app.route('/leaderboard/<int:group_id>')
@login_required
def leaderboard(group_id):
    order = request.args.get('order','desc')
    order_by = 'DESC' if order=='desc' else 'ASC'
    rows = fetchall_dict(f"""
        SELECT u.username, SUM(p.score) AS total_score
        FROM punctuality_logs p
        JOIN users u ON u.id = p.user_id
        JOIN meetups m ON m.id = p.meetup_id
        WHERE m.group_id = %s
        GROUP BY p.user_id
        ORDER BY total_score {order_by}
    """, (group_id,))
    return render_template('leaderboard.html', scores=rows, group_id=group_id, order=order)

# Profile
@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    if request.method == 'POST':
        bio = request.form['bio']
        execute("REPLACE INTO user_profiles (user_id, bio) VALUES (%s,%s)", (current_user.id, bio))
        flash("Profile updated.")
    row = fetchone_dict("SELECT bio FROM user_profiles WHERE user_id = %s", (current_user.id,))
    bio = row['bio'] if row else ""
    return render_template('profile.html', bio=bio)

# Cancel (mark canceled) kept for compatibility
@app.route('/cancel_meetup/<int:meetup_id>', methods=['GET'])
@login_required
def cancel_meetup(meetup_id):
    # Only owner can cancel
    row = fetchone_dict("SELECT user_id FROM meetups WHERE id = %s", (meetup_id,))
    if not row or str(row.get('user_id')) != str(current_user.id):
        flash("Not authorized to cancel this meetup.", "danger")
        return redirect(url_for('my_meetups'))
    execute("UPDATE meetups SET status = 'canceled' WHERE id = %s", (meetup_id,))
    flash("Meetup canceled.")
    return redirect(url_for('my_meetups'))

# New: delete meetup permanently (owner only)
@app.route('/delete_meetup', methods=['POST'])
@login_required
def delete_meetup():
    meetup_id = request.form.get('meetup_id')
    if not meetup_id:
        flash("Missing meetup id", "danger")
        return redirect(url_for('my_meetups'))
    row = fetchone_dict("SELECT user_id FROM meetups WHERE id = %s", (meetup_id,))
    if not row or str(row.get('user_id')) != str(current_user.id):
        flash("Not authorized to delete this meetup.", "danger")
        return redirect(url_for('my_meetups'))
    # delete related rows
    execute("DELETE FROM punctuality_logs WHERE meetup_id = %s", (meetup_id,))
    execute("DELETE FROM invitations WHERE meetup_id = %s", (meetup_id,))
    execute("DELETE FROM meetups WHERE id = %s", (meetup_id,))
    flash("Meetup deleted.")
    return redirect(url_for('my_meetups'))

# New: host can kick a user from meetup (owner only)
@app.route('/kick_user', methods=['POST'])
@login_required
def kick_user():
    meetup_id = request.form.get('meetup_id')
    user_id = request.form.get('user_id')
    if not meetup_id or not user_id:
        flash("Missing parameters", "danger")
        return redirect(url_for('my_meetups'))
    row = fetchone_dict("SELECT user_id FROM meetups WHERE id = %s", (meetup_id,))
    if not row or str(row.get('user_id')) != str(current_user.id):
        flash("Not authorized to kick users.", "danger")
        return redirect(url_for('my_meetups'))
    execute("DELETE FROM invitations WHERE meetup_id = %s AND user_id = %s", (meetup_id, user_id))
    flash("User removed from meetup.")
    return redirect(url_for('my_meetups'))

# Invite & create invitation endpoints
@app.route('/invite', methods=['POST'])
@login_required
def invite():
    user_id = request.form.get('user_id')
    meetup_id = request.form.get('meetup_id')
    meetup = fetchone_dict("SELECT id FROM meetups WHERE id = %s AND user_id = %s", (meetup_id, current_user.id))
    if not meetup:
        flash("Invalid meetup ID or you do not own this meetup.")
        return redirect(url_for('my_meetups'))
    execute("INSERT INTO invitations (user_id, meetup_id, status) VALUES (%s,%s,%s)", (user_id, meetup_id, 'pending'))
    flash("User invited.")
    return redirect(url_for('my_meetups'))

@app.route('/create_invitation', methods=['POST'])
@login_required
def create_invitation():
    meetup_id = request.form.get('meetup_id')
    invitee_ids = request.form.getlist('invitees[]')
    if not invitee_ids:
        raw = request.form.get('user_ids','')
        if raw:
            try:
                invitee_ids = json.loads(raw)
            except:
                invitee_ids = []
    if not meetup_id:
        location = request.form.get('location') or request.form.get('title') or 'Untitled Meetup'
        scheduled_time = request.form.get('scheduled_time') or None
        lat = request.form.get('lat') or None
        lng = request.form.get('lng') or None
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO meetups (user_id, location, scheduled_time, lat, lng, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (current_user.id, location, scheduled_time, lat if lat else None, lng if lng else None, 'scheduled', current_user.id))
        conn.commit()
        meetup_id = cur.lastrowid
        cur.close()
        conn.close()
    if not invitee_ids:
        flash("Please select at least one user to invite.", "danger")
        return redirect(url_for('invitations'))
    for invitee_id in invitee_ids:
        existing = fetchone_dict("SELECT id FROM invitations WHERE user_id = %s AND meetup_id = %s", (invitee_id, meetup_id))
        if not existing:
            execute("INSERT INTO invitations (user_id, meetup_id, status) VALUES (%s, %s, %s)", (invitee_id, meetup_id, 'pending'))
    flash("Invitations sent successfully!", "success")
    return redirect(url_for('invitations'))

@app.route('/respond_invite', methods=['POST'])
@login_required
def respond_invite():
    invite_id = request.form.get('invite_id')
    action = request.form.get('action')
    if action == 'accept':
        status = 'accepted'
    elif action == 'decline':
        status = 'declined'
    else:
        flash("Unknown action.", "danger")
        return redirect(url_for('invitations'))
    execute("UPDATE invitations SET status = %s WHERE id = %s AND user_id = %s", (status, invite_id, current_user.id))
    return ('', 204) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect(url_for('invitations'))

# New endpoint: update user location (server-persisted to user_locations table)
@app.route('/update_location', methods=['POST'])
@login_required
def update_location():
    data = request.get_json() or {}
    lat = data.get('lat')
    lng = data.get('lng')
    accuracy = data.get('accuracy')
    if lat is None or lng is None:
        return jsonify({'error':'missing coordinates'}), 400
    # upsert into user_locations table
    conn = get_db_connection()
    cur = conn.cursor()
    # Try update first
    cur.execute("SELECT id FROM user_locations WHERE user_id = %s", (current_user.id,))
    exists = cur.fetchone()
    if exists:
        cur.execute("UPDATE user_locations SET lat=%s, lng=%s, accuracy=%s, last_seen=NOW() WHERE user_id=%s", (lat, lng, accuracy, current_user.id))
    else:
        cur.execute("INSERT INTO user_locations (user_id, lat, lng, accuracy, last_seen) VALUES (%s, %s, %s, %s, NOW())", (current_user.id, lat, lng, accuracy))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok':True}), 200

# GET /invitations
@app.route('/invitations')
@login_required
def invitations():
    invites = fetchall_dict("""
        SELECT i.id AS invite_id, m.id AS meetup_id, m.location, m.scheduled_time, m.lat AS latitude, m.lng AS longitude
        FROM invitations i
        JOIN meetups m ON i.meetup_id = m.id
        WHERE i.user_id = %s AND i.status = 'pending'
    """, (current_user.id,))
    meetups = fetchall_dict("SELECT id, location, scheduled_time, lat, lng, user_id FROM meetups WHERE user_id = %s ORDER BY scheduled_time DESC", (current_user.id,))
    all_users = fetchall_dict("SELECT id, username FROM users WHERE id != %s", (current_user.id,))
    return render_template('invitations.html', invitations=invites, meetups=meetups, all_users=all_users)

# My meetups
@app.route('/my_meetups')
@login_required
def my_meetups():
    filter_status = request.args.get('status','all')
    after = request.args.get('after')
    before = request.args.get('before')

    params = [current_user.id]
    cond = ["m.user_id = %s"]

    if filter_status != 'all':
        cond.append("m.status = %s"); params.append(filter_status)
    if after:
        cond.append("m.scheduled_time >= %s"); params.append(after)
    if before:
        cond.append("m.scheduled_time <= %s"); params.append(before)

    where = " AND ".join(cond)
    created = fetchall_dict(f"SELECT m.* FROM meetups m WHERE {where} ORDER BY m.scheduled_time DESC", tuple(params))

    inv_params = [current_user.id]
    inv_cond = ["i.user_id = %s", "i.status = 'accepted'"]
    if filter_status != 'all':
        inv_cond.append("m.status = %s"); inv_params.append(filter_status)
    if after:
        inv_cond.append("m.scheduled_time >= %s"); inv_params.append(after)
    if before:
        inv_cond.append("m.scheduled_time <= %s"); inv_params.append(before)
    inv_where = " AND ".join(inv_cond)
    invited = fetchall_dict(f"""
        SELECT DISTINCT m.* FROM meetups m
        JOIN invitations i ON m.id = i.meetup_id
        WHERE {inv_where}
        ORDER BY m.scheduled_time DESC
    """, tuple(inv_params))

    seen = {}
    all_meetups = []
    def add_meetup_row(row):
        mid = row['id']
        if mid in seen:
            return
        seen[mid] = True

        # fetch members for this meetup
        members = fetchall_dict("""
            SELECT u.id, u.username AS name, i.status
            FROM invitations i
            JOIN users u ON i.user_id = u.id
            WHERE i.meetup_id = %s
        """, (mid,))

        # determine creator username
        creator_name = None
        creator_id = row.get('user_id') or row.get('created_by') or row.get('created_by_id')
        if creator_id:
            creator_row = fetchone_dict("SELECT username FROM users WHERE id = %s", (creator_id,))
            if creator_row:
                creator_name = creator_row.get('username')

        # if creator not present in members list, prepend them as host (so everyone sees host)
        already_in_members = any(str(m.get('id')) == str(creator_id) for m in members) if creator_id else False
        if creator_name and not already_in_members:
            members.insert(0, {'id': creator_id, 'name': creator_name, 'status': 'host'})

        scheduled = row.get('scheduled_time')
        all_meetups.append({
            'id': mid,
            'location': row.get('location'),
            'scheduled_time': scheduled,
            'description': row.get('description') if 'description' in row else None,
            'members': members,
            'is_owner': (str(row.get('user_id')) == str(current_user.id)) if row.get('user_id') is not None else False,
            'creator': creator_name,
            'lat': row.get('lat') if 'lat' in row else row.get('latitude') if 'latitude' in row else None,
            'lng': row.get('lng') if 'lng' in row else row.get('longitude') if 'longitude' in row else None
        })

    for r in created:
        add_meetup_row(r)
    for r in invited:
        add_meetup_row(r)

    now = datetime.now()
    today = now.date().isoformat()
    week_start = (now - timedelta(days=now.weekday())).date().isoformat()
    week_end = (now + timedelta(days=(6 - now.weekday()))).date().isoformat()

    return render_template('my_meetups.html',
                           meetups=all_meetups,
                           current_filter=filter_status,
                           after=after,
                           before=before,
                           users=fetchall_dict("SELECT id, username FROM users WHERE id != %s", (current_user.id,)),
                           today=today,
                           now=now.date().isoformat(),
                           week_start=week_start,
                           week_end=week_end)

@app.route('/discover')
@login_required
def discover():
    return render_template('discover.html')

@app.route('/my_scores')
@login_required
def my_scores():
    logs = fetchall_dict("""
        SELECT m.location, m.scheduled_time, p.status, p.score
        FROM punctuality_logs p
        JOIN meetups m ON m.id = p.meetup_id
        WHERE p.user_id = %s
        ORDER BY m.scheduled_time DESC
    """, (current_user.id,))
    return render_template('my_scores.html', logs=logs)

@app.context_processor
def inject_google_key():
    return dict(GOOGLE_API_KEY=GOOGLE_API_KEY)

@app.route('/meetup/<int:meetup_id>')
@login_required
def meetup_detail(meetup_id):
    meetup = fetchone_dict("""
        SELECT m.*, u.username AS creator
        FROM meetups m
        JOIN users u ON m.user_id = u.id
        WHERE m.id = %s
    """, (meetup_id,))
    if not meetup:
        flash("Meetup not found.")
        return redirect(url_for('my_meetups'))
    invited_users = fetchall_dict("""
        SELECT i.*, u.username
        FROM invitations i
        JOIN users u ON i.user_id = u.id
        WHERE i.meetup_id = %s
    """, (meetup_id,))
    return render_template('meetup_detail.html', meetup=meetup, invited_users=invited_users)

if __name__ == '__main__':
    app.run(debug=True)
