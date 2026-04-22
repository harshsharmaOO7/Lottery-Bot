# 📱 Image Upload Guide — GitHub App

## Image Naming Convention (ZARURI)

Image ka naam EXACTLY aise rakhna hai:

```
nagaland-8pm-2026-04-13.jpg
nagaland-6pm-2026-04-13.jpg
nagaland-1pm-2026-04-13.jpg
kerala-3pm-2026-04-13.jpg
```

**Format:** `{state}-{draw}-{YYYY-MM-DD}.jpg`

---

## GitHub App Se Upload Kaise Karo

### Step 1 — App Install Karo
- Android: Play Store → "GitHub"
- iPhone: App Store → "GitHub"

### Step 2 — Repo Kholo
1. GitHub app open karo
2. Login karo
3. `harshsharmaOO7/Lottery-Bot` repo dhundho

### Step 3 — Image Upload Karo
1. `images/` folder pe tap karo
2. Top-right mein **"..."** ya **"+"** button
3. **"Upload files"** select karo
4. Gallery se lottery result screenshot select karo
5. **File ka naam rename karo:** `nagaland-8pm-2026-04-13.jpg`
6. Commit message: `8PM result 13 April`
7. **Commit to main** tap karo

### Step 4 — Automatic Ho Jaata Hai ✅
- GitHub Actions automatically trigger hoga
- `update_result.py` chalega
- `results.json` update ho jaayega
- **2-3 minute mein site pe live!**

---

## Verify Karo Ki Live Hua Ya Nahi

1. `https://harshsharmaoo7.github.io/Lottery-Bot/results.json` kholo
2. `nagaland[0].image` check karo — aaj ki date aur 8PM hona chahiye
3. `nagaland[0].image` URL copy karo → browser mein paste karo → image dikhni chahiye

---

## Aaj Ke Draw Ke Liye File Names

```
1PM result:  nagaland-1pm-2026-04-13.jpg   (1PM ke baad)
6PM result:  nagaland-6pm-2026-04-13.jpg   (6PM ke baad)
8PM result:  nagaland-8pm-2026-04-13.jpg   (8PM ke baad)
```

Date aaj ki rakhna — app automatically IST date detect karta hai.
