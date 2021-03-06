from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Table, Boolean, Column, DateTime, Float, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import scoped_session

ENGINE = None
Session = None

# Create an instance of an engine that stores data in the local directory's
# mysql file. 

engine = create_engine("mysql://root@localhost/vd", echo=False)
session = scoped_session(sessionmaker(bind=engine,
									  autocommit = False,
									  autoflush = False))

# Base class definition. It is simply required for SQLALchemy's magic to work. 
Base = declarative_base()
Base.query = session.query_property()

# association tables
genres = Table('genres_association', Base.metadata,
	Column('genre_id', Integer, ForeignKey('genres.id')),
	Column('media_id', Integer, ForeignKey('media.id'))
)
user_genres = Table('user_genre_assoc', Base.metadata,
	Column('genre_id', Integer, ForeignKey('genres.id')),
	Column('user_id', Integer, ForeignKey('users.id'))
)
user_follows = Table('user_follows_assoc', Base.metadata,
	Column('user_id', Integer, ForeignKey('users.id')),
	Column('follow_id', Integer, ForeignKey('users.id'))
)

# Setting up a Movies class that inherits the Base class.
class Media(Base):
	# Informs SQLAlchemy that instances of this class will be stored in a table named users.
	__tablename__ = "media"

	id = Column(Integer, primary_key=True)
	imdbpyID = Column(Integer, nullable=True)
	title = Column(String(400), nullable=False)
	year = Column(Integer, nullable=True)
	runtime = Column(String(32), nullable=True)
	color = Column(String(32), nullable=True)
	language = Column(String(32), nullable=True)
	country = Column(String(32), nullable=True)
	mpaa_rating = Column(String(256), nullable=True)
	plot = Column(Text, nullable=True)
	budget = Column(String(32), nullable=True)
	gross = Column(String(64), nullable=True)
	taglines = Column(String(256), nullable=True)
	subtitles = Column(String(64), nullable=True)
	kind = Column(String(16), nullable=True)
	actors = Column(Text, nullable=True)
	director = Column(String(64), nullable=True)
	poster = Column(Boolean, nullable=True)
	metascore = Column(Integer, nullable=True)
	imdbRating = Column(Float, nullable=True)
	imdbID = Column(String(64), nullable=True)
	imdbURL = Column(String(256), nullable=True)
	tomatoMeter = Column(Integer, nullable=True)
	tomatoUserMeter = Column(Integer, nullable=True)
	tomatoUserRating = Column(Float, nullable=True)
	shortPlot = Column(Text, nullable=True)
	omdbLoad = Column(DateTime, nullable=True)

	genres = relationship('Genre', secondary=genres,
		backref = backref('media', lazy='dynamic'))

	# replaces large poster with a smaller version
	# def small_poster(self):
	# 	if not self.poster:
	# 		return None
	# 	return self.poster.replace('SX300', 'SX60')

class Genre(Base):
	__tablename__ = "genres"

	id = Column(Integer, primary_key=True)
	genre = Column(String(64), nullable=False)

class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True)
	username = Column(String(64), nullable=False)
	email = Column(String(64), nullable=False)
	password = Column(String(64), nullable=False)
	first_name = Column(String(64), nullable=True)
	last_name = Column(String(64), nullable=True)
	age = Column(Integer, nullable=True)
	gender = Column(Integer, nullable=True)
	zipcode = Column(String(15), nullable=True)
	avg_rating = 0.0

	genres = relationship('Genre', secondary=user_genres,
		order_by='Genre.genre', backref = backref('users', lazy='dynamic'))

	follows = relationship('User', secondary=user_follows,
		primaryjoin=id==user_follows.c.user_id,
        secondaryjoin=id==user_follows.c.follow_id,
        backref='followers')

	def gendername(self):
		if self.gender == 0:
			return "Male"
		elif self.gender == 1:
			return "Female"
		elif self.gender == 2:
			return "Unspecified"

class Rating(Base):
	__tablename__ = "ratings"

	id = Column(Integer, primary_key=True)
	movie_id = Column(Integer, ForeignKey('media.id'))
	user_id = Column(Integer, ForeignKey('users.id'))
	rating = Column(Integer, nullable=True)
	review = Column(Text, nullable=True)
	user = relationship("User", backref=backref("ratings", order_by=id))
	movie = relationship("Media", backref=backref("ratings", order_by=id))
	UniqueConstraint('media_id', 'user_id', name="uniq_rating")

### End class declarations

def connect():
	global ENGINE
	global Session
	ENGINE = create_engine("mysql://root@localhost/vd", echo=True)
	Session = sessionmaker(bind=ENGINE)

	return session 

# Create all tables in the engine. This is equivalent to "Create Table"
# statements in raw SQL.
# Base.metadata.create_all(engine)
