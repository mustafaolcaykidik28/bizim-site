import os
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import time
import re
import random
from PIL import Image
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
CORS(app)

# --- GÜVENLİK VE OTURUM AYARLARI ---
app.config['SECRET_KEY'] = 'cok_gizli_ask_anahtari_99'
# Giriş yapanı hatırlaması için oturum ömrünü 365 gün yapıyoruz
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)

# --- GİRİŞ BİLGİLERİ ---
USER_LOGIN = "Sudis"
USER_PASS = "280126"

# --- 🐘 VERİTABANI BAĞLANTISI ---
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///mysite.db'
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

db = SQLAlchemy(app)

# --- KİLİT MEKANİZMASI (login_required) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- MODELLER ---
album_memories = db.Table('album_memories',
    db.Column('album_id', db.Integer, db.ForeignKey('album.id'), primary_key=True),
    db.Column('memory_id', db.Integer, db.ForeignKey('memory.id'), primary_key=True)
)

class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(10), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    media_type = db.Column(db.String(10), nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(500), nullable=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)

class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cover_image = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    memories = db.relationship('Memory', secondary=album_memories, lazy='subquery',
        backref=db.backref('albums', lazy=True))

class MapPin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(10), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    place_name = db.Column(db.String(100), nullable=True)

class BucketList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    is_done = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# --- GİRİŞ VE ÇIKIŞ ROTALARI ---
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USER_LOGIN and password == USER_PASS:
            session.permanent = True # Tarayıcıyı kapatınca unutma (365 gün sakla)
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="Hatalı Kullanıcı Adı veya Şifre!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# --- WEB SİTESİ ROTALARI (HEPSİ KİLİTLİ) ---

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        selected_date = request.form.get('date')
        return redirect(url_for('view_date', date_str=selected_date))
    today = datetime.now()
    delta = today - RELATIONSHIP_START
    days_together = delta.days
    return render_template('index.html', days_together=days_together)

@app.route('/view/<date_str>')
@login_required
def view_date(date_str):
    memories = Memory.query.filter_by(date_str=date_str).all()
    notes = Note.query.filter_by(date_str=date_str).all()
    all_albums = Album.query.all()
    location = MapPin.query.filter_by(date_str=date_str).first()
    try:
        current_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        prev_date = (current_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
        next_date = (current_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
        pretty_date = current_date_obj.strftime('%d %B %Y')
    except:
        prev_date, next_date, pretty_date = date_str, date_str, date_str
    return render_template('view_date.html', memories=memories, notes=notes, albums=all_albums, location=location, date_str=date_str, pretty_date=pretty_date, prev_date=prev_date, next_date=next_date)

@app.route('/favorites')
@login_required
def favorites_page():
    fav_memories = Memory.query.filter_by(is_favorite=True).all()
    fav_notes = Note.query.filter_by(is_favorite=True).all()
    return render_template('favorites.html', memories=fav_memories, notes=fav_notes)

@app.route('/albums')
@login_required
def albums_page():
    albums = Album.query.all()
    return render_template('albums.html', albums=albums)

@app.route('/album/<int:id>')
@login_required
def view_album(id):
    album = Album.query.get_or_404(id)
    return render_template('view_album.html', album=album)

@app.route('/bucket_list')
@login_required
def bucket_list_page():
    bucket_items = BucketList.query.order_by(BucketList.is_done, BucketList.id.desc()).all()
    return render_template('bucket_list.html', bucket_items=bucket_items)

@app.route('/map')
@login_required
def map_page():
    return render_template('map.html')

# --- DİĞER FONKSİYONLAR (YÜKLEME, SİLME VS.) ---
# Bunlar da kilitli olmalı ki dışarıdan API ile veri gönderilemesin

@app.route('/upload_manual', methods=['POST'])
@login_required
def upload_manual():
    date_str = request.form.get('target_date')
    file = request.files.get('file')
    if file:
        try:
            upload_result = cloudinary.uploader.upload(file, resource_type="auto")
            cloud_url = upload_result['secure_url']
            m_type = 'video' if file.filename.lower().endswith(('mp4', 'mov', 'avi', 'm4v')) else 'image'
            new_memory = Memory(date_str=date_str, filename=cloud_url, media_type=m_type)
            db.session.add(new_memory)
            db.session.commit()
        except Exception: pass
    return redirect(url_for('view_date', date_str=date_str))

@app.route('/save_note', methods=['POST'])
@login_required
def save_note():
    date_str = request.form.get('date_str')
    content = request.form.get('note_content')
    if content:
        new_note = Note(date_str=date_str, content=content)
        db.session.add(new_note)
        db.session.commit()
    return redirect(url_for('view_date', date_str=date_str))

# (Yardımcı Fonksiyonlar)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'm4v'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_date_from_file(file_path, filename):
    try:
        if filename.lower().endswith(('jpg', 'jpeg', 'png')):
            image = Image.open(file_path)
            exif_data = image._getexif()
            if exif_data:
                date_str = exif_data.get(36867)
                if date_str:
                    dt_obj = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                    return dt_obj.strftime('%Y-%m-%d')
    except: pass
    match = re.search(r'(20\d{2})(\d{2})(\d{2})', filename)
    if match: return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d')

# --- DİĞER API VE SİLME ROTALARI ---
@app.route('/api/home_data')
@login_required
def api_home_data():
    today = datetime.now()
    delta = today - RELATIONSHIP_START
    return jsonify({'days_together': delta.days})

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_memory(id):
    m = Memory.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    return redirect(request.referrer)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
