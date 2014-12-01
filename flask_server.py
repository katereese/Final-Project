# -*- coding: utf-8 -*-
import collections
import datetime
from flask import Flask, render_template, redirect, request, flash, session
from model import User, Media, Rating, Genre, genres, session as dbsession
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, func, and_
from sqlalchemy.sql import label
from sqlalchemy.sql.expression import text, column
from werkzeug.contrib.cache import SimpleCache
import json
import omdb
import urllib

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

app = Flask(__name__)
app.secret_key ='bosco'
# Simple cache should only be initialized once
cache = SimpleCache()

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
		session["user"] = u
		print session
		return redirect("/wall")      
	else:
		flash("User not recognized, please try again or signup")
		return redirect("/")

@app.route("/logout", methods=["GET", "POST"])
def logout():
	session.clear()
	print "logged out"
	return redirect("/") 

@app.route("/sign_up")
def sign_up():
	return render_template("sign_up.html", user=get_current_user())

@app.route("/sign_up", methods=["POST"])
def sign_up_form():
		## input new user input into database
		email = request.form.get("email")
		password = request.form.get("password")
		username = request.form.get("username")
		first_name = request.form.get("first_name")
		last_name = request.form.get("last_name")
		gender = int(request.form.get("gender"))
		age = int(request.form.get("age"))
		zipcode = request.form.get("zipcode")
		
		# create an instance of User with email, password, username, etc. as attributes
		user = User(email=email, password=password, username=username, first_name=first_name, 
			last_name=last_name, gender=gender, age=age, zipcode=zipcode)
		
		# check for email in db, if not there, add it to db
		if dbsession.query(User).filter_by(email = email).first():
			flash("This email address is already in use. Please try again.")
			return redirect("/sign_up")
		else:
			dbsession.add(user)
			dbsession.commit()
			created_user = dbsession.query(User).filter_by(email = email).first()
			session["login"] = created_user.id
			session["user"] = created_user
			return redirect("/pick_genres")

def get_current_user():
	if 'user' in session:
		return dbsession.query(User).\
			options(joinedload('genres')).\
			filter_by(id = session['user'].id).first()
	else:
		return None

@app.route("/my_profile")
def my_profile():
	# fetch user_id from the session dictionary of logged-in user
	user_id = session["login"]
	# query Rating object filtering on user_id column and user_id stored in the "login" session
	ratings = dbsession.query(Rating).filter_by(user_id = user_id).all()
	# query User object, joining in follows association table
	user = dbsession.query(User).options(joinedload('follows')).filter_by(id=user_id).first()
	return render_template("my_profile.html", user=user, ratings=ratings)

@app.route("/user_list")
def user_list():
	loggedin_user = int(session["user"].id)
	# print user_id
	user_list = []
	# queries list of user objects sorted by highest number of ratings made
	user_ids = dbsession.query(Rating.user_id).group_by(Rating.user_id).order_by(desc(func.count(Rating.id))).limit(10).all()
	# iterates through each object in list and appends the first element, which is user id
	for u_id in user_ids:
		if u_id[0] == loggedin_user:
			continue
		else:
			user = dbsession.query(User).filter_by(id = u_id[0]).first()
			user_list.append(user)
	
	# query User object, joining in follows association table
	user = dbsession.query(User).options(joinedload('follows')).filter_by(id=loggedin_user).first()
	return render_template("user_list.html", users=user_list, user=user)

@app.route("/user_search")
def user_search():
	loggedin_user_id = int(session["user"].id)
	
	# retrieve user input from user_list.html and set variable user to input
	email_input = request.args.get("email")
	if not email_input:
		return redirect("/user_list")

	# query database by user email
	user_info = dbsession.query(User).filter_by(email = email_input).first()
	if not user_info:
		# user wasn't found
		flash("This user does not exist. Please try again.")
		return redirect("/user_list")
	
	# logic that redirects user to their profile
	if user_info.id == loggedin_user_id:
		return redirect("/my_profile")
	else:
		return redirect("/user_profile?id=%d" % user_info.id)

