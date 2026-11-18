# FSS Control Center — Deployment Kit

Paket ini menyiapkan pola deployment berikut:

- GitHub Pages: halaman informasi dan download.
- GitHub Releases: distribusi ZIP Windows.
- Windows Launcher: menjalankan FastAPI lokal dan frontend build lokal.
- Pemrosesan Excel: tetap di laptop pengguna; tidak dikirim ke backend cloud.

## Isi paket

- `be/app/services/sch_reconciliation.py`: alias `Delivery time` -> `Delivery period`.
- `be/app/services/sch_validator.py`: validator mengenali header fisik `Delivery time`, dengan kompatibilitas nama `Delivery period`.
- `launcher/main.py`: launcher Windows; menjalankan API di `127.0.0.1:8000`, menyajikan frontend di `127.0.0.1:5173`, dan meneruskan `/api/*` ke FastAPI.
- `launcher/build_windows.bat`: build frontend dan paket EXE dengan PyInstaller.
- `.github/workflows/pages.yml`: deploy halaman download GitHub Pages.
- `.github/workflows/release-windows.yml`: build dan publish ZIP Windows saat tag `v*` dibuat.
- `site/index.html`: halaman awal GitHub Pages.
- `.gitignore`: mengecualikan database lokal, file Excel operasional, environment, dan cache.

## Cara menerapkan ke project lokal

1. Backup folder project terlebih dahulu.
2. Ekstrak paket ini ke folder project lokal `fss-control-center`, izinkan file patch menimpa dua service SCH yang disebut di atas.
3. Pastikan struktur project lokal tetap memiliki `be/`, `fe/`, dan `fe/package.json`.
4. Pastikan file `be/requirements.txt` tetap milik project kamu. Paket ini tidak mengganti dependency aplikasi.
5. Periksa `fe` menggunakan `npm run build`. Jika FE memakai API URL absolut, pastikan targetnya `http://127.0.0.1:8000` atau `http://localhost:8000`. Jika FE memakai path relatif `/api`, launcher menyediakan proxy lokal.
6. Jalankan `launcher/build_windows.bat` di Windows. Hasilnya ada di `dist/FSSControlCenter/` dan `dist/FSS-Control-Center-Windows.zip`.

## Catatan runtime

- Launcher membutuhkan Windows.
- Microsoft Excel desktop harus terpasang untuk operasi yang menggunakan `xlwings`.
- Port lokal yang digunakan: `8000` (API) dan `5173` (frontend).
- Konfigurasi dan riwayat Tanpa Rumus disimpan di `%LOCALAPPDATA%\\FSSControlCenter\\data`, bukan di folder publik project.
- Jangan commit `*.xlsx`, `*.xlsm`, `be/data/*.db`, `.env`, atau data order perusahaan.

## Aktifkan GitHub Pages

1. Push folder `site/` dan workflow ke branch `main`.
2. Di repository GitHub, buka Settings -> Pages.
3. Pada Build and deployment, pilih Source: **GitHub Actions**.
4. Workflow `Deploy GitHub Pages` akan menerbitkan halaman.

Alamat project Pages yang diharapkan:
`https://fsscontrolcenter.github.io/fsscontrolcenter/`

## Terbitkan Launcher Windows melalui GitHub Releases

Setelah seluruh source project (folder `be`, `fe`, `launcher`, `site`, dan `.github`) sudah berada di repository organization:

```powershell
git add .
git commit -m "Prepare local Windows deployment"
git push organization main
git tag v0.1.0
git push organization v0.1.0
```

Tag akan memicu workflow build Windows. Setelah workflow selesai, ZIP akan tersedia di GitHub Releases dan tombol download pada halaman Pages akan mengarah ke release terbaru.

## Penting: repository organization

Pastikan source code aplikasi benar-benar sudah di-push ke `fsscontrolcenter/fsscontrolcenter`. Jangan hanya mengunggah `README.md`. Repository publik tidak boleh berisi database lokal, file Excel perusahaan, token, atau `.env`.

## Batas verifikasi

Paket ini menyiapkan patch dan alur build. Build EXE final harus dijalankan pada Windows dan diuji pada laptop Windows yang memiliki Microsoft Excel desktop. GitHub Actions juga perlu dijalankan setelah source project lengkap berada di repository.
