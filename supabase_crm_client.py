#!/usr/bin/env python3
"""
CRM Client - Supabase Integration
Replaces Google Sheets with proper PostgreSQL database
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
import os

class SupabaseCRMClient:
    def __init__(self):
        """Initialize Supabase client from config file"""
        config_path = Path.home() / ".nanobot" / "workspace" / "supabase_config.json"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Supabase config not found at {config_path}\n"
                "Create it with your Supabase URL and keys."
            )

        config = json.loads(config_path.read_text())
        self.supabase: Client = create_client(
            config["url"],
            config["service_role_key"]  # Use service_role for admin access
        )
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Check if tables exist, create if not"""
        # Tables should already exist from SQL script
        # This just verifies connection
        try:
            # Test query
            result = self.supabase.table("clients").select("id").limit(1).execute()
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            raise

    # ========== CLIENTS ==========

    def add_client(self, client_data: Dict) -> str:
        """Add a new client"""
        # Generate client ID (human-readable)
        result = self.supabase.table("clients").select("id").execute()
        next_num = len(result.data) + 1
        client_id = f"CLI-{next_num:03d}"

        data = {
            "id": client_id,
            "name": client_data["name"],
            "phone": client_data.get("phone"),
            "email": client_data["email"],
            "company": client_data["company"],
            "source": client_data.get("source", "Other"),
            "status": client_data.get("status", "Lead"),
            "project_type": client_data["project_type"],
            "budget": client_data.get("budget"),
            "notes": client_data.get("notes", ""),
            "created_date": client_data.get("created_date", datetime.now().date().isoformat()),
            "last_contact": client_data.get("last_contact", datetime.now().date().isoformat()),
            "next_followup": client_data.get("next_followup"),
            "assigned_to": client_data.get("assigned_to", "Electro")
        }

        result = self.supabase.table("clients").insert(data).execute()
        if result.data:
            # Log interaction
            self.add_interaction({
                "client_id": client_id,
                "summary": "Client added to CRM",
                "type": "System",
                "followup_needed": bool(data.get("next_followup"))
            })
            return client_id
        else:
            raise Exception("Failed to add client")

    def get_client(self, client_id: str) -> Optional[Dict]:
        """Get client by ID"""
        result = self.supabase.table("clients").select("*").eq("id", client_id).execute()
        return result.data[0] if result.data else None

    def update_client(self, client_id: str, updates: Dict):
        """Update client"""
        result = self.supabase.table("clients").update(updates).eq("id", client_id).execute()
        return result.data

    def list_clients(self, status: str = None) -> List[Dict]:
        """List all clients, optionally filtered by status"""
        query = self.supabase.table("clients").select("*")
        if status:
            query = query.eq("status", status)
        result = query.order("created_date", desc=True).execute()
        return result.data

    def search_clients(self, query: str) -> List[Dict]:
        """Search clients by name, company, phone, email"""
        # Supabase doesn't have full-text search easily, use ILIKE
        result = self.supabase.table("clients").select("*").execute()
        all_clients = result.data
        q = query.lower()
        return [c for c in all_clients if
                q in c.get("name", "").lower() or
                q in c.get("company", "").lower() or
                q in c.get("phone", "") or
                q in c.get("email", "").lower()]

    # ========== PROJECTS ==========

    def add_project(self, project_data: Dict) -> str:
        """Add a new project"""
        # Generate project ID
        result = self.supabase.table("projects").select("id").execute()
        next_num = len(result.data) + 1
        project_id = f"PROJ-{next_num:03d}"

        data = {
            "id": project_id,
            "client_id": project_data["client_id"],
            "name": project_data["name"],
            "description": project_data.get("description", ""),
            "start_date": project_data.get("start_date", datetime.now().date().isoformat()),
            "deadline": project_data.get("deadline"),
            "status": project_data.get("status", "Planning"),
            "price": project_data.get("price", 0),
            "paid_amount": project_data.get("paid_amount", 0),
            "balance": project_data.get("balance", project_data.get("price", 0)),
            "payment_terms": project_data.get("payment_terms", "50% advance, 50% delivery"),
            "files_link": project_data.get("files_link", "")
        }

        result = self.supabase.table("projects").insert(data).execute()
        return project_id if result.data else None

    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get project by ID"""
        result = self.supabase.table("projects").select("*").eq("id", project_id).execute()
        return result.data[0] if result.data else None

    def update_project(self, project_id: str, updates: Dict):
        """Update project"""
        result = self.supabase.table("projects").update(updates).eq("id", project_id).execute()
        return result.data

    def list_projects(self, status: str = None) -> List[Dict]:
        """List all projects"""
        query = self.supabase.table("projects").select("*")
        if status:
            query = query.eq("status", status)
        result = query.order("start_date", desc=True).execute()
        return result.data

    def get_client_projects(self, client_id: str) -> List[Dict]:
        """Get all projects for a client"""
        result = self.supabase.table("projects").select("*").eq("client_id", client_id).execute()
        return result.data

    # ========== INTERACTIONS ==========

    def add_interaction(self, interaction_data: Dict) -> str:
        """Log an interaction"""
        # Generate ID
        result = self.supabase.table("interactions").select("id").execute()
        next_num = len(result.data) + 1
        interaction_id = f"INT-{next_num:03d}"

        data = {
            "id": interaction_id,
            "client_id": interaction_data["client_id"],
            "timestamp": interaction_data.get("timestamp", datetime.now().isoformat()),
            "type": interaction_data.get("type", "Note"),
            "summary": interaction_data["summary"],
            "outcome": interaction_data.get("outcome", ""),
            "followup_needed": interaction_data.get("followup_needed", False),
            "followup_date": interaction_data.get("followup_date")
        }

        result = self.supabase.table("interactions").insert(data).execute()

        # Update client's last_contact and next_followup
        if data["followup_needed"] and data["followup_date"]:
            self.update_client(data["client_id"], {
                "last_contact": datetime.now().date().isoformat(),
                "next_followup": data["followup_date"]
            })

        return interaction_id

    def get_interactions(self, client_id: str = None, limit: int = 50) -> List[Dict]:
        """Get interactions, optionally filtered by client"""
        query = self.supabase.table("interactions").select("*")
        if client_id:
            query = query.eq("client_id", client_id)
        result = query.order("timestamp", desc=True).limit(limit).execute()
        return result.data

    # ========== INVOICES ==========

    def add_invoice(self, invoice_data: Dict) -> str:
        """Create an invoice"""
        result = self.supabase.table("invoices").select("id").execute()
        next_num = len(result.data) + 1
        invoice_id = f"INV-{next_num:03d}"

        data = {
            "id": invoice_id,
            "client_id": invoice_data["client_id"],
            "project_id": invoice_data.get("project_id"),
            "invoice_no": invoice_data.get("invoice_no", f"INV-{datetime.now().strftime('%Y%m%d')}-{next_num:03d}"),
            "amount": invoice_data["amount"],
            "due_date": invoice_data["due_date"],
            "status": invoice_data.get("status", "Pending"),
            "payment_date": invoice_data.get("payment_date"),
            "upi_link": invoice_data.get("upi_link", ""),
            "notes": invoice_data.get("notes", "")
        }

        result = self.supabase.table("invoices").insert(data).execute()
        return invoice_id

    def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Get invoice by ID"""
        result = self.supabase.table("invoices").select("*").eq("id", invoice_id).execute()
        return result.data[0] if result.data else None

    def update_invoice(self, invoice_id: str, updates: Dict):
        """Update invoice"""
        result = self.supabase.table("invoices").update(updates).eq("id", invoice_id).execute()
        return result.data

    def get_pending_invoices(self) -> List[Dict]:
        """Get all pending/overdue invoices"""
        result = self.supabase.table("invoices").select("*").in_("status", ["Pending", "Overdue"]).execute()
        return result.data

    def mark_invoice_paid(self, invoice_id: str, payment_date: str = None):
        """Mark invoice as paid"""
        if not payment_date:
            payment_date = datetime.now().date().isoformat()
        return self.update_invoice(invoice_id, {
            "status": "Paid",
            "payment_date": payment_date
        })

    def get_overdue_invoices(self) -> List[Dict]:
        """Get overdue invoices (due date < today and status not Paid)"""
        today = datetime.now().date().isoformat()
        result = self.supabase.table("invoices").select("*").lt("due_date", today).neq("status", "Paid").execute()
        return result.data

    # ========== TASKS ==========

    def add_task(self, task_data: Dict) -> str:
        """Create a task"""
        result = self.supabase.table("tasks").select("id").execute()
        next_num = len(result.data) + 1
        task_id = f"TASK-{next_num:03d}"

        data = {
            "id": task_id,
            "project_id": task_data["project_id"],
            "description": task_data["description"],
            "assignee": task_data.get("assignee", "Electro"),
            "priority": task_data.get("priority", "Medium"),
            "status": task_data.get("status", "Todo"),
            "due_date": task_data.get("due_date"),
            "hours_spent": task_data.get("hours_spent", 0)
        }

        result = self.supabase.table("tasks").insert(data).execute()
        return task_id

    def get_project_tasks(self, project_id: str) -> List[Dict]:
        """Get all tasks for a project"""
        result = self.supabase.table("tasks").select("*").eq("project_id", project_id).execute()
        return result.data

    def update_task(self, task_id: str, updates: Dict):
        """Update task"""
        result = self.supabase.table("tasks").update(updates).eq("id", task_id).execute()
        return result.data

    # ========== DASHBOARD STATS ==========

    def get_dashboard_stats(self) -> Dict:
        """Get CRM statistics for dashboard"""
        clients = self.list_clients()
        projects = self.list_projects()
        pending_invoices = self.get_pending_invoices()
        overdue_invoices = self.get_overdue_invoices()

        total_revenue = sum(float(p.get("price", 0)) for p in projects if p.get("price"))
        total_paid = sum(float(p.get("paid_amount", 0)) for p in projects)
        pending_amount = sum(float(inv.get("amount", 0)) for inv in pending_invoices)

        leads = [c for c in clients if c.get("status") == "Lead"]
        prospects = [c for c in clients if c.get("status") == "Prospect"]
        active_projects = [p for p in projects if p.get("status") not in ["Delivered", "Cancelled"]]

        return {
            "total_clients": len(clients),
            "leads": len(leads),
            "prospects": len(prospects),
            "active_projects": len(active_projects),
            "total_revenue": total_revenue,
            "total_paid": total_paid,
            "balance_due": total_revenue - total_paid,
            "pending_invoices_count": len(pending_invoices),
            "pending_invoices_amount": pending_amount,
            "overdue_invoices_count": len(overdue_invoices),
            "overdue_amount": sum(float(inv.get("amount", 0)) for inv in overdue_invoices)
        }

    # ========== REAL-TIME SUBSCRIPTIONS ==========

    def subscribe_to_table(self, table_name: str, callback):
        """Subscribe to real-time changes on a table"""
        # This would use Supabase real-time
        # For now, return a placeholder
        print(f"Real-time subscription for {table_name} not implemented in this version")
        return None


# Quick test
if __name__ == "__main__":
    print("Supabase CRM Client Test")
    print("-----------------------")
    try:
        client = SupabaseCRMClient()
        print("✅ Connected to Supabase")

        stats = client.get_dashboard_stats()
        print("\nDashboard Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")

        print("\n✅ CRM is ready to use!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Created Supabase project")
        print("2. Run the SQL to create tables")
        print("3. Saved credentials to ~/.nanobot/workspace/supabase_config.json")
