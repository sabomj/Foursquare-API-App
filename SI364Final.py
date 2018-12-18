#SI364finalproject
#Madeleine Sabo

import os
from flask import Flask, render_template, session, redirect, request, url_for, flash
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from werkzeug.security import generate_password_hash, check_password_hash

import requests
import json

from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

#applicationconfigs

app = Flask(__name__)
app.debug = True
app.use_reloader = True
app.config['SECRET_KEY'] = 'hard to guess string from si364'
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/sabomjfinal"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


#appsetup
manager = Manager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


# Login configurations setup
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)

#associationtables
venue_collection = db.Table('venue_collection', db.Column('user_id', db.Integer, db.ForeignKey('reviews.id')), db.Column('collection_id', db.Integer, db.ForeignKey('venueCollection.id')))
venue_reviews = db.Table('venue_reviews', db.Column('search_id', db.Integer, db.ForeignKey('search.id')), db.Column('review_id', db.Integer, db.ForeignKey('reviews.id')))

##################
##### MODELS #####
##################

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    collection = db.relationship('VenueCollection', backref='User')

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

## DB load function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class VenueReview(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    venue = db.Column(db.String(64))
    review_text = db.Column(db.String(1000))

    def __repr__(self):
        return "Review of {}: {}".format(self.venue, self.review_text)


class VenueCollection(db.Model):
    __tablename__ = 'venueCollection'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(255))
    description = db.Column(db.String(255))
    venue = db.relationship('VenueReview', secondary=venue_collection, backref=db.backref('venueCollection', lazy='dynamic'), lazy='dynamic')

