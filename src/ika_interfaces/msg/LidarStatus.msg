# Lidar bağlantı durumu (/ika/lidar, lidar_manager_node).

string source     # usb | gpio
string port       # kullanılan seri port; bulunamadıysa boş
bool running      # sllidar sürücüsü çalışıyor
float32 rate_hz   # son birkaç saniyedeki /scan hızı
string message    # son hata veya bilgi
