# TODO: Compile the main HTML here, embed plots

from flask import render_template

def build_frontend():
    """Render the frontend page dynamically."""
    return render_template("frontend.html")