class Search(db.Model):
    __tablename__ = 'search'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(64), unique=True)
    reviews = db.relationship('VenueReview', secondary=venue_reviews, backref=db.backref('search', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return " {}".format(self.term)

########################
######## Forms #########
########################

class RegistrationForm(FlaskForm):
    email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
    username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
    password2 = PasswordField("Confirm Password:",validators=[Required()])
    submit = SubmitField('Register User')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class SearchForm(FlaskForm):
    search = StringField('Enter a venue in Ann Arbor to search: ', validators=[Required()])
    submit = SubmitField('Submit')

class CollectionCreateForm(FlaskForm):
    name = StringField('Name of Collection: ', validators=[Required()])
    description = StringField('Enter a description for your collection:', validators=[Required()])
    choose_venues = SelectMultipleField('Venues to include: ')
    submit = SubmitField('Create Venue Collection')

class UpdateButtonForm(FlaskForm):
    submit = SubmitField('Update Name of Collection')

class NewNameForm(FlaskForm):
    new_update = StringField('What is the new name of your collection:', validators=[Required()])
    submit = SubmitField("Update")

class DeleteButtonForm(FlaskForm):
    submit = SubmitField("Delete Collection")


########################
### Helper functions ###
########################

def api_search(search_string):
    baseurl = 'https://api.foursquare.com/v2/venues/search'
    params = {'client_id': '5VAU2NNH03XOEEP0GOXFNZFUN1PGPVWLMGTUPKUZDXKAUXFK', 'client_secret': 'DWY24ITJFTPM3ZDOIZN2E2KPGR224UXCT51DML0SNYOCT4FL', 'query': search_string, 'v': 20181020, 'near': 'Ann Arbor', 'limit':50}
    data = requests.get(baseurl, params = params)
    json_data = json.loads(data.text)
    # return json_data['response']
    # print (json_data)

    venuesid = json_data['response']['venues'][0]['id']
    venue_name = json_data['response']['venues'][0]['name']
    search = str(venuesid)

    baseurl_tips = 'https://api.foursquare.com/v2/venues/' + search + '/tips'
    tips = requests.get(baseurl_tips, params= {'client_id': '5VAU2NNH03XOEEP0GOXFNZFUN1PGPVWLMGTUPKUZDXKAUXFK', 'client_secret': 'DWY24ITJFTPM3ZDOIZN2E2KPGR224UXCT51DML0SNYOCT4FL', 'v':20181020, 'mins': 3})
    tips_text = json.loads(tips.text)

    tips_list_text = []
    for x in tips_text['response']['tips']['items']:
        tips_list_text.append(x['text'])
        # list_to_string = ' (2) '.join(tips_list_text)
    return (venue_name, tips_list_text)
# print api_search('espresso royale')
#     # print(tips_list_text)

def get_review_by_id(id):
    i = VenueReview.query.filter_by(id=id).first()
    return i

def get_or_create_review(venue, review_text):
    i = VenueReview.query.filter_by(review_text=review_text).first()
    if not i:
        i = VenueReview(venue=venue, review_text = review_text)
        db.session.add(i)
        db.session.commit()
        return i

def get_or_create_search_term(term):
    search_string = Search.query.filter_by(term=term).first()
    if not search_string:
        search_string = Search(term=term)
        add_search = api_search(term)
        for x in add_search:
            venue = add_search[0]
            if len((add_search[1])) < 0:
                review_text = "No Reviews to show"
            if len((add_search[1])) == 1:
                split1 = str((add_search[1])[0])
                review_text = "(1)" + split1
            else:
                split1 = str((add_search[1])[0])
                split2 = str((add_search[1])[1])
                review_text = "(1) " + split1 + " (2) " + split2
        review_user = get_or_create_review(venue, review_text)

        search_string.reviews.append(review_user)
        db.session.add(search_string)
        db.session.commit()
        return search_string


def get_or_create_collection(name, description, current_user, venue_list=[]):
    user_collection = VenueCollection.query.filter_by(name=name, user_id=current_user.id).first()
    if not user_collection:
        user_collection = VenueCollection(name=name, user_id=current_user.id, description=description, venue = venue_list)
        for x in venue_list:
            user_collection.venue.append(x)
        db.session.add(user_collection)
        db.session.commit()
        return user_collection


########################
#### View functions ####
########################

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out, thank you for visiting.')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can log in!')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route('/secret')
@login_required
def secret():
    return "Only authenticated users can do this, sorry!"

@app.route('/', methods=['GET', 'POST'])
def index():
    form = SearchForm()
    if form.validate_on_submit():
        get_or_create_search_term(form.search.data)
        return redirect(url_for('review_results', search_string=form.search.data))
    return render_template('index.html', form=form)

@app.route('/searched_reviews/<search_string>')
def review_results(search_string):
    term = Search.query.filter_by(term=search_string).first()
    searched_reviews = term.reviews.all()
    return render_template('searched_reviews.html', searched_reviews=searched_reviews, term=term)

@app.route('/search_terms')
def search_terms():
    all_search_terms = Search.query.all()
    return render_template('search_terms.html', all_search_terms=all_search_terms)

@app.route('/all_reviews')
def all_reviews():
    reviews = VenueReview.query.all()
    return render_template('all_reviews.html', all_reviews=reviews)

@app.route('/create_venue_collection',methods=["GET","POST"])
@login_required
def create_collection():
    form = CollectionCreateForm()
    reviews = VenueReview.query.all()

    choices = [(x.id, x.venue) for x in reviews]
    form.choose_venues.choices = choices
    if request.method == 'POST':
        chosen_venues = form.choose_venues.data
        review_obj = [get_review_by_id(int(x)) for x in chosen_venues]
        get_or_create_collection(name=form.name.data, current_user=current_user, description=form.description.data, venue_list=review_obj)
        return redirect(url_for('user_collections'))
    return render_template('create_collection.html', form=form)

@app.route('/collections', methods=["GET","POST"])
@login_required
def user_collections():
    update = UpdateButtonForm()
    delete = DeleteButtonForm()
    collections = VenueCollection.query.filter_by(user_id=current_user.id).all()
    return render_template('user_collections.html', collections=collections, form = update, form1 = delete)

@app.route('/collection/<id_num>')
def collection(id_num):
    id_num = int(id_num)
    collection = VenueCollection.query.filter_by(id=id_num).first()
    venues = collection.venue.all()
    return render_template('collection.html', collection=collection, venues=venues)

@app.route('/update/<collection>',methods=["GET","POST"])
def update(collection):
    form = NewNameForm()
    if form.validate_on_submit():
        if request.method == 'POST':
            all_items = VenueCollection.query.filter_by(description=collection).first()
            all_items.name = form.new_update.data
            db.session.commit()
            flash('The name of your collection has been changed to "{}" '.format(all_items.name))
            return redirect(url_for('user_collections'))

    return render_template('update_collection.html', collection=collection, form=form)

@app.route('/delete/<collection>',methods=["GET","POST"])
def delete(collection):
    collection = VenueCollection.query.filter_by(name=collection).first()
    db.session.delete(collection)
    db.session.commit()

    flash('Collection has been deleted')
    return redirect(url_for('user_collections'))


if __name__ == '__main__':
    db.create_all()
    manager.run()
