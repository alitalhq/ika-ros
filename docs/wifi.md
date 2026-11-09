# Robotu yeni bir Wi-Fi ağına bağlama

Gemstone'da Wi-Fi'yi NetworkManager (`nmcli`) yönetir. Bir ağa bir kez
bağlanınca şifresi kaydedilir; robot sonraki açılışlarda o ağı kendiliğinden
bulur. Yeni bir yerde (yarışma alanı, okul, ev) robotun ağını bir kez tanıtmak
gerekir.

Robot henüz o ağda olmadığı için Wi-Fi üzerinden ona ulaşamazsınız. Aşağıdaki
yollardan biriyle karta girin.

## 1. Karta bağlanma (ağ olmadan)

**Type-C kablosuyla (önerilen).** Gemstone'u Type-C ile bilgisayara takın.
Kart açılınca (~1 dk) bilgisayarda bir USB ağ arayüzü belirir ve kart
`192.168.7.2` adresinden cevap verir:

```bash
ssh gemstone@192.168.7.2        # kullanıcı adı imajı yazarken seçtiğinizdir
```

İlk bağlantıda "host key" sorusuna `yes` deyin. Kart yeniden imajlandıysa
"REMOTE HOST IDENTIFICATION HAS CHANGED" uyarısı çıkar; eski kaydı silin:
`ssh-keygen -R 192.168.7.2`.

**Seri konsol.** Aynı Type-C kablosu bilgisayarda `/dev/ttyACM0` (Windows'ta
`COMx`) olarak da görünür: `sudo screen /dev/ttyACM0 115200` (çıkış:
`Ctrl-A`, `k`).

**Ekran ve klavye.** Karta HDMI ekran ve USB klavye takıp doğrudan da
girebilirsiniz.

## 2. Ağı tanıtma

```bash
sudo nmcli dev wifi rescan
sudo nmcli dev wifi list                                # görünen ağlar
sudo nmcli dev wifi connect "AĞ_ADI" password "ŞİFRE"   # kaydet ve bağlan
```

Ağ adında boşluk varsa tırnak içinde yazın. Komut `successfully activated`
derse bağlantı kaydedilmiştir.

**Gizli ağ (SSID yayınlamıyor):**

```bash
sudo nmcli dev wifi connect "AĞ_ADI" password "ŞİFRE" hidden yes
```

**Kurumsal ağ (kullanıcı adı + şifre, WPA2-Enterprise / eduroam vb.):**

```bash
sudo nmcli connection add type wifi ifname wlan0 con-name "AĞ_ADI" ssid "AĞ_ADI" \
  wifi-sec.key-mgmt wpa-eap 802-1x.eap peap 802-1x.phase2-auth mschapv2 \
  802-1x.identity "KULLANICI" 802-1x.password "ŞİFRE"
sudo nmcli connection up "AĞ_ADI"
```

`peap`/`mschapv2` en yaygın ayardır; ağın yöneticisi farklısını söylerse onu
yazın.

**Telefon hotspot'u** da sıradan bir ağ gibi eklenir; pist başında ağ yoksa
en kolay yol budur. Robot ve tarayıcıyı açan bilgisayar aynı hotspot'a
bağlanmalıdır.

## 3. Robotun yeni adresini bulma

Ağ DHCP ile adres verir; her ağda adres farklıdır.

```bash
ip -4 -br addr show wlan0       # ör. wlan0  UP  10.0.10.91/23
```

Web arayüzü: **`http://<bu-adres>:8000`**. Arayüzü açacak bilgisayar robotla
aynı ağda olmalıdır. Bazı kurumsal ve misafir ağlar cihazların birbirini
görmesini engeller (client isolation); arayüz açılmıyorsa hotspot deneyin.

## Kayıtlı ağları yönetme

```bash
nmcli -t -f NAME,TYPE connection show            # kayıtlı ağlar
sudo nmcli connection delete "AĞ_ADI"            # bir ağı unut
sudo nmcli connection modify "AĞ_ADI" connection.autoconnect-priority 10
```

Birden fazla kayıtlı ağ aynı anda görünüyorsa önceliği yüksek olana bağlanır.

## Sorun giderme

- `Secrets were required, but not provided`: şifre yanlış, ya da ağ kurumsal
  (yukarıdaki kurumsal komutu kullanın).
- `No network with SSID ... found`: ağ 5 GHz'de ve kart görmüyor olabilir,
  ya da kart menzil dışında. `nmcli dev wifi list` çıktısına bakın.
- Bağlandı ama arayüz açılmıyor: robot servisi çalışıyor mu
  (`systemctl status ika`), bilgisayar aynı ağda mı, ağ cihazları
  birbirinden yalıtıyor mu?
- Şifreyi `nmcli` komutuna yazmak onu kabuk geçmişine kaydeder. Paylaşılan
  bir kartta sonra `history -c` çalıştırın, ya da `password` yerine
  `--ask` verip şifreyi sorulduğunda girin:
  `sudo nmcli --ask dev wifi connect "AĞ_ADI"`.
