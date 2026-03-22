# 📱 Project Dashboard + CRM

Local web server for managing projects and clients on Android/Termux.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🚀 **QUICK START**

### **1. Install Dependencies**
```bash
pip install supabase python-dotenv
```

### **2. Set Up Supabase** (5 min)

Follow [SUPABASE_SETUP_GUIDE.md](./SUPABASE_SETUP_GUIDE.md) to:

1. Create Supabase project
2. Run SQL to create tables
3. Set up Row Level Security
4. Get your credentials
5. Create `.env` file

### **3. Start Server**
```bash
cd ~/.nanobot/workspace/pm-dashboard
bash start.sh
```

### **4. Open Dashboard**
- **Phone:** http://localhost:8080
- **Laptop (same WiFi):** http://YOUR_IP:8080
- **CRM:** http://localhost:8080/crm

---

## 🌟 **FEATURES**

### **Project Management**
- 📂 Browse all project files
- ✏️ Edit code in browser (syntax highlighting)
- 👁️ Live preview (SSI support for PHP-like includes)
- 🚀 One-click GitHub push
- 📊 Project stats (files, size, git status)

### **CRM (Client Management)**
- 👥 Track clients, leads, prospects
- 📁 Projects linked to clients
- 📝 Log interactions (calls, emails, meetings)
- 💳 Invoice tracking (pending, paid, overdue)
- ✅ Task management
- 📈 Dashboard with real-time stats
- 🔐 Authentication-ready (Supabase)

### **Automation Ready**
- 🤖 Telegram bot integration
- ⏰ Cron job support
- 🔌 Webhook endpoints
- 📊 REST API

---

## 🔐 **SECURITY**

**Never commit secrets!** This repo uses:

- `.env` file (ignored by git) for secrets
- `.env.example` template for setup
- Environment variables for all sensitive data
- Supabase Row Level Security (RLS)

See [SECURITY.md](./SECURITY.md) for best practices.

---

## 📡 **API ENDPOINTS**

### **Projects**
```
GET  /api/projects              # List all projects
GET  /api/files?project=X       # List files in project
GET  /api/read?project=X&file=Y # Read file content
POST /api/save                  # Save file
POST /api/push                  # Git push
GET  /preview/X                 # Preview project
```

### **CRM**
```
GET  /crm                       # CRM UI
GET  /api/crm/clients           # List clients
POST /api/crm/client            # Add client
GET  /api/crm/client/{id}       # Get client
PUT  /api/crm/client/{id}       # Update client
GET  /api/crm/projects          # List projects
POST /api/crm/project           # Add project
GET  /api/crm/stats             # Dashboard stats
GET  /api/crm/invoices/pending  # Pending invoices
POST /api/crm/interaction       # Log interaction
PUT  /api/crm/invoice/{id}      # Mark invoice paid
```

---

## 🗄️ **DATABASE SCHEMA (Supabase)**

```
clients
  ├─ id (UUID)
  ├─ name, phone, email, company
  ├─ source, status, project_type
  ├─ budget, notes
  ├─ created_date, last_contact, next_followup
  └─ assigned_to

projects
  ├─ id (UUID)
  ├─ client_id → clients.id
  ├─ name, description
  ├─ start_date, deadline
  ├─ status, price, paid_amount, balance
  └─ payment_terms, files_link

interactions
  ├─ id (UUID)
  ├─ client_id → clients.id
  ├─ timestamp, type, summary
  ├─ outcome, followup_needed, followup_date

invoices
  ├─ id (UUID)
  ├─ client_id → clients.id
  ├─ project_id → projects.id
  ├─ invoice_no (unique)
  ├─ amount, due_date, status
  ├─ payment_date, upi_link, notes

tasks
  ├─ id (UUID)
  ├─ project_id → projects.id
  ├─ description, assignee, priority
  ├─ status, due_date, hours_spent
```

---

## ⚙️ **CONFIGURATION**

### **Environment Variables**

Create `.env` file (from `.env.example`):

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=1322072712
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

---

## 🏗️ **PROJECT STRUCTURE**

```
pm-dashboard/
├── server.py              # Main HTTP server (Python)
├── supabase_crm_client.py # CRM database client
├── start.sh               # Start script
├── telegram-commands.sh   # Telegram bot handler
├── .env                   # Your secrets (ignored)
├── .env.example           # Template
├── .gitignore             # Git ignore rules
├── server.log             # Server logs (ignored)
└── README.md              # This file
```

---

## 🧪 **TESTING**

```bash
# Test Supabase connection
cd ~/.nanobot/workspace/pm-dashboard
python3 -c "from supabase_crm_client import SupabaseCRMClient; crm = SupabaseCRMClient(); print(crm.get_dashboard_stats())"

# Test server
curl http://localhost:8080/api/crm/stats

# Test CRM UI
curl http://localhost:8080/crm | head -20
```

---

## 🚀 **DEPLOYMENT**

### **Option 1: Railway (Recommended)**
1. Push to GitHub
2. Create new service on Railway
3. Connect repo
4. Add environment variables (from `.env`)
5. Deploy!

### **Option 2: Render**
1. Create Web Service
2. Connect GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python server.py`
5. Add environment variables

### **Option 3: VPS (DigitalOcean, Linode, etc.)**
```bash
git clone https://github.com/yourname/pm-dashboard.git
cd pm-dashboard
pip install -r requirements.txt
# Create .env file
nohup python server.py > server.log 2>&1 &
```

---

## 📦 **REQUIREMENTS**

Create `requirements.txt`:
```
supabase>=2.0.0
python-dotenv>=1.0.0
```

Install:
```bash
pip install -r requirements.txt
```

---

## 🤝 **CONTRIBUTING**

1. Fork the repo
2. Create feature branch
3. Make changes
4. Test with `python3 -m py_compile server.py`
5. Submit PR

---

## 📄 **LICENSE**

MIT License - see LICENSE file

---

## 🆘 **HELP**

- **Setup issues?** See [SUPABASE_SETUP_GUIDE.md](./SUPABASE_SETUP_GUIDE.md)
- **Security concerns?** See [SECURITY.md](./SECURITY.md)
- **Full inventory?** See `/workspace/AUTOMATION_INVENTORY.md`

---

**Built for Electro's Web Dev Business** 🚀

*Last updated: 2026-03-22*
# Trigger redeploy
