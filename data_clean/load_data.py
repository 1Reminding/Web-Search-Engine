import os
import json
from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://localhost:27017/')
db = client['nankai_news_datasets']
collection = db['2024_12_01_02_57_18']

for filename in os.listdir(r'C:\Xing\IR\lab4\code\2024_12_01_02_57_18'):
    if filename.endswith('.json'):
        with open(os.path.join(r'C:\Xing\IR\lab4\code\2024_12_01_02_57_18', filename), 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            collection.insert_one(json_data)