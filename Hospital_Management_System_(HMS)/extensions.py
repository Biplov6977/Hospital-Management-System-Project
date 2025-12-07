from flask_sqlalchemy import SQLAlchemy

# shared DB instance used by app and models to avoid circular imports
db = SQLAlchemy()
