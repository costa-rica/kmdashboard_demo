import os
import json

if os.environ.get('TERM_PROGRAM')=='Apple_Terminal':
    with open("/Users/nick/Documents/_config_files/config_km_dashboard20221210_mac.json") as config_file:
        config = json.load(config_file)
elif os.environ.get('USER')=='sanjose':
    with open('/home/sanjose/Documents/environments/config.json') as config_file:
        config = json.load(config_file)
else:
    with open('/home/ubuntu/environments/config.json') as config_file:
        config = json.load(config_file)



class Config:
    SECRET_KEY = config.get('SECRET_KEY_DMR')
    SQLALCHEMY_DATABASE_URI = config.get('SQL_URI')
    MAIL_SERVER = config.get('MAIL_SERVER_GD')
    MAIL_PORT = config.get('MAIL_PORT_GD')
    MAIL_USE_TLS = True
    MAIL_PASSWORD = config.get('MAIL_PASSWORD_TGE')
    MAIL_USERNAME = config.get('MAIL_USERNAME_TGE')
    DEBUG = True
    UPLOADED_FILES_FOLDER = os.path.join(os.path.dirname(__file__), 'static/files')
    UTILITY_FILES_FOLDER = os.path.join(os.path.dirname(__file__), 'static/files_utility')
    QUERIES_FOLDER = os.path.join(os.path.dirname(__file__), 'static/queries')
    FILES_DATABASE = os.path.join(os.path.dirname(__file__), 'static/files_database')
    UPLOADED_TEMP_DATA = os.path.join(os.path.dirname(__file__), 'static/files_temp')
    
    