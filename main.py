import streamlit as st
import random
import pandas as pd
import datetime
import hashlib
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

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
    
    for session in range(NUM_SESSIONS):
        session_matches = []
        attempts = 0
        while len(session_matches) < num_courts:
            random.shuffle(players)
            court_players = players[:4 * num_courts]
            
            # Create court matchups
            for i in range(0, len(court_players), 4):
                court = court_players[i:i + 4]
                pair1 = (court[0], court[1])
                pair2 = (court[2], court[3])
                
                # Check if these pairs haven't played yet
                if (pair1 not in played_pairs and pair2 not in played_pairs and
                    (pair1[::-1] not in played_pairs) and (pair2[::-1] not in played_pairs)):
                    session_matches.append(court)
                    played_pairs.update([pair1, pair2])
            
            attempts += 1
            if attempts > 100:
                break
        
        matches[session] = session_matches
    
    return matches

# Function to display the schedule in markdown for proper formatting
def display_schedule_markdown(schedule, num_courts):
    times = ['4 PM', '4:30 PM', '5 PM', '5:30 PM']
    
    for session, matchups in schedule.items():
        st.write(f"### Session {times[session]}")  # Header for each session
        for court in range(len(matchups)):
            matchup = matchups[court]
            team1 = f'{matchup[0]} & {matchup[1]}'
            team2 = f'{matchup[2]} & {matchup[3]}'
            st.markdown(f"**Court {chr(65+court)}**: \n {team1} vs {team2}")

def display_schedule_transposed(schedule, num_courts):
    times = ['4:00-4:30 PM', '4:30-5:00 PM', '5:00-5:30 PM', '5:30-6:00 PM']
    courts = [f'Court {chr(65+i)}' for i in range(num_courts)]  # A, B, C, D
    
    # Initialize a DataFrame with the correct size for the number of courts and sessions
    df = pd.DataFrame(index=courts, columns=times)
    
    for session, matchups in schedule.items():
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
    
    # Display the transposed DataFrame
    st.dataframe(df_transposed)
    
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
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
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
    y = (height + table_height) / 2

    # Draw the table
    table.drawOn(pdf, x, y)

    pdf.save()
    buffer.seek(0)
    return buffer

# Callback function to clear the schedule and reset states
def clear_schedule():
    st.session_state['players'] = []
    st.session_state['schedule_generated'] = False
    st.session_state['clear_input'] = True  # Set the flag to clear input
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]  # Forget the password
    # Note: Not calling st.experimental_rerun() here

# Function to hash a password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to check if the entered password is correct
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hash_password(st.session_state["password"]) == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # First run, show input for password.
    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    
    # Password incorrect, show input + error.
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    
    # Password correct.
    else:
        return True

# Initialize global variables in session_state
if 'players' not in st.session_state:
    st.session_state['players'] = []
players = st.session_state['players']

if 'schedule_generated' not in st.session_state:
    st.session_state['schedule_generated'] = False

if 'new_player' not in st.session_state:
    st.session_state['new_player'] = ''

if 'clear_input' not in st.session_state:
    st.session_state['clear_input'] = False

# Check if input needs to be cleared
if st.session_state['clear_input']:
    st.session_state['new_player'] = ''
    st.session_state['clear_input'] = False

# Get the date of the next upcoming Saturday
next_saturday = get_next_saturday()

# Format the date as "YYYY-MM-DD" for the file name
formatted_date = next_saturday.strftime("%B %d, %Y")
formatted_date_for_filename = next_saturday.strftime("%Y-%m-%d")

# Define MAX_PLAYERS
MAX_PLAYERS = 16

# Streamlit app UI
st.title('TLTC Saturday Tennis Sign-up')

st.write("""
### Instructions:
- Max of 16 players (4 courts)
- Extra players added to subs list
- Sign-up by Thursday at midnight
- Schedule will be posted on Friday
- Games are Saturday from 4:00pm to 6:00pm      
- Questions? Contact SaturdayTennis@gmail.com
""")

# Step 1: Enter player names one by one
if len(players) < MAX_PLAYERS:
    with st.form(key="player_signup"):
        # Update text input to include the next Saturday's date
        new_player = st.text_input(f"Sign-up for {formatted_date}:", key='new_player')
        
        # Automatically press the button upon Enter
        submit = st.form_submit_button("I'm in!")
        
        if submit:
            if new_player and new_player not in players:
                players.append(new_player)
                st.session_state['players'] = players
            elif submit and not new_player:
                st.error("Please enter a valid, unique name.")
            elif submit and new_player in players:
                st.error("Player is already signed up!")

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
    
    if check_password():
        if not st.session_state.get('schedule_generated', False):
            # Automatically generate schedule when password is correct
            schedule = generate_schedule(players_for_schedule, num_courts)
            df_transposed = display_schedule_transposed(schedule, num_courts)
            
            if subs:
                st.write(f"Substitutes: {', '.join(subs)}")
            
            # Create PDF and add download button
            pdf_buffer = create_pdf(df_transposed)
            st.download_button(
                label="Download as PDF",
                data=pdf_buffer,
                file_name=f"tennis_schedule_{formatted_date_for_filename}.pdf",
                mime="application/pdf"
            )
            
            # Set the schedule_generated flag to True
            st.session_state['schedule_generated'] = True
        
        # Always show the Generate Schedule button
        if st.button("Generate Schedule"):
            schedule = generate_schedule(players_for_schedule, num_courts)
            df_transposed = display_schedule_transposed(schedule, num_courts)
            
            if subs:
                st.write(f"Substitutes: {', '.join(subs)}")
            
            # Create PDF and add download button
            pdf_buffer = create_pdf(df_transposed)
            st.download_button(
                label="Download as PDF",
                data=pdf_buffer,
                file_name=f"tennis_schedule_{formatted_date_for_filename}.pdf",
                mime="application/pdf"
            )
        
        # Display the Clear Schedule button
        if st.button("Clear Schedule"):
            clear_schedule()
            st.rerun()

else:
    st.write("Waiting for players to sign-up...")