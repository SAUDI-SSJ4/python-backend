from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# No need to import models here - they will be registered automatically when imported 