@app.route("/user_profile", methods=["GET"])
def user_profile():
	id = int(request.args.get("id"))
	current_user = None
	if 'user' in session:
		current_user = dbsession.query(User).options(joinedload('follows')).get(session['user'].id)

	user_info = dbsession.query(User).filter_by(id=id).first()
	ratings = dbsession.query(Rating).options(joinedload('movie')).filter_by(user_id = user_info.id).all()

	avg_rating = average_rating(ratings)
	return render_template("user_profile.html", user=user_info, ratings=ratings, avg_rating=avg_rating, current_user=current_user)

@app.route("/follow_user", methods=["POST"])
def follow_user():
	loggedin_user_id = int(session["user"].id)
	# fetch followee id from template button submit form
	followee_id = int(request.form.get('followee_id'))
	#test
	print "%d wants to follow %d" % (loggedin_user_id, followee_id)

	# create objects that gets the followee and follower/loggedin user ids
	follower_obj = dbsession.query(User).get(loggedin_user_id)
	followee_obj = dbsession.query(User).get(followee_id)

	# append the follower object with a value of followee obj through the follows relationship
	follower_obj.follows.append(followee_obj)
	dbsession.commit()
	return redirect("/my_profile")

@app.route("/movie_search")
def movie_search():
	## movie search
	title = request.args.get("title")
	movies = None
	movies2 = None

	if title:
		# first try to find exact matches
		movies = dbsession.query(Media).filter(Media.title == title).filter(Media.omdbLoad != None).all()
		# fall back on matching parts of the string
		# if not movies:
		movies2 = dbsession.query(Media).filter(Media.title.contains(title)).filter(Media.omdbLoad != None).all()
		fixtitle(movies)
		fixtitle(movies2)

	return render_template("movie_search.html", movies=movies, movies2=movies2)

@app.route("/wall")
def user_wall():
	## lists Friends recommendations
	if "user" in session:
		# joins logged in user and the follows relationship
		user = dbsession.query(User).options(joinedload('follows')).filter_by(id = session["user"].id).first()
		# extract user id:s of people the user is following
		followed_ids = []
		for u in user.follows:
			followed_ids.append(u.id)

		# queries for movies that have been rated by people the user follows
		# but not the user itself.
		#
		# 'reset_joinpoint().outerjoin(...).filter()' filters out the user's own
		# ratings.
		follows_media = dbsession.query(Media,
			label('avg_rating', func.avg(Rating.rating))).\
			join(Rating).\
			join(User).\
			filter(User.id.in_ (followed_ids)).\
			reset_joinpoint().\
			outerjoin(Rating, and_(Rating.movie_id == Media.id, Rating.user_id == user.id), aliased = True).\
			filter(Rating.movie_id == None).\
			group_by(Media.id).\
			order_by(desc('avg_rating')).\
			limit(20)

	## lists Videodrome recommendations
	genre_dict = {}
	# queries the user's picked genres
	if "user" in session:
		# joins logged in user and the genres relationship, which includes user ids and genre ids
		user = dbsession.query(User).options(joinedload('genres')).filter_by(id = session["user"].id).first()
		# keeps order intact
		genre_dict = collections.OrderedDict()

		# check cache if it already has a genre_dict for this user id
		genre_dict_from_cache = cache.get(session["user"].id)
		# if not, then generate the media
		if genre_dict_from_cache is None:
			print "\n\nNot found in Cache\n\n"
			# genre id:s for query below
			genre_ids = []
			for i in user.genres:
				genre_ids.append(i.id)

			# for each genre associated to the user
			base_query_result = base_media_query()
			for i in user.genres:
				base_query_in_loop = base_query_result
				# queries lists of movies for each picked genre, by joining the genres relationship
				## previous query: media = base_media_query().join(genres).filter_by(genre_id=i.id).limit(5).all()
				### new portion of query removes movies user has rated
				media = base_query_in_loop\
					.join(genres)\
					.filter_by(genre_id=i.id)\
					.outerjoin(Rating, and_(Rating.movie_id==Media.id, Rating.user_id == user.id))\
					.filter(Rating.movie_id==None)\
					.limit(5)\
					.all()
				# unicode fix
				fixtitle(media)
				# assigns each genre item as key to (list of movies) value
				genre_dict[i] = media
			# set the generated media inside cache for the next time
			cache.set(session["user"].id, genre_dict, timeout=10*60)
		else:
			# Found it in cache! Use the cached value!
			print "\n\nFound in cache!\n\n"
			genre_dict = genre_dict_from_cache

	return render_template("wall.html", genres = genre_dict, media=follows_media)

