from flask_wtf import FlaskForm
# from flask_wtf.file import FileField, FileAllowed
# from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from optimise.db import get_db


class RegistrationForm(FlaskForm):
    last_name = StringField('Last Name',
                           validators=[DataRequired(), Length(min=2, max=20)])
    first_name = StringField('First Name',
                           validators=[DataRequired(), Length(min=2, max=20)])
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    device_id = StringField('House identifier',
                           validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM User WHERE username = ?", (username.data,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM User WHERE email = ?", (email.data,))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')
        
    def validate_device_id(self, device_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM User WHERE device_id = ?", (device_id.data,))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            raise ValidationError('That device id is already in use. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign in')

class changeExpenseBudget(FlaskForm):
    expense_budget = IntegerField('Expense Budget', validators=[DataRequired()])
    submit = SubmitField('Submit')

class PreferenceForm(FlaskForm):
    APPLIANCE_TIME_RANGES = [
        (None, 'Choose...'),
        ('08:00-10:00', '08:00 AM - 10:00 AM'),
        ('12:00-14:00', '12:00 PM - 02:00 PM'),
        ('18:00-20:00', '06:00 PM - 08:00 PM')
    ]

    SLEEP_TIME_RANGES = [
        (None, 'Choose...'),
        ('22:00-06:00', '10:00 PM - 06:00 AM'),
        ('23:00-07:00', '11:00 PM - 07:00 AM'),
    ]

    # language = SelectField(u'Programming Language', 
    #                        choices=[('cpp', 'C++'), ('py', 'Python'), ('text', 'Plain Text')])
    temperature_preference = SelectField(u'Temperature Preference', 
                                         choices=APPLIANCE_TIME_RANGES, validators=[DataRequired()])
    lighting_preference = SelectField(u'Lighting Preference', 
                                         choices=APPLIANCE_TIME_RANGES, validators=[DataRequired()])
    tv_watchtime = SelectField(u'Television Watchtime', 
                                  choices=APPLIANCE_TIME_RANGES, validators=[DataRequired()])
    humidity_levels = IntegerField('Humidity Levels', validators=[DataRequired()])
    appliance_preference = SelectField('Appliance usage time', 
                                          choices=APPLIANCE_TIME_RANGES, coerce=str)
    sleep_time = SelectField('Preferred time of sleep', 
                                choices=SLEEP_TIME_RANGES, coerce=str)
    occupancy_preference = SelectField('When are you at home', 
                                          choices=APPLIANCE_TIME_RANGES, coerce=str)
    
    # custom_lighting_preference = StringField('Custom Lighting Preference')
    # custom_tv_watchtime = StringField('Custom Television Watchtime')
    # custom_appliance_preference = StringField('Custom Appliance usage time')
    # custom_sleep_time = StringField('Custom Preferred time of sleep')
    # custom_occupancy_preference = StringField('Custom When are you at home')

    submit = SubmitField('Save Preferences')