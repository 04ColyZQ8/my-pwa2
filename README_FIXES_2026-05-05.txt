CarLock fixes 2026-05-05

ESP32 sketch:
- CarLock_A7670_SD_GPS_WakeFix_StaleFix.ino
- Every CAN command goes through ensureBusAwakeForCommand().
- Full bus wake is skipped only when recent CAN RX or recent keepalive proves bus is already active.
- Removed ESP32 Wi-Fi geolocation fallback. Location is OnStar GPS only.
- Engine/RPM stale timeout clears false RUNNING state if RPM frames stop.
- Keeps SD logging, dynamic 2014/2015 GM lock ACK, OnStar GPS decode.

Backend/frontend:
- app.py keeps OnStar-only /api/getCarLocation and disables legacy /api/location Wi-Fi geolocation.
- app.py now persists VIN decode cache to vin_cache.json when possible.
- carlockPWA.js caches stable vehicle info in localStorage so VIN/model name does not flicker or slow the UI.

Blynk pins used:
V28 latitude double
V29 longitude double
V30 GPS status string
V31 speed integer
V32 heading integer
