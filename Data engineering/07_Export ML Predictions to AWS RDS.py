# Databricks notebook source
import pandas as pd
from sqlalchemy import create_engine

pdf = spark.table("workspace.gold.hcp_ml_engagement_scores").toPandas()

pdf.columns = pdf.columns.str.lower()

DATABASE_URL = "postgresql+psycopg2://postgres:Hemanth1139@hcp-engagement-db.c580gw4eiq07.ap-south-1.rds.amazonaws.com:5432/postgres"
engine = create_engine(DATABASE_URL)

pdf.to_sql('ml_predictions', engine, if_exists='append', index=False)

print(f"Successfully uploaded {len(pdf)} predictions to RDS!")
