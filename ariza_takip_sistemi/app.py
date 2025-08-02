import os
import csv
import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
CSV_FILE = 'ARIZALAR.csv'

# --- Admin Paneli için Basit Şifre Koruması ---
def check_auth(username, password):
    return username == 'admin' and password == '12345'

def authenticate():
    """Kullanıcıdan kimlik bilgisi isteyen bir 401 yanıtı gönderir."""
    return Response(
        'Giriş yapılamadı. Bu alana erişim için yetkilendirme gerekli.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

# --- CSV Okuma ve Yazma Fonksiyonları ---
def read_csv_data():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_csv_data(data, fieldnames):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

# --- ANA ROTALAR ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/issues')
def get_issues():
    issues_data = read_csv_data()
    issues_list = []
    for row in issues_data:
        try:
            coords = row.get('Koordinatlar', '0,0').split(',')
            issue = {
                'id': int(row['Veri No']),
                'issue_no': int(row.get('No', 0)),
                'neighborhood': row['Mahalle İsmi'],
                'link': row['Linkler'],
                'latitude': float(coords[0].strip()),
                'longitude': float(coords[1].strip()),
                'before_photo_path': row.get('Before_Photo_Path'),
                'after_photo_path': row.get('After_Photo_Path'),
                'before_photo_timestamp': row.get('Before_Photo_Timestamp'),
                'after_photo_timestamp': row.get('After_Photo_Timestamp')
            }
            issues_list.append(issue)
        except (ValueError, KeyError, IndexError):
            continue
            
    neighborhood = request.args.get('neighborhood')
    if neighborhood:
        issues_list = [i for i in issues_list if i['neighborhood'] == neighborhood]
        
    return jsonify(issues_list)

# CSV'deki tüm benzersiz mahalle adlarını döndürür.
@app.route('/neighborhoods')
def get_neighborhoods():
    issues_data = read_csv_data()
    neighborhoods = sorted(list(set(row['Mahalle İsmi'] for row in issues_data if 'Mahalle İsmi' in row)))
    return jsonify(neighborhoods)

# Fotoğraf yüklemelerini işler ve CSV'yi günceller.
@app.route('/upload/<int:id>', methods=['POST'])
def upload_photos(id):
    data = read_csv_data()
    target_row = None
    fieldnames = []
    if data:
        fieldnames = data[0].keys()
        # Gerekli sütunlar yoksa ekle
        for col in ['Before_Photo_Path', 'After_Photo_Path', 'Before_Photo_Timestamp', 'After_Photo_Timestamp']:
            if col not in fieldnames:
                fieldnames.append(col)

    for row in data:
        if int(row['Veri No']) == id:
            target_row = row
            break
            
    if not target_row:
        return jsonify({'success': False, 'error': 'Arıza bulunamadı'}), 404

    try:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        os.makedirs('static/photos/before', exist_ok=True)
        os.makedirs('static/photos/after', exist_ok=True)
        
        if 'before' in request.files and request.files['before'].filename != '':
            before_file = request.files['before']
            ext = os.path.splitext(before_file.filename)[1]
            path = f"photos/before/{id}{ext}"
            before_file.save(os.path.join('static', path))
            target_row['Before_Photo_Path'] = path
            target_row['Before_Photo_Timestamp'] = current_time

        if 'after' in request.files and request.files['after'].filename != '':
            after_file = request.files['after']
            ext = os.path.splitext(after_file.filename)[1]
            path = f"photos/after/{id}{ext}"
            after_file.save(os.path.join('static', path))
            target_row['After_Photo_Path'] = path
            target_row['After_Photo_Timestamp'] = current_time

        write_csv_data(data, fieldnames)
        return jsonify({'success': True, 'message': 'Fotoğraflar yüklendi.'})
    except Exception as e:
        print(f"Upload hatası ID {id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- BASİT ADMIN PANELİ ROTALARI ---
@app.route('/admin')
def admin_panel():
    return render_template('admin.html', issues=read_csv_data())

@app.route('/add', methods=['POST'])
def add_issue():
    """Yeni arıza ekler."""
    data = read_csv_data()
    # Yeni ID'yi belirle
    new_id = max([int(row['Veri No']) for row in data]) + 1 if data else 1
    
    new_issue = {
        'Veri No': new_id,
        'No': request.form.get('issue_no', ''),
        'Mahalle İsmi': request.form.get('neighborhood', 'Bilinmiyor'),
        'Koordinatlar': request.form.get('coordinates', '0,0'),
        'Linkler': request.form.get('link', ''),
        'Before_Photo_Path': '',
        'After_Photo_Path': '',
        'Before_Photo_Timestamp': '',
        'After_Photo_Timestamp': ''
    }
    
    fieldnames = data[0].keys() if data else new_issue.keys()
    data.append(new_issue)
    write_csv_data(data, fieldnames)
    
    return redirect(url_for('admin_panel'))

@app.route('/delete/<int:id>')
def delete_issue(id):
    """Bir arızayı siler."""
    data = read_csv_data()
    if not data:
        return redirect(url_for('admin_panel'))

    fieldnames = data[0].keys()
    # Silinecek ID dışındaki tüm verileri yeni bir listeye al
    data_to_keep = [row for row in data if int(row['Veri No']) != id]
    
    # Eğer veri silindiyse dosyayı yeniden yaz
    if len(data_to_keep) < len(data):
        write_csv_data(data_to_keep, fieldnames)
        
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')