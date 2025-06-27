from bs4 import BeautifulSoup
import requests
import os
import mysql.connector
from typing import Literal, List
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from typing import Union, List
from pathlib import Path
import pandas as pd
from src.config.configs import *


load_dotenv()

class MySQLConnector():
    def __init__(self, host:str = MYSQL_URL, 
                 port:int = MYSQL_PORT,
                 user:str = MYSQL_NAME, 
                 passwd :str = MYSQL_PASSWORD,
                 database:str = MYSQL_DB):
        self.mydb = mysql.connector.connect(
        host=host,
        user=user,
        password=passwd,
        port= port,
        )
        self.database = database
        self.cursor = self.mydb.cursor()

        self.cursor.execute(f"SHOW DATABASES")

        db_list = [db[0] for db in self.cursor.fetchall()]
        if self.database not in db_list:
            self.cursor.execute(f"CREATE DATABASE {self.database} CHARACTER SET utf8 COLLATE utf8_general_ci")
        self.mydb.close()
        
        self.mydb = mysql.connector.connect(
        host=host,
        user=user,
        password=passwd,
        port= port,
        database = self.database
        )

    def check_exists_table(self, table_name:str):

        mycursor = self.mydb.cursor()

        mycursor.execute("SHOW TABLES")
        tables = mycursor.fetchall()
        result = (table_name,) in tables
        mycursor.close()
        return result

    def create_table(self, table_name):
        with open(f"./src/database/schema/{table_name}.txt") as f:
            create_table_query = " ".join([line.strip() for line in f.readlines()])
        if self.check_exists_table(table_name=table_name):
            logger.warning("Table is exist.")
            return 
        try:
            
            mycursor = self.mydb.cursor()
            mycursor.execute(create_table_query)
            mycursor.close()
            logger.info("Create table {} success!", table_name)
        except mysql.connector.Error as err:
            logger.error(f"Error in create table: {err}")
    
    def insert_to_web_pages(self,table_name:str ,url:str, html:str, title:str):
        try:
            query = f"INSERT INTO {table_name} (url, html, \
            title) VALUE (%s, %s, %s)"
            # values = [d.values() for d in data]
            mycursor = self.mydb.cursor()
            mycursor.execute(query, (url, html, title))
            self.mydb.commit()
        except mysql.connector.Error as err:
            logger.error(f"Error when insert to table: {err}")
    

    def custom_query(self, query:str, data=None, cursor_template = None):
        try:
            mycursor = self.mydb.cursor()
            if data is not None:
                mycursor.execute(query, data)
            else:
                mycursor.execute(query)
            myresult = mycursor.fetchall()
            return myresult
        except mysql.connector.Error as err:
            logger.error(f"Error when query to database: {err}")
            return None

    
    def update_medicine(self, id:str, assign:str):
        try:
            query = f"""
                INSERT INTO medicine_detailt (id, assign) 
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                assign = VALUES(assign);
                """
            mycursor = self.mydb.cursor()
            mycursor.execute(query, (id, assign))
            self.mydb.commit()
        except mysql.connector.Error as err:
            logger.error(f"Error when insert to table: {err}, {id}, {assign}")

    def insert_to_medicine_detail(self, detail_data):
        try:
            query = f"INSERT INTO medicine_detailt (name, type, specification, assign, short_description, \
                ingredient, usesage, dosage, adverseEffect, careful, preservation, price, image_url, note, FAQ, rate, QA) \
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
            mycursor = self.mydb.cursor()
            mycursor.execute(query, detail_data)
            self.mydb.commit()
        except mysql.connector.Error as err:
            logger.error(f"Error when insert to table: {err}")
            logger.error(f"detail_data: {detail_data}")

    def insert_to_chunks(self,data:List[List[str]]):
        try:
            query = "INSERT INTO chunks (text, metadata) VALUE (%s, %s)"
            # values = [d.values() for d in data]
            mycursor = self.mydb.cursor()
            mycursor.executemany(query, data)
            self.mydb.commit()
        except mysql.connector.Error as err:
            logger.error(f"Error when insert to table: {err}")
    
    def export_data(self, table_name:str ,file_path: Union[str, Path]):
        try:
            query = f"SELECT * FROM {table_name}"

            data = pd.read_sql(query, self.mydb)
            data.to_csv(file_path, index=False, encoding="utf-8-sig")

            logger.success("Saved all your transaction in {}", file_path)
        
        except Exception as err:
            logger.error(f"Error when export table to csv: {err}")
