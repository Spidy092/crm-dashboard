# Supabase CRM Setup Guide

## 🚀 Why Supabase?

- ✅ **Real PostgreSQL database** (not a spreadsheet)
- ✅ **Authentication** built-in (user login)
- ✅ **Real-time updates** (live data changes)
- ✅ **REST API** automatically generated
- ✅ **No quotas** (unlike Google Sheets)
- ✅ **Scalable** to millions of records
- ✅ **Free tier**: 500 MB database, 10K rows/month

---

## 📋 Step-by-Step Setup

### **Step 1: Create Supabase Project**

1. Go to https://supabase.com/ → Sign up / Log in
2. Click **"New Project"**
3. Fill in:
   - **Name**: `crm-dashboard` (or your business name)
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Select closest (e.g., Asia)
4. Click **"Create project"**
5. Wait 2–3 minutes for provisioning

---

### **Step 2: Create Database Tables**

Once project is ready:

1. In Supabase dashboard, go to **SQL Editor** (left sidebar)
2. Click **"New Query"**
3. Copy-paste the following SQL:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Clients table
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  phone TEXT,
  email TEXT NOT NULL,
  company TEXT NOT NULL,
  source TEXT DEFAULT 'Other',
  status TEXT DEFAULT 'Lead',
  project_type TEXT,
  budget NUMERIC,
  notes TEXT,
  created_date DATE DEFAULT CURRENT_DATE,
  last_contact DATE,
  next_followup DATE,
  assigned_to TEXT DEFAULT 'Electro',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  name TEXT NOT NULL,
  description TEXT,
  start_date DATE,
  deadline DATE,
  status TEXT DEFAULT 'Planning',
  price NUMERIC,
  paid_amount NUMERIC DEFAULT 0,
  balance NUMERIC,
  payment_terms TEXT DEFAULT '50% advance, 50% delivery',
  files_link TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Interactions table
CREATE TABLE interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  type TEXT DEFAULT 'Note',
  summary TEXT NOT NULL,
  outcome TEXT,
  followup_needed BOOLEAN DEFAULT FALSE,
  followup_date DATE
);

-- Invoices table
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  project_id UUID REFERENCES projects(id),
  invoice_no TEXT UNIQUE NOT NULL,
  amount NUMERIC NOT NULL,
  due_date DATE NOT NULL,
  status TEXT DEFAULT 'Pending',
  payment_date DATE,
  upi_link TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks table
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  description TEXT NOT NULL,
  assignee TEXT DEFAULT 'Electro',
  priority TEXT DEFAULT 'Medium',
  status TEXT DEFAULT 'Todo',
  due_date DATE,
  hours_spent NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
```

4. Click **"Run"** (bottom right)
5. You should see: "Success. No rows returned"

---

### **Step 3: Set Up Row Level Security Policies**

We need to allow authenticated users to access data.

In the same SQL Editor, run:

```sql
-- Allow all operations for authenticated users (simple policy)
-- For production, you'd want more granular policies

CREATE POLICY "Allow all for authenticated users" ON clients
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON projects
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON interactions
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON invoices
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON tasks
  FOR ALL USING (auth.role() = 'authenticated');
```

Click **"Run"**.

---

### **Step 4: Get Supabase Credentials**

1. In Supabase dashboard, go to **Settings** (gear icon) → **API**
2. You'll see:
   - **URL**: `https://your-project.supabase.co`
   - **anon public** key (starts with `eyJ...`)
   - **service_role** key (starts with `eyJ...`)

3. **Copy both keys** and your URL

---

### **Step 5: Save Credentials Securely**

We use environment variables (via `.env` file) to keep secrets out of Git.

1. Create a `.env` file in the `pm-dashboard` directory:

```bash
cd ~/.nanobot/workspace/pm-dashboard
cat > .env << EOF
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
EOF
```

2. Replace the values with your actual Supabase URL and service_role key.

3. **Important**: The `.env` file is automatically ignored by Git (see `.gitignore`). Never commit it!

**Alternative**: You can also export environment variables in your shell:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-key-here"
```

But `.env` file is easier and persists across reboots.

---

### **Step 6: Install Supabase Python Client**

```bash
pip install supabase
```

---

### **Step 7: Test Connection**

```bash
cd ~/.nanobot/workspace/pm-dashboard
python3 -c "
from supabase_crm_client import SupabaseCRMClient
crm = SupabaseCRMClient()
stats = crm.get_dashboard_stats()
print('✅ Connected! Stats:', stats)
"
```

Expected output: JSON with stats (all zeros if no data yet).

---

### **Step 8: Restart Dashboard Server**

```bash
cd pm-dashboard
pkill -f server.py
nohup python3 server.py > server.log 2>&1 &
```

---

### **Step 9: Access CRM**

Open: `http://localhost:8080/crm`

You should see:
- ✅ Stats cards (all 0 initially)
- ✅ Clients tab (empty)
- ✅ Projects tab
- ✅ Invoices tab
- ✅ "Add Client" button works

---

## 🔐 **Authentication (Optional)**

If you want to add user login to the CRM:

1. In Supabase dashboard, go to **Authentication** → **Providers**
2. Enable **Email** (passwordless or with password)
3. In your dashboard, add login page that:
   - Calls Supabase auth API
   - Stores session token
   - Passes token in requests

For now, we're using `service_role_key` which bypasses RLS (admin access). This is fine for single-user (you only).

---

## 📊 **Using the CRM**

### **Add Client via API:**
```bash
curl -X POST http://localhost:8080/api/crm/client \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ramesh Kumar",
    "phone": "9876543210",
    "email": "ramesh@example.com",
    "company": "Ramesh Restaurant",
    "project_type": "Website",
    "budget": 25000
  }'
```

### **View Stats:**
```bash
curl http://localhost:8080/api/crm/stats
```

### **List Clients:**
```bash
curl http://localhost:8080/api/crm/clients
```

---

## 🐛 **Troubleshooting**

| Error | Solution |
|-------|----------|
| `Supabase credentials not found` | Create `.env` file with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` |
| `Invalid API key` | Double-check URL and keys from Supabase settings |
| `relation "clients" does not exist` | Run the SQL to create tables |
| `permission denied for relation clients` | RLS policies not set → run the policy SQL |
| `module supabase not found` | `pip install supabase python-dotenv` |
| `Connection refused` | Server not running → restart dashboard |

---

## 🎯 **Next Steps After Setup**

1. ✅ Add your first client via web UI
2. ✅ Create a project for that client
3. ✅ Log interactions (calls, meetings)
4. ✅ Create invoices and mark paid
5. ✅ View dashboard stats update in real-time

---

## 📞 **Need Help?**

Common issues:
- **Tables not created?** Run the SQL again, check for errors
- **Can't connect?** Verify `.env` file has correct values
- **Permission errors?** Make sure RLS policies are set

**Once you've done the setup, run:**
```bash
cd ~/.nanobot/workspace
python3 verify_supabase_setup.py
```

---

**Ready to switch to a proper database?** Let me know when you've completed the steps, and I'll help verify everything is working! 🚀
