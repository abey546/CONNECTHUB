from flask import Flask, render_template, redirect, url_for, flash, request
from models import db, User, Event, Category, Location, Post, Comment, Like 
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from forms import RegistrationForm, LoginForm, EventForm, PostForm, CommentForm, UpdateProfileForm 
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate  # Import Flask-Migrate
from flask import request
from werkzeug.utils import secure_filename
import os
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Ab0719109663@localhost/connecthub_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'abeyhassan123456'

db.init_app(app)

# Flask-Migrate configuration
migrate = Migrate(app, db)

# Flask-Login configuration
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Function to initialize categories and locations
def init_data():
    if Category.query.count() == 0:
        categories = ['Wedding', 'Burial', 'Graduation', 'Birthday Party', 'Community Gathering']
        for name in categories:
            category = Category(name=name)
            db.session.add(category)
        db.session.commit()

    if Location.query.count() == 0:
        locations = ['Town Hall', 'Community Center', 'Park', 'Library']
        for loc_name in locations:
            location = Location(name=loc_name)
            db.session.add(location)
        db.session.commit()

# Home route
@app.route("/")
def home():
    init_data()
    events = Event.query.order_by(Event.start_date).all()
    return render_template("index.html", events=events)

# Event Details route
@app.route("/event/<int:event_id>")
def event_details(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event_details.html', event=event)

# Registration route
@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, _password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login route
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user._password_hash, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', form=form)

# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Event Creation Route
@app.route("/create_event", methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventForm()
    
    # Populate choices in the route
    form.location.choices = [(loc.id, loc.name) for loc in Location.query.all()]
    form.category.choices = [(cat.id, cat.name) for cat in Category.query.all()]

    if form.validate_on_submit():
        new_event = Event(
            title=form.title.data, 
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            location_id=form.location.data, 

            category_id=form.category.data,
            organizer_id=current_user.id
        )
        db.session.add(new_event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('home')) 
    return render_template('create_event.html', form=form)

# Profile route
@app.route("/profile")
@login_required
def profile():
    user_events = Event.query.filter_by(organizer_id=current_user.id).all()
    return render_template('profile.html', user=current_user, events=user_events)

# Posts Feed route
@app.route('/posts', methods=['GET', 'POST'])
@login_required
def posts():
    form = PostForm()
    if form.validate_on_submit():
        new_post = Post(content=form.content.data, author_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('posts'))

    # Pagination Logic
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page=page, per_page=5)
    
    return render_template('posts.html', form=form, posts=posts.items, pagination=posts)
@app.route("/profile/update", methods=['GET', 'POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    
    if form.validate_on_submit():
        if form.profile_picture.data:
            # Save the file and update the user's profile picture path
            picture_file = secure_filename(form.profile_picture.data.filename)
            form.profile_picture.data.save(os.path.join('static/profile_pics', picture_file))
            current_user.profile_picture = picture_file
        
        # Update other profile information
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.bio = form.bio.data
        current_user.website_link = form.website_link.data
        current_user.contact_email = form.contact_email.data

        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))

    # Pre-populate the form with current user data
    form.first_name.data = current_user.first_name
    form.last_name.data = current_user.last_name
    form.bio.data = current_user.bio
    form.website_link.data = current_user.website_link
    form.contact_email.data = current_user.contact_email
    
    return render_template('update_profile.html', form=form)

# Post Details route
@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def post_details(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        #new_comment = Comment(content=form.content.data, author_id=current_user.id, post_id=post.id)
        new_comment = Comment(content=form.content.data, user_id=current_user.id, post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('post_details', post_id=post.id))

    return render_template('post_details.html', post=post, form=form)

# Like Post route
@app.route("/like/<int:post_id>", methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if like:
        db.session.delete(like)
        flash('Post unliked.', 'info')
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(new_like)
        flash('Post liked!', 'success')

    db.session.commit()
    return redirect(url_for('posts'))

# Unlike Post route
@app.route("/unlike/<int:post_id>", methods=['POST'])
@login_required
def unlike_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if like:
        db.session.delete(like)
        db.session.commit()
    return redirect(url_for('posts'))

# Comment on Post route
@app.route("/comment/<int:post_id>", methods=['POST'])
@login_required
def comment_post(post_id):
    form = CommentForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added!', 'success')
    return redirect(url_for('posts'))

if __name__ == "__main__":
    app.run(debug=True)

