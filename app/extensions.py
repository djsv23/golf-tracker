from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap5

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
bootstrap = Bootstrap5()
