import os
import shutil
import csv
import datetime
from unidecode import unidecode
import re

def normalize_text(text):
    """Metni büyük/küçük harf duyarsız ve boşluksuz hale getirir"""
    text = unidecode(text).lower()
    text = re.sub(r'[^a-z0-9]', '', text)  # Sadece harf ve rakamları tut
    return text

def organize_photos(source_dir, csv_path):
    """Fotoğrafları id_mahalleadi formatında düzenler ve CSV'yi günceller"""
    # Klasörleri oluştur
    os.makedirs('static/photos/before', exist_ok=True)
    os.makedirs('static/photos/after', exist_ok=True)
    
    # CSV'den verileri oku ve mahalle bazında grupla
    issues_by_neighborhood = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Sütun adlarını kontrol et
        if 'Veri No' not in reader.fieldnames:
            raise KeyError("CSV dosyasında 'Veri No' sütunu bulunamadı. Lütfen sütun adlarını kontrol edin.")
        if 'Mahalle İsmi' not in reader.fieldnames:
            raise KeyError("CSV dosyasında 'Mahalle İsmi' sütunu bulunamadı. Lütfen sütun adlarını kontrol edin.")
        if 'No' not in reader.fieldnames:
            raise KeyError("CSV dosyasında 'No' sütunu bulunamadı. Lütfen sütun adlarını kontrol edin.")
        
        for row in reader:
            try:
                neighborhood = row['Mahalle İsmi'].strip()
                # Mahalle ismini normalleştir
                normalized_neighborhood = normalize_text(neighborhood)
                issue_no = int(row['No'])
                veri_no = int(row['Veri No'])
                
                if normalized_neighborhood not in issues_by_neighborhood:
                    issues_by_neighborhood[normalized_neighborhood] = []
                
                issues_by_neighborhood[normalized_neighborhood].append({
                    'veri_no': veri_no,
                    'issue_no': issue_no,
                    'neighborhood': neighborhood,  # Orijinal ismi sakla
                    'before_photo_path': row.get('Before_Photo_Path', ''),
                    'row': row
                })
            except (KeyError, ValueError) as e:
                print(f"Hata: Satır işlenemedi: {row}. Hata: {e}")
    
    # Mahalleleri issue_no'ya göre sırala
    for neighborhood, issues in issues_by_neighborhood.items():
        issues.sort(key=lambda x: x['issue_no'])
    
    # Fotoğrafları işle
    total_processed = 0
    
    # Tüm olası klasör yapılarını destekle
    def collect_photos(path):
        photos = []
        # Dizindeki tüm dosyaları ve alt dizinleri tara
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path) and entry.lower().endswith(('.png', '.jpg', '.jpeg')):
                photos.append(full_path)
            elif os.path.isdir(full_path) and entry.lower() not in ['.', '..']:
                # Alt dizinleri rekürsif olarak tara
                photos.extend(collect_photos(full_path))
        return photos
    
    # Tüm mahalle klasörlerini işle
    for neighborhood_dir in os.listdir(source_dir):
        neighborhood_path = os.path.join(source_dir, neighborhood_dir)
        if not os.path.isdir(neighborhood_path):
            continue
        
        # Mahalle adını normalleştir
        normalized_dir_name = normalize_text(neighborhood_dir)
        
        # CSV'de bu mahalleyi bul
        matched_neighborhood = None
        for csv_neighborhood in issues_by_neighborhood.keys():
            if normalized_dir_name == csv_neighborhood:
                matched_neighborhood = csv_neighborhood
                break
        
        if not matched_neighborhood:
            print(f"Uyarı: CSV'de bulunmayan mahalle: {neighborhood_dir} (normalleştirilmiş: {normalized_dir_name})")
            continue
        
        # Mahalleye ait arızaları al
        issues = issues_by_neighborhood[matched_neighborhood]
        
        # Mahalle klasöründeki tüm fotoğrafları topla (alt klasörler dahil)
        all_photos = collect_photos(neighborhood_path)
        
        # Fotoğrafları dosya adına göre sırala
        all_photos.sort()
        
        # Her arızaya bir fotoğraf ata
        for i, photo_path in enumerate(all_photos):
            if i >= len(issues):
                print(f"Uyarı: {neighborhood_dir} mahallesinde arıza sayısından fazla fotoğraf var")
                break
            
            issue = issues[i]
            
            # Sadece öncesi fotoğrafı eksik olanları güncelle
            if not issue['before_photo_path']:
                # Yeni dosya adını oluştur: veri_no_mahalleadi
                ext = os.path.splitext(photo_path)[1]
                new_name = f"{issue['veri_no']}_{normalize_text(issue['neighborhood'])}{ext}"
                dest_path = os.path.join('static/photos/before', new_name)
                
                # Fotoğrafı kopyala
                shutil.copy2(photo_path, dest_path)
                
                # CSV'yi güncelle
                relative_path = f"photos/before/{new_name}"
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                update_csv(csv_path, issue['veri_no'], 
                         {'Before_Photo_Path': relative_path,
                          'Before_Photo_Timestamp': timestamp})
                
                print(f"İşlendi: {os.path.basename(photo_path)} -> {new_name}")
                total_processed += 1
    
    print(f"\nToplam {total_processed} fotoğraf işlendi ve CSV güncellendi!")

def update_csv(csv_path, id, updates):
    """CSV dosyasını günceller"""
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Eksik sütunları ekle
    for col in ['Before_Photo_Path', 'After_Photo_Path', 'Before_Photo_Timestamp', 'After_Photo_Timestamp']:
        if col not in fieldnames:
            fieldnames.append(col)
    
    # Güncellemeleri uygula
    for row in rows:
        if int(row['Veri No']) == id:
            for key, value in updates.items():
                if key in fieldnames:
                    row[key] = value
    
    # CSV'yi yeniden yaz
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == '__main__':
    organize_photos('fotograflar', 'ARIZALAR.csv')