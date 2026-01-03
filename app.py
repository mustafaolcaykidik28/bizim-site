# --- EN BAŞA PROXY ZORLAMASI EKLİYORUZ ---
import os

# PythonAnywhere ücretsiz hesapları için proxy ayarını işletim sistemi seviyesinde yapıyoruz
os.environ["http_proxy"] = "http://proxy.server:3128"
os.environ["https_proxy"] = "http://proxy.server:3128"

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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mysite.db'
app.config['UPLOAD_FOLDER'] = '/tmp' 
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

# --- ☁️ CLOUDINARY AYARLARI ---
# Hem environment değişkeni hem de config ile çift dikiş atıyoruz
import cloudinary

# BURAYI KOPYALA VE ESKİSİNİN YERİNE YAPIŞTIR
cloudinary.config(
  cloud_name = "olcay",
  api_key = "326246576888513",
  api_secret = "MgWuIddS2CZHmjdOqubHuLR6sC4",
  secure = True
)

# --- ❤️ TARİH AYARI ---
RELATIONSHIP_START = datetime(2025, 1, 28) 

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# --- TABLOLAR & MODELLER ---
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
    except:
        pass
    match_compact = re.search(r'(20\d{2})(\d{2})(\d{2})', filename)
    if match_compact:
        return f"{match_compact.group(1)}-{match_compact.group(2)}-{match_compact.group(3)}"
    match_hyphen = re.search(r'(20\d{2})-(\d{2})-(\d{2})', filename)
    if match_hyphen:
        return f"{match_hyphen.group(1)}-{match_hyphen.group(2)}-{match_hyphen.group(3)}"
    
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')

# --- API ROTASI ---
@app.route('/api/home_data')
def api_home_data():
    today = datetime.now()
    delta = today - RELATIONSHIP_START
    return jsonify({
        'days_together': delta.days,
        'start_date': RELATIONSHIP_START.strftime('%Y-%m-%d'),
        'message_title': 'Yıldönümümüz Kutlu Olsun Aşkım ❤️',
        'message_body': 'Birlikte geçirdiğimiz her an çok değerli...'
    })

@app.route('/api/memories/<date_str>')
def api_get_memories(date_str):
    memories = Memory.query.filter_by(date_str=date_str).all()
    notes = Note.query.filter_by(date_str=date_str).all()
    
    memory_list = []
    for m in memories:
        memory_list.append({
            'id': m.id,
            'url': m.filename,
            'type': m.media_type,
            'description': m.description,
            'is_favorite': m.is_favorite
        })

    note_list = []
    for n in notes:
        note_list.append({
            'id': n.id,
            'content': n.content,
            'is_favorite': n.is_favorite
        })
        
    return jsonify({'memories': memory_list, 'notes': note_list})

@app.route('/api/bucket_list')
def api_get_bucket_list():
    items = BucketList.query.order_by(BucketList.is_done, BucketList.id.desc()).all()
    data = []
    for item in items:
        data.append({
            'id': item.id,
            'content': item.content,
            'is_done': item.is_done
        })
    return jsonify(data)

@app.route('/api/pins')
def api_get_pins():
    pins = MapPin.query.all()
    pin_data = []
    for pin in pins:
        pin_data.append({
            'date_str': pin.date_str,
            'lat': pin.lat,
            'lng': pin.lng,
            'place_name': pin.place_name
        })
    return jsonify(pin_data)

# --- WEB SİTESİ ROTALARI ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_date = request.form.get('date')
        return redirect(url_for('view_date', date_str=selected_date))
    today = datetime.now()
    delta = today - RELATIONSHIP_START
    days_together = delta.days
    return render_template('index.html', days_together=days_together)

@app.route('/bucket_list')
def bucket_list_page():
    bucket_items = BucketList.query.order_by(BucketList.is_done, BucketList.id.desc()).all()
    return render_template('bucket_list.html', bucket_items=bucket_items)

@app.route('/add_bucket_item', methods=['POST'])
def add_bucket_item():
    content = request.form.get('content')
    if content:
        new_item = BucketList(content=content)
        db.session.add(new_item)
        db.session.commit()
    return redirect(url_for('bucket_list_page'))

@app.route('/toggle_bucket_item/<int:id>')
def toggle_bucket_item(id):
    item = BucketList.query.get_or_404(id)
    item.is_done = not item.is_done 
    db.session.commit()
    return redirect(url_for('bucket_list_page'))

@app.route('/delete_bucket_item/<int:id>')
def delete_bucket_item(id):
    item = BucketList.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('bucket_list_page'))

@app.route('/view/<date_str>')
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
        prev_date = date_str
        next_date = date_str
        pretty_date = date_str
    return render_template('view_date.html', memories=memories, notes=notes, albums=all_albums, location=location, date_str=date_str, pretty_date=pretty_date, prev_date=prev_date, next_date=next_date)

@app.route('/save_memory_comment', methods=['POST'])
def save_memory_comment():
    memory_id = request.form.get('memory_id')
    comment = request.form.get('comment')
    memory = Memory.query.get_or_404(memory_id)
    memory.description = comment
    db.session.commit()
    return redirect(request.referrer)

@app.route('/toggle_favorite/<int:id>', methods=['POST'])
def toggle_favorite(id):
    memory = Memory.query.get_or_404(id)
    memory.is_favorite = not memory.is_favorite
    db.session.commit()
    return redirect(request.referrer)

