import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change_this_secret"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "postgresql://neondb_owner:npg_w6pRD0WnMBQJ@ep-cold-scene-af3vj731-pooler.c-2.us-west-2.aws.neon.tech/kanakk_db?sslmode=require&channel_binding=require"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    