def base_media_query():
	print "I'm querying all the darn movies again.."
	# sorts movies by higest tomato meter, then highest imdb rating ---- want to filter by already rated
	return dbsession.query(Media).order_by(desc('tomatoMeter')).order_by(desc('imdbRating'))

@app.route("/genre_prof", methods=["GET"])
def genre_profile():
	id = int(request.args.get("id"))
	if not id:
		return redirect("/wall")
	genre = dbsession.query(Genre).get(id)
	media = base_media_query().join(genres).filter_by(genre_id=id).limit(100).all()
	fixtitle(media)
	
	return render_template("genre_prof.html", media = media, genre = genre)

@app.route("/movie_prof", methods=["GET"])
def movie_profile():
	user = get_current_user()
	id = request.args.get("id")
	if not id:
		return redirect("/wall")

	movie_info = dbsession.query(Media).options(joinedload('genres')).get(id)
	if not movie_info:
		# movie wasn't found
		flash("This movie does not exist. Please try again.")
		return redirect("/wall")

	# FIXME: fix this workaround for utf-8 decoding weirdness in flask/jinja
	if movie_info.director:
		movie_info.director = movie_info.director.decode('utf-8', 'ignore')
	if movie_info.actors:
		movie_info.actors = movie_info.actors.decode('utf-8', 'ignore')
	if movie_info.plot:
		movie_info.plot = movie_info.plot.decode('utf-8', 'ignore')

	ratings = dbsession.query(Rating).options(joinedload('user')).filter_by(movie_id = id).all()
	avg_rating = average_rating(ratings)

	# get rating of currently logged in user
	current_user_rating = None
	for rating in ratings:
		if rating.user == user:
			current_user_rating = rating
			break

	return render_template("movie_prof.html", movie=movie_info, ratings=ratings, avg_rating = avg_rating, user=user, current_user_rating = current_user_rating)

@app.route("/add_rating", methods=["POST"])
def add_rating():
	#get movie from search in movie_prof.html
	movie_id = int(request.form.get("id"))
	movie_from_wall = request.form.get("rating_from_wall")
	user_id = int(session["user"].id)
	score = int(request.form.get("rating"))
	review = request.form.get("movie_review")
	if not review:
		review = ""

	rating = dbsession.query(Rating).filter_by(user_id = user_id, movie_id=movie_id).first()
	if not rating:
		# add new rating
		rating = Rating(movie_id = movie_id, user_id = user_id, rating = score, review = review)
	else:
		# update existing rating
		rating.rating = score
		rating.review = review

	dbsession.add(rating)
	dbsession.commit()
	clear_user_cache()

	## flash message that it's been added?
	if movie_from_wall:
		return redirect("/wall")
	else:
		return redirect("/movie_prof?id=%d" % movie_id)

def clear_user_cache():
	cache.set(session["user"].id, None, timeout=0)

@app.route("/movie_list")
def movie_list():
	movie_list = dbsession.query(Media).limit(20).all()
	return render_template("movie_list.html", movies=movie_list)

def average_rating(ratings):
	if len(ratings) == 0:
		return 0.0
	sum = 0
	for r in ratings:
		sum = sum + r.rating
	return float("{0:.1f}".format(float(sum) / len(ratings)))

@app.route("/pick_genres")
def pick_genres():
	# get a list of all genres
	genres = dbsession.query(Genre).all()
	# load current user and all her/his/it genre selections
	user = get_current_user()

	return render_template("pick_genres.html", genres=genres, user=user)

@app.route("/post_genres", methods=["POST"])
def post_genres():
	# get logged in user and user genre picks from pick_genres.html
	user_obj = get_current_user()
	genre_ids = [int(gi) for gi in request.form.getlist('genres')]

	# modifying the collection that we're itering over is no bueno
	genres_in_db = dbsession.query(Genre).all()
	for g in genres_in_db:
		if g in user_obj.genres:
			user_obj.genres.remove(g)
	try:
		print "Committing..\n\n"
		dbsession.commit()
	except:
		print "\n\n\nRolling back uh oh\n\n\n"
		dbsession.rollback()

	for gi in genre_ids:
		genre_obj = dbsession.query(Genre).filter_by(id=gi).first()
		user_obj.genres.append(genre_obj)
	try:
		dbsession.commit()
		cache.set(session["user"].id, None, timeout=0)
	except:
		dbsession.rollback()
	return redirect("/wall")

