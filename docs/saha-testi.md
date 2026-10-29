# Saha testi: adım adım

Her adım bir öncekine dayanır; sırayı atlamayın. Motor adımlarında robotu
**tekerleri havada kalacak şekilde** bir kutunun üzerine koyun.

Komutlar Gemstone üzerinde, konteyner içinde çalışır:

```bash
cd ~/ika-ros
docker compose build                      # ilk sefer ~15-20 dk
docker compose run --rm ika bash          # test kabuğu
# konteyner içinde:
HW=/ika_ws/src/ika/ika_bringup/config/hardware.yaml
```

Docker'sız kurulumda ([native-kurulum.md](native-kurulum.md)) servisi durdurup
root kabuğunda aynı ortamı kurun:

```bash
sudo systemctl stop ika
sudo -i
source /opt/ros/jazzy/setup.bash && source ~gemstone/ika-ros/install/setup.bash
export PYTHONPATH=~gemstone/ika-gpio-venv/lib/python3.12/site-packages:$PYTHONPATH
HW=~gemstone/ika-ros/src/ika_bringup/config/hardware.yaml
```

(`gemstone` yerine kendi kullanıcı adınızı yazın.) Testler bitince
`sudo systemctl start ika`.

`./src` konteynere bağlı olduğu için `hardware.yaml`'ı host'ta düzenleyince
değişiklik hemen geçerli olur. Yeni Python dosyası veya C++ değişikliğinden
sonra konteynerde `colcon build --symlink-install` çalıştırın.

## 0. Hazırlık

