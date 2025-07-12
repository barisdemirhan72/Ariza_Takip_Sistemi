from flask import Flask, render_template, request, redirect, url_for, jsonify
import csv
import os
import datetime

app = Flask(__name__)

def read_csv():
    issues = []
    try:
        with open('FİNAL MAHALLE.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    coords = row['Koordinatlar'].split(',')
                    latitude = float(coords[0].strip())
                    longitude = float(coords[1].strip())
                    issue = {
                        'id': int(row['Veri No']),
                        'issue_no': int(row.get('No', 0)),
                        'neighborhood': row['Mahalle İsmi'],
                        'link': row['Linkler'],
                        'latitude': latitude,
                        'longitude': longitude,
                        'before_photo_path': row.get('Önceki Fotoğraf Yolu', None),
                        'after_photo_path': row.get('Sonraki Fotoğraf Yolu', None),
                        'before_photo_timestamp': row.get('Arıza Yüklenme Saati', None),
                        'after_photo_timestamp': row.get('Arıza Giderilme Saati', None)
                    }
                    issues.append(issue)
                except (KeyError, ValueError, IndexError):
                    print(f"Veri hatası, satır atlanıyor: {row}")
                    continue
    except FileNotFoundError:
        print("Hata: FİNAL MAHALLE.csv dosyası bulunamadı!")
        return []
    except Exception as e:
        print(f"CSV okuma hatası: {e}")
        return []
    return issues

def update_csv(id, before_path=None, after_path=None, before_timestamp=None, after_timestamp=None):
    try:
        with open('FİNAL MAHALLE.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
            if 'Before_Photo_Path' not in fieldnames:
                fieldnames += ['Before_Photo_Path', 'After_Photo_Path', 'Before_Photo_Timestamp', 'After_Photo_Timestamp']
        with open('FİNAL MAHALLE.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                if int(row['Veri No']) == id:
                    if before_path:
                        row['Before_Photo_Path'] = before_path
                    if after_path:
                        row['After_Photo_Path'] = after_path
                    if before_timestamp:
                        row['Before_Photo_Timestamp'] = before_timestamp
                    if after_timestamp:
                        row['After_Photo_Timestamp'] = after_timestamp
                writer.writerow(row)
    except Exception as e:
        print(f"CSV güncelleme hatası: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/issues')
def get_issues():
    neighborhood = request.args.get('neighborhood')
    issues = read_csv()
    if not issues:
        return jsonify({"error": "Veri yüklenemedi, CSV dosyası kontrol edin"}), 500
    if neighborhood:
        issues = [issue for issue in issues if issue['neighborhood'] == neighborhood]
    return jsonify(issues)

@app.route('/neighborhoods')
def get_neighborhoods():
    issues = read_csv()
    if not issues:
        return jsonify({"error": "Veri yüklenemedi, CSV dosyası kontrol edin"}), 500
    neighborhoods = sorted(set(issue['neighborhood'] for issue in issues))
    return jsonify(neighborhoods)

@app.route('/upload/<int:id>', methods=['GET', 'POST'])
def upload_photos(id):
    if request.method == 'POST':
        before_file = request.files.get('before')
        after_file = request.files.get('after')
        os.makedirs('static/photos', exist_ok=True)
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        before_path = None
        after_path = None
        if before_file and before_file.filename != '':
            file_ext = os.path.splitext(before_file.filename)[1]
            before_path = f"photos/{id}_before{file_ext}"
            before_file.save(os.path.join('static', before_path))
        if after_file and after_file.filename != '':
            file_ext = os.path.splitext(after_file.filename)[1]
            after_path = f"photos/{id}_after{file_ext}"
            after_file.save(os.path.join('static', after_path))
        update_csv(id, before_path, after_path, current_time if before_path else None, current_time if after_path else None)
        return redirect(url_for('index'))
    return render_template('upload.html', id=id)

if __name__ == '__main__':
    app.run(debug=True)