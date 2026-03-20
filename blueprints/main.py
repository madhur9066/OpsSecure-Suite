"""blueprints/main.py — Dashboard"""
from flask import Blueprint, render_template, request
from modules.db import ResultRepo

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html",
                           stats=ResultRepo.get_stats(),
                           current_path=request.path)
