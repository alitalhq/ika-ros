# Kullanım ve pil güvenliği

Robot 3S Li-Po (11.1 V nominal, dolu 12.6 V, 4200 mAh, 40C) ile çalışır. Li-Po piller hafif
ve güçlüdür ama yanlış kullanılınca şişer, alev alır ve söndürmesi zordur.
Bu sayfadaki kurallar robotla çalışan herkes içindir.

## Pil: zorunlu kurallar

- **Her pile düşük gerilim alarmı (low battery alarm / Li-Po checker) takın.**
  Alarm pilin balans soketine takılır, her hücreyi ayrı izler ve ayarlanan
  eşiğin altında öter. Eşiği **3.5 V/hücre** yapın (3S için ~10.5 V). Alarm
  ötünce robotu hemen durdurun ve pili çıkarın. Li-Po 3.0 V/hücrenin altına
  indiğinde kalıcı hasar görür ve bir sonraki şarjda şişebilir. Robotun
  yazılımı pil gerilimini ölçmez; tek koruma bu alarmdır.
- **Li-Po'yu taşırken ve şarj ederken Li-Po güvenlik çantasında (safe bag)
  tutun.** Çanta yangını durdurmaz ama alevi içinde tutar, çevreye yayılmasını
  geciktirir. Çantaya tek pil koyun, fermuarını kapatın.
- **Pili, kullandığınız pilin üreticisinin dokümantasyonuna (etiket, veri
  sayfası, kullanım kılavuzu) uygun şekilde şarj edin.** Şarj akımı, şarj
  gerilimi, sıcaklık aralığı ve saklama koşulları pilden pile değişir;
  üreticinin değerleri bu sayfadaki genel değerlerden önce gelir. Şarj
  cihazının kılavuzundaki talimatlara da uyun.
- **Yalnızca balanslı Li-Po şarj cihazıyla şarj edin** (balans soketi takılı,
  "LiPo Balance" modu, hücre sayısı 3S). Akım: en fazla 1C, yani 4200 mAh pil
  için **4.2 A** (daha düşük, ör. 2 A, pile daha iyi gelir). Pilin üzerindeki
  **40C deşarj** değeridir (en fazla ~168 A çekilebilir); şarj akımı değildir.
- **Şarjı hiçbir zaman gözetimsiz bırakmayın**, gece boyu şarjda bırakmayın.
  Yanmaz bir zeminde (seramik, beton, metal tepsi), yanıcı şeylerden uzakta
  şarj edin.
- **Şişmiş, ezilmiş, delinmiş, kablosu soyulmuş ya da ısınan pili kullanmayın,
  şarj etmeyin.** Safe bag'e koyup dışarıda, yanmaz bir yerde bekletin ve
  pil geri dönüşüm noktasına verin.

## Pil: günlük kullanım

| Durum | Hücre başına | 3S toplam |
|---|---|---|
| Tam dolu | 4.20 V | 12.6 V |
| Saklama | 3.80–3.85 V | 11.4–11.6 V |
| Alarm eşiği (önerilen) | 3.50 V | 10.5 V |
| Kesinlikle altına inmeyin | 3.00 V | 9.0 V |

- Bir haftadan uzun kullanmayacaksanız şarj cihazının **Storage** moduyla
  saklama gerilimine getirin. Tam dolu ya da boş saklamak ömrünü kısaltır.
- Sürüşten hemen sonra pil ılıktır; soğumadan şarj etmeyin.
- Hücreler arasında 0.1 V'tan fazla fark varsa balanslı şarjla eşitleyin; fark
  sürekli büyüyorsa pil yaşlanmıştır.
- Saha ayarlarını (`min_duty`, `max_wheel_speed`) **dolu pille** yapın; zayıf
  pilde motorlar aynı duty'de yavaş döner (bkz. [saha testi](saha-testi.md)).
- Soğukta (0 °C altı) pil kapasitesi düşer ve alarm erken öter; şarj etmeyin.

## Taşıma

- Pili robottan **çıkararak**, safe bag içinde taşıyın. Robotun içinde
  taşınan pilin konnektörü kısa devre yapabilir.
- Konnektörü (XT60 vb.) açıkta bırakmayın; uç kapağı takın ya da bantlayın.
  Anahtar, bozuk para ve aletlerle aynı cebe koymayın.
- **Uçakta** Li-Po yalnızca kabin bagajında taşınabilir, bagaja verilemez.
  100 Wh altı pillerde genelde izin gerekmez (bu pil: 11.1 V × 4.2 Ah ≈ 47 Wh). Her pil
  ayrı safe bag'de, uçları yalıtılmış olsun; havayolunun kuralına bakın.
- Güneşte kalan araçta bırakmayın.

## Yangın olursa

- Pili ve robotu yanıcı şeylerden uzaklaştırabiliyorsanız uzaklaştırın;
  dumanı solumayın, Li-Po dumanı zehirlidir.
- Küçük Li-Po yangınında en etkilisi **bol suyla soğutmak** ya da kumla
  boğmaktır; tozlu (ABC) yangın söndürücü de kullanılabilir. Söndükten sonra
  pil yeniden alev alabilir; saatlerce açık havada, kovada bekletin.

## Robotu kullanırken

