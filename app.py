import os
from flask_cors import CORS
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import time
import re
import random
from datetime import datetime, timedelta
from PIL import Image
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
CORS(app)

# --- AYARLAR ---
app.config['SECRET_KEY'] = 'ozel_anahtar_buraya'

# --- 🐘 POSTGRESQL BAĞLANTISI ---
# Render üzerindeki DATABASE_URL'i okur, yoksa yerel sqlite açar
uri = os.getenv("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///mysite.db'

app.config['UPLOAD_FOLDER'] = '/tmp' 
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

# --- ☁️ CLOUDINARY AYARLARI ---
cloudinary.config(
  cloud_name = "dwkm1gjsc",
  api_key = "326246576888513",
  api_secret = "MgWuIddS2CZHmjdOqubHuLR6sC4",
  secure = True
)

# --- ❤️ TARİH AYARI ---
RELATIONSHIP_START = datetime(2025, 1, 28) 

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# ... (Modeller ve Rotalar kodun geri kalanıyla aynı kalacak, sadece yukarıdaki config kısımları değişti) ...
# (Lütfen kendi kodundaki modelleri ve rotaları bu satırın altına eklemeyi unutma)
