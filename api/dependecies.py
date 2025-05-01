# Defines dependencies used by the routers
from sqlmodel import Session, create_engine
import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import logging
import boto3



#Create Logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)



#Load env values in Local & Prod
RUNNING_IN_AWS = os.getenv("AWS_EXECUTION_ENV") is not None

if not RUNNING_IN_AWS:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
COGNITO_REGION = os.getenv("COGNITO_REGION")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
COGNITO_PUBLIC_KEY_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_REGION}_{COGNITO_USER_POOL_ID}/.well-known/jwks.json"




# Db stuff & Initialize tables
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine) # creates the database tables based on the modelds defined using SQLModel

def get_db():
    with Session(engine) as session:
        yield session



# Verify AWS Cognito JWT using Boto3
cognito_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_cognito_token(token: str = Depends(oauth2_scheme)):

    try:
        response = cognito_client.get_user(AccessToken=token)
        logger.info(f"Token successfully validated. User: {response}")
        return response  

    except Exception as e:
        logger.exception(f"Unexpected error while verifying token: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error during token validation")
