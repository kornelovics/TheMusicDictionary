from flask import Flask, render_template, url_for, redirect, request, session
from flask_session import Session
from flask_bcrypt import Bcrypt
import sqlite3
import subprocess
import json
import os

import TMDEngine.run as run_engine  # the py module for music recognition
import config


app = Flask(__name__)
bcrypt = Bcrypt(app)  # an encryption lib to encrypt the passwords
app.secret_key = config.SECRET_KEY  # setting the secret key for the session
app.config.update(
    PERMANENT_SESSION_LIFETIME=config.PERMANENT_SESSION_LIFETIME,
    SESSION_PERMANENT=False,
    SESSSION_COOKIE_NAME="tmduser",
    SESSION_TYPE="filesystem"
)

Session(app)  # creating the flask session

"""
Database Tables:

users: CREATE TABLE users (id integer primary key autoincrement,  username varchar(30) not null, mail varchar(30) not null, password varchar(60) not null);
"""


@app.route('/')
def hello():
    # passing the session data to change the display for a signed in user
    return render_template("landingPage.html", data=session)

# the sign in page


@app.route("/signin")
def signIn():

    # if an already signed in user tries to sign in again
    if session != {}:
        return redirect(url_for('profilePage'))

    return render_template("signIn.html")


# the sign up page
@app.route("/signup")
def signUp():

    # if an already signed in user tries to sign up
    if session != {}:
        return redirect(url_for('profilePage'))

    return render_template("signUp.html")


# Add Credentials to Database and redirect to profile page
@app.route("/signUpValidation", methods=["POST"])
def signUpValidation():

    # getting the form values
    username = request.form.get('name')
    mail = request.form.get('mail')
    password = request.form.get('password')

    # encrypt passwords using bcrypt flask-bcrypt, requires python3 to work
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    con = sqlite3.connect('accounts')
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # checking if username is already present
    u_cmd = 'SELECT username from users where username = "{0}"'.format(
        username)
    cur.execute(u_cmd)
    uname_rows = cur.fetchall()
    # checking if mail is present
    m_cmd = 'SELECT mail from users where mail = "{0}"'.format(mail)
    cur.execute(m_cmd)
    m_rows = cur.fetchall()

    if uname_rows != []:  # already a user with this username
        return render_template("signUp.html", msg="Username Taken")

    if m_rows != []:  # already a user with this mail
        return render_template("signUp.html", msg="Mail address already registered.")

    cmd = 'INSERT INTO users (username, mail, password) VALUES("{0}", "{1}", "{2}")'.format(
        username, mail, pw_hash)
    cur.execute(cmd)

    con.commit()

    # extracting the userid from the database.
    cmd = 'SELECT id from users where mail = "{0}"'.format(mail)
    cur.execute(cmd)

    rows = cur.fetchall()

    con.close()

    for entry in rows:
        userId = entry['id']

    # creating a session
    session["username"] = username
    session["userId"] = userId

    # redirect to the profile page
    return redirect(url_for("profilePage", user=username))


# Validate Credentials from Database for Login
@app.route("/signInValidation", methods=["POST"])
def signInValidation():

    mail = request.form.get('mail')
    password = request.form.get('password')

    con = sqlite3.connect("accounts")
    con.row_factory = sqlite3.Row

    cur = con.cursor()

    # login validation: check if email is present in db
    cmd = 'SELECT * FROM users WHERE mail == "{0}"'.format(mail)
    cur.execute(cmd)
    rows = cur.fetchall()
    con.close()

    if rows == []:
        # no user with sepcified credentials
        return redirect(url_for('signUp'))

    for entry in rows:
        username = entry['username']
        stored_hash = entry['password']
        userId = entry['id']

    # check password
    if bcrypt.check_password_hash(stored_hash, password):  # returns True
        # create a session for the user

        session["username"] = username
        session["userId"] = userId

        # redirect to profile page
        return redirect(url_for('profilePage'))
    else:
        return redirect(url_for('signIn'))


# Profile Page
@app.route("/profile", methods=["GET", "POST"])
def profilePage():

    # if someone tries to access a profile page without sigining in
    if session == {}:
        return redirect(url_for('hello'))

    return render_template("profile.html", data=session)


rec_created = False  # flag for recording created

# Process sample sent to server by the recorder


@app.route("/process_sample", methods=["POST"])
def process_sample():
    global rec_created  # to modify flag
    recorded_sample = request.files["sample_data"]

    # saving the recording sample to disk
    with open("rec_sample.wav", "wb") as rec:
        recorded_sample.save(rec)

    # converting the saved file to RIFF/RIFX using ffmpeg (device agnostic)
    if os.name == 'nt':  # Windows
        subprocess.run(["powershell", "ffmpeg -y -i rec_sample.wav rec_output.wav"], shell=True)
    else:               # macOS/Linux
        subprocess.run("ffmpeg -y -i rec_sample.wav rec_output.wav", shell=True)

    rec_created = True  # allow song identification to take place
    return redirect(url_for("profilePage"))


@app.route("/song_prediction")
def gen_prediction():
    try:
        global rec_created

        while rec_created == False:  # waiting for recording to be created
            continue

        # song recording has been created and identification can begin
        engine_pred = run_engine.engine()
        print(engine_pred)

        pred_json = json.dumps({
            "ans": engine_pred
        })

        rec_created = False  # resetting flag

        return pred_json
    except ValueError as v:
        pred_json = json.dumps({
            "ans": "Recording Not Viable"
        })

        rec_created = False

        return pred_json


# logout function
@app.route('/logout')
def logout():
    session.pop("username", None)
    session.pop("userId", None)
    session.pop("song_prediction", None)

    return redirect(url_for('hello'))


if __name__ == "__main__":
    app.run()