- **Pili takmadan önce** kabloları kontrol edin: kutup (kırmızı +, siyah −),
  gevşek ya da açıkta kalan uç, L298N vida klemenslerinde kılçık. Ters
  bağlanan pil L298N'i ve Gemstone'u yakar.
- **Kablo değiştirirken pili çıkarın.** Pil takılıyken pin değiştirmek
  GPIO'ları yakabilir.
- Pilde bir **ana anahtar ve sigorta** (ör. 10 A bıçak sigorta) olması
  önerilir. 40C pil kısa devrede 150 A'in üstünde akım verebilir; kablo ve
  L298N yanmadan önce sigorta atar.
- **Gemstone pilden doğrudan beslenebilir, ama yalnızca DC güç girişinden**
  (şemada J4, "Optional Power Input"). Resmi değer 5–12 V / 5 A; dolu 3S
  12.6 V ile bunun biraz üstündedir ama donanım payın içindedir
  (t3-gem-o1 v0.2 şeması ve TI veri sayfalarına göre):
  - Girişteki eFuse (IC4, TPS259470A) aşırı gerilim kesmesi R26 = 1 MΩ /
    R29 = 88.7 kΩ ile **~14.7 V'ta** keser (eşik 1.183–1.223 V → 14.5–15.0 V),
    13.4 V'un altına inince yeniden açar. eFuse'un kendisi 23 V'a kadar
    çalışır.
  - Arkadaki 5 V düşürücü (TPS62180) 4–15 V aralığında çalışır, mutlak
    sınırı 17 V'tur.
  - Kartınızın revizyonu farklıysa şemasına bakın.
- **Pili Type-C girişine asla vermeyin.** Type-C 5–9 V içindir; o hattın
  eFuse'u (IC3, R16 = 1 MΩ / R22 = 133 kΩ) ~10.2 V'ta keser.
- Pil takılıyken Type-C de bağlanabilir: kart iki eFuse ile öncelikli güç
  seçici olarak tasarlanmış, Type-C'de geçerli güç varsa pil yolunu kendisi
  kapatır (IC3 AUXOFF → Q8 → R32 → IC4 OVLO). Bu durumda kart USB'den,
  motorlar pilden beslenir.
- Pil girişinin düşük gerilim kesmesi (R28 = 1 MΩ / R33 = 430 kΩ) ~4.0 V'ta
  açar, ~3.6 V'ta kapatır; yani kart **pili aşırı deşarjdan korumaz**. 3S'i
  10.5 V altına indirmemek düşük gerilim alarmının işidir.
- Pilden Gemstone'a ve L298N'e **ayrı kablolarla** gidin (yıldız bağlantı);
  birinin klemensinden diğerine köprü yapmayın. L298N besleme girişine
  470–1000 µF elektrolitik kondansatör koyun (motorların ani durmasında
  besleme hattına dönen gerilimi bastırır). Batarya, L298N, Gemstone ve
  enkoder **GND'leri ortaktır**.
- İlk testleri **tekerler havada** (robotu bir kutunun üstüne koyarak) yapın.
  Yazılım ayarı yanlışsa robot masadan düşmez.
- Robot hareket ederken elinizi tekerlerden uzak tutun; web arayüzündeki
  **acil durdurma** düğmesinin yerini bilin. Arayüz bağlantısı koparsa robot
  `/cmd_vel` zaman aşımıyla kendiliğinden durur, ama buna güvenip robotu
  masanın kenarında sürmeyin.
- Lidar freni (`safety.enabled`) yalnızca lidarın gördüğü yükseklikteki
  engelleri görür; alçak cisimleri, merdiven boşluğunu, masa kenarını görmez.
- L298N yük altında ısınır; soğutucusuna dokunmayın, havalandırmasını
  kapatmayın.
- Lidarın lazeri Class 1'dir (göze zararsız kabul edilir), yine de dönen
  kafaya uzun süre yakından bakmayın.
- Robotu suya, ıslak zemine, tozlu ve metal talaşlı yüzeylere sokmayın.

## Kapatma

Pili ya da USB-C'yi doğrudan çekmek dosya sistemini bozabilir (kartın
günlüğünde bunun izleri görüldü). Önce yazılımı kapatın:

```bash
ssh gemstone@<robot-ip> sudo poweroff
```

Kartın ışıkları sönünce (~15 sn) pili çıkarın. Kart pilden beslendiği için
`poweroff`'tan sonra bile pilden akım çekmeye devam eder.
Pili robotta takılı bırakmayın: birkaç saatte 3.0 V/hücrenin altına inip
kalıcı hasar görebilir.

## Kontrol listesi

Her çalışmadan önce:

- [ ] Pil şişmemiş, kablosu sağlam, gerilimi 11.4 V üstü
- [ ] Düşük gerilim alarmı balans soketine takılı ve eşiği 3.5 V
- [ ] Kablolar ve kutup kontrol edildi, pil en son takıldı
- [ ] Acil durdurma ekranda açık
- [ ] İlk hareket tekerler havada denendi

Bittikten sonra:

- [ ] `sudo poweroff`, ışıklar sönünce pil çıkarıldı
- [ ] Pil soğuyunca safe bag içinde, üreticinin talimatlarına göre şarj edildi ya da saklama gerilimine
      getirildi
