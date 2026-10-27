# Çizgi sensörü dizisinin anlık durumu (ika_line/line_sensor_node yayınlar).

std_msgs/Header header

# Soldan sağa sensör okumaları; true = sensör çizgiyi görüyor.
bool[] sensors

# Ham okumalar, soldan sağa. QTR-RC: boşalma süresi [µs] (koyu = uzun);
# dijital sensör: pin seviyesi (0/1). Eşik ayarı için.
uint16[] raw

# En az bir sensör çizgiyi görüyor mu?
bool detected

# Çizginin robot eksenine göre yanal konumu (metre, ROS kuralı: sol +y).
# detected=false iken anlamsızdır.
float32 position

# Tüm sensörler aynı anda çizgiyi görüyor (kavşak / bitiş çizgisi).
bool intersection
