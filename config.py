import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET KEY') or 'microblogtest'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POSTS_PER_PAGE = 5
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = '587'
    MAIL_USE_TLS = 1
    MAIL_USERNAME = 'enter email'
    MAIL_PASSWORD = 'enter pass'
    ADMINS = ['enter admin']
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL') #http://localhost:9200
    