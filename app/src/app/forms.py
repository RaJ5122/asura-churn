from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SelectField, FileField, RadioField
from wtforms.validators import DataRequired, Optional, NumberRange

class AddCustomerForm(FlaskForm):
    customer_id = StringField('Customer ID', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[Optional(), NumberRange(min=0)])
    gender = SelectField('Gender', choices=[
        ('', 'Select'),
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ], validators=[Optional()])
    location = StringField('Location', validators=[Optional()])
    subscription_length_months = IntegerField('Subscription Length (months)', 
        validators=[DataRequired(), NumberRange(min=0)])
    monthly_bill = FloatField('Monthly Bill', 
        validators=[DataRequired(), NumberRange(min=0)])
    total_usage_gb = FloatField('Total Usage (GB)', 
        validators=[DataRequired(), NumberRange(min=0)])

class DynamicAnalysisForm(FlaskForm):
    data_source = RadioField('Data Source', 
                           choices=[('database', 'Database'), ('file', 'File Upload')],
                           default='database')
    file = FileField('Upload File', validators=[Optional()])
    age_range = SelectField('Age Range', 
                          choices=[
                              ('', 'All Ages'),
                              ('18-25', '18-25'),
                              ('26-35', '26-35'),
                              ('36-45', '36-45'),
                              ('46-55', '46-55'),
                              ('56-100', '56+')
                          ],
                          validators=[Optional()])
    location = SelectField('Location', validators=[Optional()])
    gender = SelectField('Gender',
                        choices=[
                            ('all', 'All Genders'),
                            ('Male', 'Male'),
                            ('Female', 'Female'),
                            ('Other', 'Other')
                        ],
                        validators=[Optional()])
    subscription_range = SelectField('Subscription Length',
                                   choices=[
                                       ('', 'All Lengths'),
                                       ('0-6', '0-6 months'),
                                       ('7-12', '7-12 months'),
                                       ('13-24', '13-24 months'),
                                       ('25-100', '25+ months')
                                   ],
                                   validators=[Optional()])
    usage_range = SelectField('Usage Range',
                            choices=[
                                ('', 'All Usage'),
                                ('0-50', '0-50 GB'),
                                ('51-100', '51-100 GB'),
                                ('101-200', '101-200 GB'),
                                ('201-1000', '201+ GB')
                            ],
                            validators=[Optional()]) 