@app.route('/toggle_note_favorite/<int:id>', methods=['POST'])
def toggle_note_favorite(id):
    note = Note.query.get_or_404(id)
    note.is_favorite = not note.is_favorite
    db.session.commit()
    return redirect(request.referrer)

@app.route('/favorites')
def favorites_page():
    fav_memories = Memory.query.filter_by(is_favorite=True).all()
    fav_notes = Note.query.filter_by(is_favorite=True).all()
    return render_template('favorites.html', memories=fav_memories, notes=fav_notes)

@app.route('/albums')
def albums_page():
    albums = Album.query.all()
    return render_template('albums.html', albums=albums)

@app.route('/create_album', methods=['POST'])
def create_album():
    name = request.form.get('name')
    file = request.files.get('cover_image')
    cover_link = None
    
    if file and allowed_file(file.filename):
        # Kapak fotoğrafını da buluta yüklüyoruz
        upload_result = cloudinary.uploader.upload(file, resource_type="auto")
        cover_link = upload_result['secure_url']
        
    new_album = Album(name=name, cover_image=cover_link)
    db.session.add(new_album)
    db.session.commit()
    return redirect(url_for('albums_page'))

@app.route('/album/<int:id>')
def view_album(id):
    album = Album.query.get_or_404(id)
    return render_template('view_album.html', album=album)

@app.route('/add_to_album', methods=['POST'])
def add_to_album():
    memory_id = request.form.get('memory_id')
    album_id = request.form.get('album_id')
    memory = Memory.query.get(memory_id)
    album = Album.query.get(album_id)
    if memory and album:
        if memory not in album.memories:
            album.memories.append(memory)
            db.session.commit()
    return redirect(request.referrer)

# --- TEKLİ YÜKLEME ---
@app.route('/upload_manual', methods=['POST'])
def upload_manual():
    date_str = request.form.get('target_date')
    file = request.files.get('file')
    if file and allowed_file(file.filename):
        try:
            upload_result = cloudinary.uploader.upload(file, resource_type="auto")
            cloud_url = upload_result['secure_url']
            
            m_type = 'video' if file.filename.lower().endswith(('mp4', 'mov', 'avi', 'm4v')) else 'image'
            new_memory = Memory(date_str=date_str, filename=cloud_url, media_type=m_type)
            db.session.add(new_memory)
            db.session.commit()
        except Exception as e:
            print(f"Tekli Yükleme Hatası: {e}")
            pass
    return redirect(url_for('view_date', date_str=date_str))

# --- TOPLU YÜKLEME (AKILLI) ---
@app.route('/bulk_upload', methods=['POST'])
def bulk_upload():
    files = request.files.getlist('files')
    for file in files:
        if file.filename == '' or not allowed_file(file.filename): continue
        try:
            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_path)
            
            # Tarihi bul
            detected_date = get_date_from_file(temp_path, filename)
            
            # Buluta yükle
            upload_result = cloudinary.uploader.upload(temp_path, resource_type="auto")
            cloud_url = upload_result['secure_url']
            
            m_type = 'video' if filename.lower().endswith(('mp4', 'mov', 'avi', 'm4v')) else 'image'
            new_memory = Memory(date_str=detected_date, filename=cloud_url, media_type=m_type)
            db.session.add(new_memory)
            
            os.remove(temp_path)
            
        except Exception as e:
            print(f"Toplu Yükleme Hatası: {e}")
            pass
            
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_memory(id):
    memory_to_delete = Memory.query.get_or_404(id)
    db.session.delete(memory_to_delete)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/save_note', methods=['POST'])
def save_note():
    date_str = request.form.get('date_str')
    content = request.form.get('note_content')
    if content:
        new_note = Note(date_str=date_str, content=content)
        db.session.add(new_note)
        db.session.commit()
    return redirect(url_for('view_date', date_str=date_str))

@app.route('/delete_note/<int:id>', methods=['POST'])
def delete_note(id):
    note = Note.query.get_or_404(id)
    date_str = note.date_str
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('view_date', date_str=date_str))

@app.route('/random_memory')
def random_memory():
    all_memories = Memory.query.all()
    if not all_memories:
        return redirect(url_for('index'))
    random_mem = random.choice(all_memories)
    return redirect(url_for('view_date', date_str=random_mem.date_str))

@app.route('/save_location', methods=['POST'])
def save_location():
    date_str = request.form.get('date_str')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    place_name = request.form.get('place_name')
    if date_str and lat and lng:
        existing_pin = MapPin.query.filter_by(date_str=date_str).first()
        if existing_pin:
            existing_pin.lat = float(lat)
            existing_pin.lng = float(lng)
            existing_pin.place_name = place_name
        else:
            new_pin = MapPin(date_str=date_str, lat=float(lat), lng=float(lng), place_name=place_name)
            db.session.add(new_pin)
        db.session.commit()
    return redirect(url_for('view_date', date_str=date_str))

@app.route('/delete_location', methods=['POST'])
def delete_location():
    date_str = request.form.get('date_str')
    pin = MapPin.query.filter_by(date_str=date_str).first()
    if pin:
        db.session.delete(pin)
        db.session.commit()
    return redirect(url_for('view_date', date_str=date_str))

@app.route('/map')
def map_page():
    return render_template('map.html')

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)

