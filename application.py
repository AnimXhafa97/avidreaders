import os
import random
import requests

from flask import Flask, session, render_template, request, redirect, url_for, g
from markupsafe import escape
from flask_session.__init__ import Session
from sqlalchemy import create_engine, exists
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps

app = Flask(__name__)



# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["secret_key"] = 'sdf$@@ERfgfh65%^#^$3451<:>UL][;][]&>KU^$%"^>SD?>A:>G:$>G:W>G"'
app.config['SESSION_COOKIE_SECURE'] = False
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("username") is None:
            message = "Please log in to search for books!"
            return render_template("login.html", message = message)
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    if session.get("logged_in") == True:
        return render_template("home_log.html")
    return render_template("home.html")

#backend for the registration page
@app.route("/register/", methods=["GET", "POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("psw")
    confirm_password = request.form.get("psw-repeat")
    if request.method == "GET":
        return render_template("register.html")
    else:
        if password != confirm_password:
            return "Error. Passwords do not match. Please go back and try again."
        data_insert = db.execute("INSERT INTO avidreaders (usernames, passwords) VALUES (:username, :password)", {
        "username":username,
        "password":password,
        })
        db.commit()
        return render_template("welcome.html", username = username)


#backend for the login page
@app.route("/login/", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "GET":
        return render_template("login.html")
    else:
        session["username"] = request.form.get("username")
        session["password"] = request.form.get("password")
        #user_check = db.execute("SELECT * FROM avidreaders WHERE avidreaders.usernames = :username", {
        # "username":session["username"],
        # }).fetchone()
        #
        # pass_check = db.execute("SELECT * FROM avidreaders WHERE avidreaders.passwords = :password", {
        # "password":session["password"],
        # }).fetchone()
        user_check = db.execute("SELECT * FROM avidreaders WHERE avidreaders.usernames = :username AND avidreaders.passwords = :password", {"username":session["username"], "password":session["password"]}).fetchone()
        message = "Incorrect username or password"
        if not user_check:
            return render_template("error.html", message = message)
        session["user_id"] = user_check.user_id
        session["logged_in"] = True
        message = "Incorrect username or password"
        return render_template("welcome.html", username = session["username"])


@app.route("/logout/")
@login_required
def logout():
    session.clear()
    session["logged_in"] = False
    return render_template("home.html")

@app.route("/books/", methods = ["GET", "POST"])
@login_required
def books():
    titles = []
    authors = []
    #good idea but write a faster search algorithm when you learn more about algorithms!
    #all this does is select 10 random books from the database and display them in the table
    for i in range(10):
        random_id = random.randint(1,4999)
        title = db.execute("SELECT title FROM books WHERE books.id = :id", {"id":random_id}).fetchone()[0]
        titles.append(title)
        author = db.execute("SELECT author FROM books WHERE books.id = :id", {"id":random_id}).fetchone()[0]
        authors.append(author)
    return render_template("books.html", titles = titles, authors = authors)


# #implements goodreads api to display results of the user's search from the books page
@app.route("/results/", methods = ["GET", "POST"])
@login_required
def results():
    titles = []
    authors = []
    year = []
    #rating = []
    user_search = request.form.get("search")
    user_search_low = user_search.lower()
    get_search = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE :user_search_low OR LOWER(author) LIKE :user_search_low", {"user_search_low": "%" + user_search.lower() + "%"}).fetchall()
    if not get_search:
        message = "We don't have that book in our library. Try another one!"
        return render_template("error.html", message = "We don't have that book in our library. Try another one!")
    return render_template("results.html", get_search = get_search)


#lets the user post their own reviews of the book
@app.route("/results/reviews/<int:id>", methods = ["GET", "POST"])
@login_required
def reviews(id):
    get_search = db.execute("SELECT * FROM books WHERE books.id = :id", {"id":id}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "mdHzsgBxLSP3qcnKJDQfXg", "isbns":get_search.isbn})
    data = res.json()
    rating = data["books"][0]["average_rating"]
    user_review = request.form.get("user_review")
    user_rating = request.form.get("rating")
    get_reviews = db.execute("SELECT avidreaders.usernames, reviews.written, reviews.rating FROM reviews JOIN avidreaders ON avidreaders.user_id = reviews.u_id WHERE r_book_id=:id", {"id":id}).fetchall()
    if request.method == "GET":
        return render_template("reviews.html", get_search = get_search, id=id, rating = rating, get_reviews = get_reviews)
    elif request.method == "POST":
        # check if the user already posted
        # if not, append the review to the reviews database under the book's appropriate ISBN number
        #show user reviews that already exist for this book
        check = db.execute("SELECT * FROM reviews WHERE reviews.u_id = :u_id AND reviews.r_book_id = :book_id", {"u_id":session["user_id"], "book_id":id}).fetchone()
        if check is not None:
            return render_template("reviews.html", get_search = get_search, id = id, rating = rating, get_reviews = get_reviews, message = "You've already reviewed this book!")
        else:
            post = db.execute("INSERT INTO reviews (u_id, r_book_id, rating, written) VALUES (:u_id, :r_book_id, :rating, :written)", {"u_id":session["user_id"], "r_book_id":id, "rating":user_rating, "written":user_review})
            get_reviews = db.execute("SELECT avidreaders.usernames, reviews.written, reviews.rating FROM reviews JOIN avidreaders ON avidreaders.user_id = reviews.u_id WHERE r_book_id=:id", {"id":id}).fetchall()
            db.commit()
        return render_template("reviews.html", user_review = user_review, user_rating =  user_rating, get_search = get_search, id=id, rating = rating, get_reviews = get_reviews)
