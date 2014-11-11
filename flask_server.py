from flask import Flask, render_template, redirect, request, flash, session
from model import User, Movie, Rating, session as dbsession 
import omdb
import json

app = Flask(__name__)
app.secret_key ='bosco'


@app.route("/")
def index():
	return render_template("front.html")

@app.route("/login", methods=["POST"])
def login():

	# fetch email and password from userinput client-side
    email = request.form.get("email")
    password = request.form.get("password")
    
    # check for user email and password in db
    u = dbsession.query(User).filter_by(email=email).filter_by(password=password).first()
   
    #if user is in db, add to session (cookie dictionary), if not redirect to login url
    if u:
        session["login"] = u.id
        print session
        return redirect("/wall")      
    else:
        flash("User not recognized, please try again or signup")
        return redirect("/")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session["login"] = "" 
    return redirect("/") 

@app.route("/sign_up")
def sign_up():
    return render_template("sign_up.html")

@app.route("/sign_up_form", methods=["POST"])
def sign_up_form():
	## input new user row into database and redirect to wall page

	# fetch email, password, etc., from userinput client-side
    # add if request.form else redirect back to sign_up?

    email = request.form.get("email")
    password = request.form.get("password")
    username = request.form.get("username")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    gender = int(request.form.get("gender"))
    age = int(request.form.get("age"))
    zipcode = request.form.get("zipcode")
    
    # create an instance of User with email, password, username, etc. as attributes
    user = User(email=email, password=password, username=username, first_name=first_name, last_name=last_name, gender=gender, age=age, zipcode=zipcode)

	# check for email in db, if not there, add it to db
    if dbsession.query(User).filter_by(email = email).first():
		flash("This email address is already in use. Please try again.")
		return redirect("/sign_up")
    else:
 		dbsession.add(user)
 		dbsession.commit()
 		return redirect("/wall")
# need to create 'forgot your password' feauture

@app.route("/my_profile")
def my_profile():
    #gets the email from the session dictionary of logged-in user
    user_id = session["login"]
    #gets the ratings of that user
    ratings = dbsession.query(Rating).filter_by(user_id = user_id).all()
    return render_template("my_profile.html", user_id=user_id, ratings=ratings)

@app.route("/user_profile")
def user_profile(id):
    user = dbsession.query(User).filter_by(id=id).join(Rating).join(Movie).first()
    ratings = dbsession.query(Rating).filter_by(user_id = id).all()
    print len(ratings)
    return render_template("user.html", user=user, ratings=ratings)

@app.route("/wall")
def user_wall():
	return render_template("wall.html")

# gets the movie prof by calling API
# @app.route("/movie_prof", methods=["GET", "POST"])
# def movie_prof():
#     #retrieve user input from main.html and set variable movie to movie title
#     movie = request.args.get("movie")
	
# 	# query API for move title using OMDb API parameters
#     res = omdb.request(t=movie, r='JSON')
#     json_content = json.loads(res.content)
#     return render_template("movie_prof.html", movie=movie, json=json_content)

@app.route("/movie_prof", methods=["GET"])
def search():
    #retrieve user input from main.html and set variable movie to movie title
    movie = request.form.get("movie")
    #query database by movie title
    movie_info = dbsession.query(Movie).filter_by(movie_title = movie).first()
    #fetch attribute for release date
    released = movie_info.Released
    #fetch attribute for imdbRating
    poster = movie_info.Poster
    #fetch attribute for ratings
    ratings = movie_info.ratings
    print movie_info
    print session
    return render_template("movie_prof.html", ratings = ratings, movie = movie, released = released, poster = poster)

@app.route("/movie_list")
def movie_list():
    movie_list = dbsession.query(Movie).limit(20).all()
    return render_template("movie_list.html", movies=movie_list)


# @app.route("/genres")
# def genres():
#     genre_list = dbsession.query(Movie.Genre).all()
#     return render_template("genres.html", genre=genre_list)

if __name__ == '__main__':
	# starts the built-in web server on port 5000
	app.run(debug = True)