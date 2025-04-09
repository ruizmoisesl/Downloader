from flask import Flask, render_template,session
import os



def spotify(session_user=None):
    name = 'Spotify'
    if session_user is None:
        session_user = session.get('user')
    return render_template("spotify.html", name=name, session_user=session_user)

def youtube(session_user=None):
    name = 'Youtube'
    if session_user is None:
        session_user = session.get('user')
    return render_template("youtube.html", name=name, session_user=session_user)

def soundcloud(session_user=None):
    name = 'Soundcloud'
    if session_user is None:
        session_user = session.get('user')
    return render_template("souncloud.html", name=name, session_user=session_user)