- [ ] `/boot/uEnv.txt`'de üç PWM overlay'i açık, yasaklı olanlar kapalı ([donanim.md](donanim.md#overlayler-bootuenvtxt))
- [ ] Enkoderler ve çizgi sensörü **3.3 V** ile besleniyor (sensörde "3.3V" köprüsü lehimli); ENA/ENB jumper'ları çıkarılmış
- [ ] Pinler çözülüyor ve çakışma yok:

```bash
ros2 run ika_base hw_check pins --config $HW
```

Çıktıda her `GPIOxx` bir `gpiochipN:line`'a, her PWM bir `pwmchipN`'e çözülmeli.
"bulunamadı" hatası varsa `gpioinfo | grep -i gpio` ile karttaki adı bulup
`hardware.yaml`'a o adı ya da `gpiochipN:line` yazın.

## 1. IMU

```bash
ros2 run ika_imu ika_imu_node --ros-args --params-file $HW
ros2 topic echo /imu/data_raw --field angular_velocity     # ikinci terminal
```

- [ ] Açılışta "jiroskop sapması" satırı çıkıyor (robot o sırada hareketsiz)
- [ ] Robot dururken `z` ≈ 0 (±0.01 rad/s)
- [ ] Robotu yukarıdan bakınca **saat yönünün tersine** çevirince `z` **pozitif**.
      Negatifse kart ters takılmıştır: `ika_description/config/robot.yaml` →
      `imu.roll: 3.14159` (kitte böyledir). Düzeltme TF'te yapılır; ham
      `/imu/data_raw` yine negatif görünür. Tam robotta doğrulayın: yerinde sola
      dönerken `/wheel/odom` ve `/odometry/filtered` `angular.z` ikisi de pozitif
      olmalı. Ters ise harita ayna görüntüsü gibi çıkar

## 2. Motor yönleri

```bash
ros2 run ika_base hw_check motors --config $HW --duty 50
```

Robotun arkasında durup öne (çizgi sensörüne) bakın. Araç önce `left`'i,
sonra `right`'ı döndürür.

- [ ] Önce **sol**, sonra **sağ** teker dönüyor. Ters sırayla dönüyorsa
      `hardware.yaml`'da `left` ve `right` bloklarını (yön ayarlarıyla birlikte)
      yer değiştirin; aksi halde ileri doğru gider ama sağ/sol dönüş ters olur
- [ ] Her teker robotu ileri götürecek yönde dönüyor. Dönmüyorsa önerilen `invert` düzeltmesini yapın
- [ ] Hiç dönmüyorsa: IN pinleri, PWM kanalı, EN jumper'ı, motor beslemesi

## 3. Enkoderler

```bash
ros2 run ika_base hw_check encoders --config $HW
```

- [ ] Tekeri elle tam bir tur **ileri** çevirince sayım pozitif ve ~2184 (x4: 546 × 4)
- [ ] Gösterilen `ppr≈` 546'dan çok farklıysa motor farklı redüktörlüdür: `encoder.ppr`'yi düzeltin
- [ ] `hata` sayacı 0 kalıyor. `hw_check sweep` sırasında yüksek duty'de artıyorsa
      olaylar kaçıyor demektir: `hw_check pins` çıktısında `libgpiod python API: v2`
      yazdığını doğrulayın (v1'in olay tamponu bu motor için küçük)
- [ ] Sayım yönü tersse `enc_invert: true` (`hw_check motors` de önerir)

## 4. Hız aralığı

```bash
ros2 run ika_base hw_check sweep --config $HW
```

**Pil dolu iken** ölçün (3S: 12.0–12.6 V). Zayıf pilde motorlar aynı duty'de
çok daha yavaş döner ve yük altında voltaj çöküp iki teker birden durabilir;
o ölçümle ayarlanan değerler pil dolunca yanlış olur. 3S LiPo'yu 10.5 V'un
altına indirmeyin.

- [ ] `pid.min_duty` ← tekerin kalktığı duty
- [ ] `max_wheel_speed` ← %100'de **iki tekerin yavaş olanının** hızı

## 5. Kapalı çevrim sürüş

```bash
ros2 launch ika_bringup robot.launch.py lidar:=false line:=false slam:=false
```

Host'ta tarayıcıdan `http://<gemstone-ip>:8000` açın, **Manuel** moda alıp sürün.

```bash
ros2 topic echo /ika_base_node/wheels    # [hedef_sol, ölçülen_sol, duty_sol, hedef_sağ, ölçülen_sağ, duty_sağ]
```

- [ ] Ölçülen hızlar hedefe oturuyor, salınım yok. Salınım varsa `pid.kp`'yi düşürün, hedefin altında kalıyorsa `pid.ki`'yi artırın
- [ ] Robot düz giderken sapmıyor (iki teker aynı hızda)
- [ ] Acil durdur (Boşluk) motorları anında kesiyor

## 6. Odometri kalibrasyonu

- [ ] **Düz 1 m**: arayüzden düz sürün, `/wheel/odom` x ile şerit metreyi
      karşılaştırın → `robot.yaml` `wheel_radius` × (gerçek / ölçülen)
- [ ] **Yerinde 5 tur**: `/wheel/odom` açısı ile gerçeği karşılaştırın →
      `wheel_separation` × (ölçülen / gerçek)
- [ ] EKF (`/odometry/filtered`) yaw'ı, 5 turdan sonra gerçeğe teker odometrisinden daha yakın

## 7. Lidar

```bash
ros2 launch ika_bringup robot.launch.py line:=false slam:=false
```

Bağlantı arayüzdeki **Lidar** panelinden seçilir (varsayılan USB). Panel
portu ve tarama hızını gösterir; seçim robotta saklanır.

- [ ] Lidar başı dönüyor, panelde ≈ 5–8 Hz (ya da `ros2 topic hz /scan`)
- [ ] **USB:** panel "lidar portu yok" diyorsa `ls /dev/serial/by-id/` boş
      olabilir; minimal imajda CP210x sürücüsü eksiktir (`lsmod | grep cp210x`)
- [ ] **GPIO:** "operation timeout" alıyorsanız TX/RX çapraz mı (lidar TX →
      pin 10), `/dev/ttyS3` var mı ve `ecap2` overlay'i açık mı kontrol edin;
      sürerse `gpio.duty_percent`'i 75'e indirin (motor gürültüsü UART'ı bozabiliyor)
- [ ] Lidarın açısı doğru. Robotun tam önüne (çizgi sensörü tarafı, ortalı,
      30–40 cm) lidar yüksekliğinden uzun bir kutu koyun; 1 m içinde başka
      bir şey olmasın. Kutunun `/scan`'deki açısı `a` ise `robot.yaml` →
      `lidar.yaw = -a` (radyan). Kitte lidar 180° dönük takılıdır: kutu
      ~±180°'de görünür, `yaw` ≈ 3.14. Yanlışsa harita sürüşte kayar, dönerken dağılır
- [ ] (İsteğe bağlı) Lidar freni: `control.yaml` → `safety.enabled: true` iken önde
      kutuya ~0.10 m kala duruyor, yanından geçilen duvarda yavaşlamıyor

## 8. Çizgi sensörü ve izleme

**Deneyap Kart üzerinden (`type: serial`, varsayılan).** Robot `line:=true` ile
çalışırken:

```bash
ros2 topic echo /line/state --field raw      # D1 … D8, mV
```

- [ ] Değerler akıyor. Akmıyorsa: Deneyap TX → pin 10, RX → pin 8, ortak GND,
      firmware yüklü mü; servis günlüğünde "Deneyap'tan veri gelmiyor" uyarısı
- [ ] Sensör 3–6 mm yükseklikte; beyaz ile siyah arasında her kanalda yüzlerce mV
      fark var (100 mV civarındaysa sensör çok yüksekte)
- [ ] Kalibrasyon: [donanim.md](donanim.md#deneyap-kart-1a-v2-üzerinden-varsayılan-type-serial)
      → `/line/calibrate_white`, `/line/calibrate_black` başarılı
- [ ] `ros2 topic echo /line/state --field sensors`: beyazda hepsi `false`, siyahta `true`
- [ ] Siyah bandı sensörün altında soldan sağa kaydırınca `true` soldan sağa ilerliyor.
      Ters ilerliyorsa A0…A7 kabloları ters takılmıştır

**Doğrudan GPIO (`type: digital`).**

```bash
ros2 run ika_line line_check --config $HW
```

- [ ] Sensör beyaz zeminin 3–5 mm üstündeyken 8 kanal **0**, siyah bandın üstünde **1**
- [ ] Hep 1 ise: sensör VCC pin 17'de mi, GND bağlı mı, "3.3V" köprüsü lehimli mi,
      D kabloları takılı mı ([donanim.md](donanim.md#çizgi-sensörü))
- [ ] Siyah bandı sensörün altında soldan sağa kaydırınca 1 soldan sağa ilerliyor.
      Ters ilerliyorsa `pins` listesini ters çevirin

**Her iki bağlantıda:**
- [ ] Robot launch'ında `/line/state`: çizgi soldayken `position` **pozitif**
- [ ] Pistte arayüzden **Çizgi izle**: önce `speed: 0.10` ile başlayın,
      sonra `kp` / `kd` / `speed` ayarlayın (`control.yaml`)

## 9. Haritalama

```bash
ros2 launch ika_bringup robot.launch.py
```

- [ ] Arayüzden yavaşça sürerken harita oluşuyor, duvarlar çift görünmüyor
- [ ] **Harita kaydet** → `~/ika_maps/<isim>.{pgm,yaml,posegraph,data}`

## 10. Kayıtlı haritada hedefe gitme

Robotu haritalamaya **başladığınız noktaya, aynı yöne bakacak şekilde** koyun:

```bash
ros2 launch ika_bringup robot.launch.py slam_mode:=localization map:=~/ika_maps/<isim> nav:=true
```

- [ ] Arayüzde "Tıkla → hedef" açıp haritaya tıklayınca robot oraya gidiyor (mod: NAV)
- [ ] Yol sırasında bir tuşa basınca robot manuele geçip duruyor (devralma)
