import logging
import os
import configparser
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO)

Base = declarative_base()

DATA_DIRECTORY = './data'
DB_NAME = os.path.join(DATA_DIRECTORY, 'watchru.db')
CONFIG_FILENAME = os.path.join(DATA_DIRECTORY, 'config.ini')

config = configparser.ConfigParser()
config.read(CONFIG_FILENAME)
sections = {}
for x in config['Sections']:
    sections[x] = config['Sections'][x]


if not os.path.exists(DATA_DIRECTORY):
    os.makedirs(DATA_DIRECTORY)

BOT_API_TOKEN = config['Telegram']['BOT_API_TOKEN']
BOT_ADMIN_PASSWORD = config['Telegram']['BOT_ADMIN_PASSWORD']

LOGIN = config['Forum']['LOGIN']
PASSWORD = config['Forum']['PASSWORD']

KEY = config['Security']['KEY'][:32]

engine = create_engine('sqlite+pysqlcipher://:{0}@/{1}?cipher=aes-256-cfb&kdf_iter=64000'.format(KEY, DB_NAME), echo=False)
#engine = create_engine('sqlite:///{0}'.format(DB_NAME), echo=False)

Session = sessionmaker(bind=engine)

TIME_SLEEP_SENDER = 1 * 60
TIME_QUANT = 10 * 60

