from flask import Flask, render_template, request, jsonify, send_file


def spotify():
    name = 'Spotify'
    return render_template("spotify.html", name = name)

def youtube():
    name = 'Youtube'
    return render_template("youtube.html", name = name)

def soundcloud():
    name = 'Soundcloud'
    return render_template("souncloud.html", name = name)