from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
import history_db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

@main_bp.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied: Admin only', 'error')
        return redirect(url_for('main.index'))
        
    stats = history_db.get_user_stats()
    users = history_db.get_all_users()
    global_history = history_db.get_all_history_admin()
    
    return render_template('admin.html', stats=stats, users=users, global_history=global_history)
