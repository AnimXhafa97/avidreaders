import csv
import os

from flask import Flask, session, render_template, request
from flask_session.__init__ import Session
from sqlalchemy import create_engine, exists
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
create_engine.max_overflow = -1
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv", "r")  # needs to be opened during reading csv
    reader = csv.reader(f)
    next(reader)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
               {"isbn": isbn, "title": title, "author": author, "year": year})
        db.commit()

if __name__ == '__main__':
    main()