# filter out junk characters that break decoding with this error:
# UnicodeDecodeError: 'utf8' codec can't decode byte 0xa2 in position 43: invalid start byte
def fixtitle(movies):
	if movies==None:
		return
	for movie in movies:
		movie.title = movie.title.decode('utf-8', 'ignore')
		if movie.shortPlot:
			movie.shortPlot = movie.shortPlot.decode('utf-8', 'ignore')



# gets the movie prof by calling OMDB API
@app.route("/movie_prof_API", methods=["GET", "POST"])
def movie_prof_API():
	id = request.args.get("id")
	movie_info = dbsession.query(Media).get(id)
	if not movie_info:
		# movie not found
		redirect('/wall')
	populate_movie_from_OMDB(movie_info)
	return redirect("/movie_prof?id=%d" % movie_info.id)

@app.route("/import_from_OMDB")
def import_from_OMDB():
	movie_list = dbsession.query(Media).filter_by(omdbLoad=None).limit(10)
	print ">>> Starting update"
	updated = 0
	for movie in movie_list:
		print "Updating... %d %s (%d)" % (movie.id, movie.title, movie.year)
		populate_movie_from_OMDB(movie)
		updated = updated + 1
	print ">>> Updated %d movies" % updated
	return redirect ("/import_from_OMDB")

# Takes a Media object as input and refreshes its data from the OMDB API
def populate_movie_from_OMDB(movie_info):
	# query API for move title using OMDB API parameters
	# Exception Handler: do this where you expect a failure
	title = movie_info.title #urllib.quote_plus(movie_info.title)
	res = omdb.request(t=title, y=movie_info.year, r='JSON', apikey="e5b6d27b", tomatoes="true")
	print "fetching [%s]" % title
 
	try:
		json_content = json.loads(res.content)
	# do this if failure
	except: 
		print res.content
		return

	# updates a column with datetime stamp
	movie_info.omdbLoad = datetime.datetime.now()

	# fetch attributes of json content to pass to movie_info object
	poster = check_api_result(json_content, 'Poster')
	if poster:
		movie_info.poster = poster
	imdbRating = check_api_result(json_content, 'imdbRating')
	if imdbRating:
		movie_info.imdbRating = float(imdbRating)
	imdbID = check_api_result(json_content, 'imdbID')
	if imdbID:
		movie_info.imdbID = imdbID
		movie_info.imdbURL = "http://www.imdb.com/title/%s" % imdbID
	runtime = check_api_result(json_content, 'Runtime')
	if runtime:
		movie_info.runtime = runtime.replace(' min', '')
	director = check_api_result(json_content, 'Director')
	if director:
		movie_info.director = director
	actors = check_api_result(json_content, 'Actors')
	if actors:
		movie_info.actors = actors
	tomatoMeter = check_api_result(json_content, 'tomatoMeter')
	if tomatoMeter:
		movie_info.tomatoMeter = int(tomatoMeter)
	tomatoUserRating = check_api_result(json_content, 'tomatoUserRating')
	if tomatoUserRating:
		movie_info.tomatoUserRating = float(tomatoUserRating)
	tomatoUserMeter = check_api_result(json_content, 'tomatoUserMeter')
	if tomatoUserMeter:
		movie_info.tomatoUserMeter = int(tomatoUserMeter)
	mpaa_rating = check_api_result(json_content, 'Rated')
	if mpaa_rating:
		movie_info.mpaa_rating = mpaa_rating
	metascore = check_api_result(json_content, 'Metascore')
	if metascore:
		movie_info.metascore = int(metascore)
	shortPlot = check_api_result(json_content, 'Plot')
	if shortPlot:
		movie_info.shortPlot = shortPlot

	dbsession.add(movie_info)
	dbsession.commit()

def check_api_result(json_content, field):
	if field in json_content and json_content[field] != 'N/A':
		return json_content[field]
	else:
		return None

if __name__ == '__main__':
	# starts the built-in web server on port 5000
	app.run(debug = True)