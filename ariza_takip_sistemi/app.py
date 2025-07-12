from flask import Flask, render_template, request, redirect, url_for, jsonify
import csv
import os

app = Flask(__name__) # Flask uygulamasını başlatır

def read_csv():
    issues = []
    try:
        with open('FİNAL MAHALLE.csv', 'r', encoding='utf-8') as f: # CSV dosyasını UTF-8 ile açar
            reader = csv.DictReader(f) # CSV satırlarını sözlük olarak okur
            for row in reader:
                try:
                    coords = row['Koordinatlar'].split(',') # Koordinatlar sütununu virgülle ayırır
                    latitude = float(coords[0].strip()) # Enlemi float'a çevirir
                    longitude = float(coords[1].strip()) # Boylamı float'a çevirir
                    issue = {
                        'id': int(row['Veri No']), # Arıza ID'sini tamsayıya çevirir
                        'issue_no': int(row.get('No', 0)), # Mahalle arızası numarasını tamsayıya çevirir, eksikse 0 kullanır
                        'neighborhood': row['Mahalle İsmi'], # Mahalle adını alır
                        'link': row['Linkler'], # Google Maps linkini alır
                        'latitude': latitude, # Enlemi kaydeder
                        'longitude': longitude, # Boylamı kaydeder
                        'before_photo_path': None, # Öncesi fotoğrafı için varsayılan None
                        'after_photo_path': None # Sonrası fotoğrafı için varsayılan None
                    }
                    before_path = f"photos/{issue['id']}_before.jpg" # Öncesi fotoğraf yolunu oluşturur
                    after_path = f"photos/{issue['id']}_after.jpg" # Sonrası fotoğraf yolunu oluşturur
                    if os.path.exists(os.path.join('static', before_path)): # Öncesi fotoğrafın varlığını kontrol eder
                        issue['before_photo_path'] = before_path # Varsa yolu kaydeder
                    if os.path.exists(os.path.join('static', after_path)): # Sonrası fotoğrafın varlığını kontrol eder
                        issue['after_photo_path'] = after_path # Varsa yolu kaydeder
                    issues.append(issue) # Arızayı listeye ekler
                except (KeyError, ValueError, IndexError): # Sütun eksikliği veya veri hatası
                    print(f"Veri hatası, satır atlanıyor: {row}") # Hata mesajı yazdırır
                    continue
    except FileNotFoundError: # Dosya bulunamazsa
        print("Hata: FİNAL MAHALLE.csv dosyası bulunamadı!") # Hata mesajı yazdırır
        return [] # Boş liste döndürür
    except Exception as e: # Diğer hatalar
        print(f"CSV okuma hatası: {e}") # Hata mesajı yazdırır
        return [] # Boş liste döndürür
    return issues # Arıza listesini döndürür

@app.route('/')
def index():
    return render_template('index.html') # Ana sayfayı render eder

@app.route('/issues')
def get_issues():
    neighborhood = request.args.get('neighborhood') # Mahalle filtresi alır
    issues = read_csv() # CSV'den arızaları okur
    if not issues: # Veri yoksa
        return jsonify({"error": "Veri yüklenemedi, CSV dosyası kontrol edin"}), 500 # Hata mesajı döndürür
    if neighborhood: # Mahalle filtresi varsa
        issues = [issue for issue in issues if issue['neighborhood'] == neighborhood] # Arızaları filtreler
    return jsonify(issues) # Arızaları JSON olarak döndürür

@app.route('/neighborhoods')
def get_neighborhoods():
    issues = read_csv() # CSV'den arızaları okur
    if not issues: # Veri yoksa
        return jsonify({"error": "Veri yüklenemedi, CSV dosyası kontrol edin"}), 500 # Hata mesajı döndürür
    neighborhoods = sorted(set(issue['neighborhood'] for issue in issues)) # Benzersiz mahalleleri sıralar
    return jsonify(neighborhoods) # Mahalleleri JSON olarak döndürür

@app.route('/upload/<int:id>', methods=['GET', 'POST'])
def upload_photos(id):
    if request.method == 'POST': # POST isteği ise
        before_file = request.files.get('before') # Öncesi fotoğrafı alır
        after_file = request.files.get('after') # Sonrası fotoğrafı alır
        os.makedirs('static/photos', exist_ok=True) # Fotoğraf klasörünü oluşturur
        if before_file and before_file.filename != '': # Öncesi fotoğraf varsa
            file_ext = os.path.splitext(before_file.filename)[1] # Dosya uzantısını alır
            filename = f"{id}_before{file_ext}" # Dosya adını oluşturur
            before_file.save(os.path.join('static/photos', filename)) # Dosyayı kaydeder
        if after_file and after_file.filename != '': # Sonrası fotoğraf varsa
            file_ext = os.path.splitext(after_file.filename)[1] # Dosya uzantısını alır
            filename = f"{id}_after{file_ext}" # Dosya adını oluşturur
            after_file.save(os.path.join('static/photos', filename)) # Dosyayı kaydeder
        return redirect(url_for('index')) # Ana sayfaya yönlendirir
    return render_template('upload.html', id=id) # Yükleme sayfasını render eder

if __name__ == '__main__':
    print(read_csv()[:5]) # İlk 5 arızayı konsola yazdırır
    app.run(debug=True) # Flask uygulamasını hata ayıklama modunda başlatır