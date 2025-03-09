from flask import Flask, render_template, request, jsonify, send_file

def index():
    return render_template("index.html")