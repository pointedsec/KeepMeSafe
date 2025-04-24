<p align="center">
  <!-- Insert logo here -->
  <img src="./core/static/kms_basic_logo_2.png" alt="KeepMeSafe Logo" width="100" />
</p>

<h1 align="center">KeepMeSafe</h1>

<p align="center">
  🔐 A secure, multi-profile password manager inspired by KeePass. <br/>
  Your vaults, encrypted and in your hands.
</p>

---

## 🚀 About the Project

**KeepMeSafe** is a minimalist, self-hosted password manager built with Django and SQLite.  
It allows users to create separate encrypted vaults under different profiles, each protected with a master key.  
Inspired by simplicity and security, KeepMeSafe is perfect for individual use or as a base for more complex multi-user systems.

---

## 🧰 Features

- 🔐 Encrypted vaults (one per profile)
- 🧑‍💻 Multi-profile support
- 🛡️ Admin-protected profile creation
- 💾 SQLite-backed for easy deployment
- 📦 Docker-ready
- 🖥️ Clean and modern UI with TailwindCSS

---

## ⚙️ Tech Stack

- **Backend**: Django, Python
- **Frontend**: HTML + TailwindCSS
- **Database**: SQLite
- **Deployment**: Docker (optional)

---

## 📸 Screenshots

> Coming soon...

---

## 🚧 How to Run

```bash
git clone https://github.com/pointedsec/keepmesafe.git
cd keepmesafe
python -m venv env
source env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The app will be available at: http://127.0.0.1:8000

---

## 🛡️ Admin Key Protection

To prevent unauthorized access to profile creation:
The admin key is configured in settings.py as `ADMIN_CREATION_KEY`.
Any attempt to access `/create_profile/` will require this key.

---
## 📄 License

This project is licensed under the MIT License.
Feel free to fork, modify, and contribute!

## 🤝 Contributing

Pull requests are welcome!
If you have suggestions or want to collaborate, feel free to open an issue or reach out.

## 💬 Contact

Made with ❤️ by pointedsec.
Feel free to contact me via email: [adelcerrorodriguez@gmail.com](mailto:adelcerrorodriguez@gmail.com)
