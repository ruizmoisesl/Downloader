from flask import Flask, render_template, request, jsonify, send_file


def spotify():
    return render_template("spotify.html")