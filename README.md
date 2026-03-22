# 📱 Project Dashboard

Local web server + Telegram commands for managing projects on your Android phone.

---

## 🚀 QUICK START

### Option 1: Web Dashboard
```bash
cd ~/.nanobot/workspace/pm-dashboard
bash start.sh
```

Then open in browser:
- **Phone:** http://localhost:8080
- **Laptop (same WiFi):** http://YOUR_IP:8080

### Option 2: Telegram Commands
Just ask me:
- "Show project status"
- "List files in coelum9"
- "Push kruthi to GitHub"
- "Preview coelum9"

---

## 🌐 WEB DASHBOARD FEATURES

| Feature | Description |
|---------|-------------|
| 📂 File Browser | Browse all project files |
| ✏️ Code Editor | Edit files in browser |
| 👁️ Live Preview | See websites instantly |
| 🚀 Git Push | Push to GitHub with one click |
| 📊 Project Stats | File counts, sizes, status |

---

## 📱 TELEGRAM COMMANDS

| Command | What it does |
|---------|--------------|
| `pm_status` | Show all projects |
| `pm_files <project>` | List files |
| `pm_read <project> <file>` | Read file content |
| `pm_push <project> [message]` | Push to GitHub |
| `pm_git <project>` | Git status |
| `pm_serve` | Start web server |
| `pm_preview <project>` | Get preview URL |

---

## 📂 PROJECTS

| Name | Path | Size |
|------|------|------|
| coelum9 | ~/workspace/coelum9 | ~9MB |
| kruthi | ~/workspace/kruthi | ~119MB |
| acumen9 | ~/workspace/acumen9-clone | ~87KB |
| webdev | ~/workspace/webdev-company | ~? |

---

## 🔧 API ENDPOINTS

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/projects` | GET | List projects |
| `/api/files?project=X` | GET | List files |
| `/api/read?project=X&file=Y` | GET | Read file |
| `/api/save` | POST | Save file |
| `/api/push` | POST | Git push |
| `/preview/X` | GET | Preview project |

---

## 💡 TIPS

1. **Share with clients:** Give them your WiFi IP:8080
2. **Edit on phone:** Use Brave browser for best experience
3. **Quick push:** Edit → Save → Push (3 clicks!)
4. **Preview changes:** Switch to Preview tab before pushing

---

*Built with ❤️ by nanobot*
