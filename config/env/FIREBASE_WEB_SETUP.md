# Firebase web app — OMEIA.AI (console reference)

**Production deploy:** set `VITE_API_URL` and `VITE_FIREBASE_*` in `react_frontend/.env.production` before `npm run build` — see `configs/DEPLOYMENT_ENV.md` and `docs/26_PRODUCTION_DEPLOYMENT.md`. The SPA calls the FastAPI host at `VITE_API_URL` (`apps/web/src/App.jsx`).

**Project:** `farkki-digital-notebook` (570069536455)  
**Web app nickname:** OMEIA.AI  
**Console owner:** `farkkilalab@gmail.com` (password never stored in repo)  
**SDK version (Console CDN):** `12.14.0` — npm package aligned in `react_frontend/package.json`

> **Note:** `measurementId` is **optional** (Firebase JS SDK v7.20.0+). OMEIA sets `G-24JLFQYRTG` for Analytics when desired; Auth works without it.

---

## `firebaseConfig` (canonical values)

Store secrets in `configs/.env` and `react_frontend/.env.local` — **not** in this file.

```javascript
const firebaseConfig = {
  apiKey: "…", // FIREBASE_WEB_API_KEY / VITE_FIREBASE_API_KEY
  authDomain: "farkki-digital-notebook.firebaseapp.com",
  projectId: "farkki-digital-notebook",
  storageBucket: "farkki-digital-notebook.firebasestorage.app",
  messagingSenderId: "570069536455",
  appId: "1:570069536455:web:4c4623a81262e6c4eef8e2",
  measurementId: "G-24JLFQYRTG", // optional
};
```

---

## Option A — npm modules (what OMEIA React app uses)

Matches Console config; bundled by Vite.

```javascript
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics"; // optional
import { getAuth, signInWithEmailAndPassword } from "firebase/auth";

const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app); // optional — see initFirebaseAnalytics() in repo
const auth = getAuth(app);
```

**Repo:** `apps/web/src/config/firebase.js`

---

## Option B — CDN `<script type="module">` (Console copy-paste)

Firebase Console also offers this **CDN** variant. Same `firebaseConfig`; different import URLs.  
**Do not mix** CDN and npm in the same page — OMEIA uses **npm only**.

```html
<script type="module">
  import { initializeApp } from "https://www.gstatic.com/firebasejs/12.14.0/firebase-app.js";
  import { getAnalytics } from "https://www.gstatic.com/firebasejs/12.14.0/firebase-analytics.js";

  const firebaseConfig = {
    apiKey: "…",
    authDomain: "farkki-digital-notebook.firebaseapp.com",
    projectId: "farkki-digital-notebook",
    storageBucket: "farkki-digital-notebook.firebasestorage.app",
    messagingSenderId: "570069536455",
    appId: "1:570069536455:web:4c4623a81262e6c4eef8e2",
    measurementId: "G-24JLFQYRTG",
  };

  const app = initializeApp(firebaseConfig);
  const analytics = getAnalytics(app);
</script>
```

For **Auth** via CDN you would additionally import:

`https://www.gstatic.com/firebasejs/12.14.0/firebase-auth.js` and use `getAuth` — OMEIA does this via npm instead.

---

## How this repo uses Firebase

| Piece | Used? | Where |
|-------|-------|--------|
| `initializeApp` + full `firebaseConfig` | Yes | `src/config/firebase.js` + env |
| `getAuth` + **Email/Password** | Yes | Administration login panel |
| `getAnalytics` | Optional | `initFirebaseAnalytics()` from `App.jsx` |
| Google Sign-In | **No** | Disabled in Console |
| Storage / Messaging SDKs | No | MVP not required |
| CDN `gstatic` scripts | **No** | Vite/npm only |

## `VITE_API_URL` (FastAPI backend)

| Environment | Value |
|-------------|--------|
| Local dev | Omitted → `http://<hostname>:8000` (see `App.jsx`) |
| Production (Hostinger) | `https://api.yourdomain.example` — must match backend TLS URL |

Backend must set `CORS_ORIGINS` to include your Hostinger app origin (e.g. `https://app.yourdomain.example`). Never put WebDAV or Supabase service credentials in Vite env.

## Backend (separate from web config)

- **Admin SDK** verifies ID tokens from Email/Password sign-in.
- Service account file: `configs/secrets/firebase-adminsdk.json` (gitignored).
- Set `FIREBASE_SERVICE_ACCOUNT_PATH` in `configs/.env` to that path.
- Web `apiKey` is **not** the Admin SDK credential.

### Security — service account file

- **Never** place the Admin SDK JSON under a web `public/` folder (it would be downloadable if deployed).
- OMEIA copies the file locally into `configs/secrets/` only; remove it from `lab-newspaper-site-react/public/` and **rotate the key** in Google Cloud if that site was ever published with `public/` exposed.
- Account: `firebase-adminsdk-fbsvc@farkki-digital-notebook.iam.gserviceaccount.com`

## Auth policy

- **Platform users:** `@helsinki.fi` allowlist + Firebase Email/Password.
- **Console:** `farkkilalab@gmail.com` for Firebase/Google Cloud UI only.
