import os
from dotenv import load_dotenv


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POSTS_PER_PAGE = 8
    MAIL_SERVER = "smtp.googlemail.com"
    MAIL_PORT = "587"
    MAIL_USE_TLS = 1
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or "enter email"
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or "enter pass"
    ADMINS = os.environ.get("ADMINS") or "enter admin"
    ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL")
