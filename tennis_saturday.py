import streamlit as st
import random
import pandas as pd
import datetime
import hashlib
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
import base64
import sqlite3
import json

def init_db():
    conn = sqlite3.connect('tennis_saturday.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players
                 (id INTEGER PRIMARY KEY, name TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS schedules
                 (date TEXT PRIMARY KEY, schedule_data TEXT)''')
    conn.commit()
    conn.close()
    
def img_to_base64(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')
    
# Function to get the next upcoming Saturday
def get_next_saturday():
    today = datetime.date.today()
    next_saturday = today + datetime.timedelta((5 - today.weekday()) % 7)
    return next_saturday

# Function to generate schedule
def generate_schedule(players, num_courts):
    NUM_SESSIONS = 4
    matches = {session: [] for session in range(NUM_SESSIONS)}
    played_pairs = set()
    max_attempts = 1000

    for session in range(NUM_SESSIONS):
        attempts = 0
        while attempts < max_attempts:
            random.shuffle(players)
            session_matches = []
            used_players = set()
            valid = True

            for court in range(num_courts):
                court_players = []
                for _ in range(4):
                    for player in players:
                        if player not in used_players:
                            court_players.append(player)
                            used_players.add(player)
                            break
                if len(court_players) < 4:
                    valid = False
                    break
                pair1 = (court_players[0], court_players[1])
                pair2 = (court_players[2], court_players[3])
                if (pair1 not in played_pairs and pair2 not in played_pairs and
                    pair1[::-1] not in played_pairs and pair2[::-1] not in played_pairs):
                    session_matches.append(court_players)
                else:
                    valid = False
                    break
            if valid:
                matches[session] = session_matches
                played_pairs.update([pair1, pair2])
                break
            attempts += 1
        else:
            st.error("Unable to generate a schedule without repeating pairs.")
            return None
    return matches

# Function to display the schedule in a transposed DataFrame
def display_schedule_transposed(schedule, num_courts):
    times = ['4:00-4:30 PM', '4:30-5:00 PM', '5:00-5:30 PM', '5:30-6:00 PM']
    courts = [f'Court {chr(65+i)}' for i in range(num_courts)]  # A, B, C, D
    
    # Initialize a DataFrame with the correct size for the number of courts and sessions
    df = pd.DataFrame(index=courts, columns=times)
    
    for session_key, matchups in schedule.items():
        session = int(session_key)  # Convert session key to integer
        for court in range(len(matchups)):
            matchup = matchups[court]
            team1 = f'{matchup[0]} & {matchup[1]}'
            team2 = f'{matchup[2]} & {matchup[3]}'
            if court < len(courts) and session < len(times):
                df.iloc[court, session] = f'{team1} vs {team2}'
    
    # Transpose the DataFrame
    df_transposed = df.transpose()
    
    # Add a 'Time' column
    df_transposed.insert(0, 'Time', df_transposed.index)
    
    # Reset the index to remove the time as index
    df_transposed = df_transposed.reset_index(drop=True)
    
    return df_transposed

def create_pdf(df):
    buffer = io.BytesIO()
    width, height = landscape(letter)  # Use landscape orientation
    pdf = canvas.Canvas(buffer, pagesize=(width, height))

    # Set up the table style
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    # Convert DataFrame to a list of lists for the table
    data = [df.columns.tolist()] + df.values.tolist()

    # Create the table
    table = Table(data)
    table.setStyle(style)

    # Get table width and height
    table_width, table_height = table.wrapOn(pdf, width, height)

    # Calculate centered position
    x = (width - table_width) / 2
    y = (height - table_height) / 2  # Adjusted to center vertically

    # Draw the table
    table.drawOn(pdf, x, y)

    pdf.save()
    buffer.seek(0)
    return buffer

def clear_schedule():
    clear_schedule_in_db(formatted_date_for_filename)
    clear_players(formatted_date_for_filename)  # Add this line to clear players
    st.session_state['schedule_generated'] = False
    st.session_state['players'] = []  # Reset the players list in session state
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    st.session_state['just_entered_password'] = True

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_attempts" not in st.session_state:
        st.session_state["password_attempts"] = 0

    if st.session_state["password_attempts"] >= 3:
        st.error("Too many incorrect attempts. Please try again later.")
        return False

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hash_password(st.session_state["password"]) == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False
            st.session_state["password_attempts"] += 1

    if "password_correct" not in st.session_state:
        st.text_input(
            "Admin Login", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Admin Login", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

def add_player(name, date):
    conn = sqlite3.connect('tennis_saturday.db')
    c = conn.cursor()
    c.execute("INSERT INTO players (name, date) VALUES (?, ?)", (name, date))
    conn.commit()
    conn.close()

def get_players(date):
    conn = sqlite3.connect('tennis_saturday.db')
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE date = ?", (date,))
    players = [row[0] for row in c.fetchall()]
    conn.close()
    return players

def clear_players(date):
    conn = sqlite3.connect('tennis_saturday.db')
    c = conn.cursor()
    c.execute("DELETE FROM players WHERE date = ?", (date,))
    conn.commit()
    conn.close()

def save_schedule_to_db(schedule, date):
    conn = sqlite3.connect('tennis_saturday.db')
    c = conn.cursor()
    schedule_data = json.dumps(schedule)
    c.execute("REPLACE INTO schedules (date, schedule_data) VALUES (?, ?)", (date, schedule_data))
    conn.commit()
    conn.close()

def load_schedule_from_db(date):
    conn = sqlite3.connect('tennis_saturday.db')
    c = conn.cursor()
    c.execute("SELECT schedule_data FROM schedules WHERE date = ?", (date,))
    result = c.fetchone()
    conn.close()
    if result:
        schedule = json.loads(result[0])
        # Convert keys back to integers
        schedule = {int(k): v for k, v in schedule.items()}
        return schedule
    return None

def clear_schedule_in_db(date):
    conn = sqlite3.connect('tennis_saturday.db')
    c = conn.cursor()
    c.execute("DELETE FROM schedules WHERE date = ?", (date,))
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Get the date of the next upcoming Saturday
next_saturday = get_next_saturday()
formatted_date = next_saturday.strftime("%A, %B %d, %Y")
formatted_date_for_filename = next_saturday.strftime("%Y-%m-%d")

# Initialize global variables in session_state
if 'players' not in st.session_state:
    st.session_state['players'] = []

# Load players from the database
players = get_players(formatted_date_for_filename)
st.session_state['players'] = players

# Load schedule from the database
schedule = load_schedule_from_db(formatted_date_for_filename)
if schedule:
    st.session_state['schedule_generated'] = True
    st.session_state['schedule'] = schedule
else:
    st.session_state['schedule_generated'] = False

# Define MAX_PLAYERS
MAX_PLAYERS = 16

# Add this near the top of your script, before any other Streamlit commands
st.set_page_config(
    page_title="Saturday Tennis",
    page_icon="images/tltc-logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Streamlit app UI
st.title('🎾 TLTC Saturday Tennis')

# Sidebar
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; justify-content: center;">
            <img src="data:image/png;base64,{}" width="200">
        </div>
        """.format(img_to_base64("images/tltc-logo.png")),
        unsafe_allow_html=True
    )
    st.header("About TLTC")
    st.write("""The Toronto Lawn Tennis Club has spent 150 years perfecting the art of tennis excellence, but on Saturdays from 4 to 6 PM, we take over to remind everyone that perfection is overrated. Our mixed crew of weekend warriors may not have the smoothest backhands or the most graceful serves, but what we lack in finesse, we make up for in friendly trash talk and questionable form. It's less about scoring aces and more about acing the art of having a laugh—plus, where else can you call "love" and mean it sarcastically?""")
    st.write("""Contact: TLTC.Mixed.Saturday@gmail.com""")

# Main content
st.write("""
### Instructions:
- Max of 16 players (4 courts)
- Extra players added to subs list
- Sign-up by Thursday night
- Schedule will be posted on Friday
- Games are Saturday from 4:00pm to 6:00pm      
""")

# Step 1: Enter player names one by one
if len(players) < MAX_PLAYERS:
    with st.form(key="player_signup"):
        #new_player = st.text_input(f"Sign-up for {formatted_date}:", key='new_player')
        # Add this CSS to make the input more prominent
        st.markdown("""
        <style>
        .big-font {
            font-size:22px !important;
            font-weight: bold;
        }
        .stTextInput > div > div > input {
            font-size: 20px;
            padding: 10px;
            border: 2px solid #4CAF50;
            border-radius: 5px;
        }
        </style>
        """, unsafe_allow_html=True)

        # Use the custom CSS class for the label
        st.markdown(f'<p class="big-font">Sign-up for {formatted_date}:</p>', unsafe_allow_html=True)

        # The text input will now use the custom styling
        new_player = st.text_input("", key='new_player', label_visibility="collapsed")

        submit = st.form_submit_button("✋  I'm in!")

        if submit:
            if new_player and new_player not in players:
                add_player(new_player, formatted_date_for_filename)
                players = get_players(formatted_date_for_filename)  # Refresh the player list
                st.session_state['players'] = players  # Update session state
                st.rerun()
            elif submit and not new_player:
                st.error("Please enter a valid, unique name.")
            elif submit and new_player in players:
                st.error("Player is already signed up!")
                st.rerun()

# Display the list of players so far
st.write(f"Current players ({len(players)}/{MAX_PLAYERS}): {', '.join(players)}")

# Step 2: Generate and display schedule when enough players have signed up
if len(players) >= 8:
    if len(players) % 4 != 0:
        subs = players[len(players) // 4 * 4:]  # Extra players are substitutes
        players_for_schedule = players[:len(players) // 4 * 4]
    else:
        subs = []
        players_for_schedule = players

    num_courts = len(players_for_schedule) // 4

    # Check if schedule exists
    if st.session_state['schedule_generated']:
        # Schedule exists, display it
        schedule = st.session_state['schedule']
        df_transposed = display_schedule_transposed(schedule, num_courts)
        st.dataframe(df_transposed, hide_index=True)
        
        if subs:
            st.write(f"Substitutes: {', '.join(subs)}")
        
        # Create PDF and add download button
        pdf_buffer = create_pdf(df_transposed)
        st.download_button(
            label="⬇️  Download as PDF",
            data=pdf_buffer,
            file_name=f"tennis_schedule_{formatted_date_for_filename}.pdf",
            mime="application/pdf"
        )
    #else:
    #    st.write("No schedule has been generated yet.")

    # Provide options to generate or clear the schedule, protected by password
    if check_password():
        #st.write("You are authenticated. You can now generate or clear the schedule.")
        if st.button("🔄  Generate Schedule"):
            schedule = generate_schedule(players_for_schedule, num_courts)
            if schedule:
                save_schedule_to_db(schedule, formatted_date_for_filename)
                st.session_state['schedule_generated'] = True
                st.session_state['schedule'] = schedule
                st.success("Schedule generated successfully.")
                st.rerun()
            else:
                st.error("Failed to generate a valid schedule.")
        
        if st.button("❌  Clear Schedule"):
            clear_schedule()
            st.success("🗑️Schedule cleared.")
            st.rerun()
else:
    st.write("Waiting for players to sign-up...")
