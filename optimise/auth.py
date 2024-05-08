import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from optimise.db import get_db
from optimise.forms import RegistrationForm, LoginForm, changeExpenseBudget

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        last_name = form.last_name.data
        first_name = form.first_name.data
        username = form.username.data
        email = form.email.data
        device_id = form.device_id.data
        password = form.password.data
        db = get_db()

        db.execute(
            "INSERT INTO User (last_name, first_name, username, email, device_id, password) VALUES (?, ?, ?, ?, ?, ?)",
            (last_name, first_name, username, email, device_id, generate_password_hash(password)),
        )
        db.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)



@bp.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        db = get_db()
        user = db.execute(
            'SELECT * FROM User WHERE email = ?', (email,)
        ).fetchone()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            # next_page = request.args.get('next')
            # return redirect(next_page) if next_page else redirect(url_for('home'))
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('auth/login.html', title='Login', form=form)


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM User WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

