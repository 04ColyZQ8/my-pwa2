CarLock OnStar GPS-only frontend/backend update

Replace these files on your backend/static site:
- app.py
- carlockPWA.html
- carlockPWA.css
- carlockPWA.js
- fallback.png
- manifest.json
- service-worker.js
- requirements.txt

ESP32 sketch does not need to be changed for the bad map issue.

Important changes:
- /api/getCarLocation now uses Blynk V28/V29 OnStar GPS only.
- Google Wi-Fi geolocation fallback is disabled because it returned bad coordinates.
- Frontend clears stale cached maps and retries automatically while OnStar GPS wakes up.

Required Blynk datastreams:
V28 Double latitude (-90 to 90, 6 decimals)
V29 Double longitude (-180 to 180, 6 decimals)
V30 String GPS status
V31 Integer speed km/h
V32 Integer heading degrees
