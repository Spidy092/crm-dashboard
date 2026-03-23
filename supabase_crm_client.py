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

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # dotenv not installed, will use system env vars

class SupabaseCRMClient:
    def __init__(self):
        """Initialize Supabase client from environment variables"""
        # Get credentials from environment
        url = os.getenv("SUPABASE_URL")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not service_role_key:
            raise ValueError(
                "Supabase credentials not found in environment.\n"
                "Please set:\n"
                "  SUPABASE_URL\n"
                "  SUPABASE_SERVICE_ROLE_KEY\n"
                "You can put these in a .env file (recommended) or export them."
            )

        self.supabase: Client = create_client(url, service_role_key)
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
        clean_data = {k: v for k, v in client_data.items() if v != ""}
        data = {
            "name": clean_data["name"],
            "email": clean_data["email"]
        }
        for field in ["phone", "company", "source", "status", "project_type", "budget", "notes", "created_date", "last_contact", "next_followup", "assigned_to"]:
            if field in clean_data:
                data[field] = clean_data[field]
                
        if "created_date" not in data:
            data["created_date"] = datetime.now().date().isoformat()
        if "last_contact" not in data:
            data["last_contact"] = datetime.now().date().isoformat()

        try:
            result = self.supabase.table("clients").insert(data).execute()
        except Exception as e:
            error_msg = str(e)
            # Provide helpful hints based on error type
            if "does not exist" in error_msg or "relation" in error_msg:
                raise Exception(f"Database table 'clients' does not exist. Run the SQL setup script from SETUP.md. Original error: {error_msg}") from e
            elif "permission denied" in error_msg or "row security" in error_msg or "policy" in error_msg:
                raise Exception(f"Permission denied. Check Row Level Security policies in Supabase. Original error: {error_msg}") from e
            elif "invalid credentials" in error_msg or "API key" in error_msg or "Unauthorized" in error_msg:
                raise Exception(f"Invalid Supabase credentials. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables. Original error: {error_msg}") from e
            else:
                raise Exception(f"Database error: {error_msg}") from e
        
        if result.data:
            client_id = result.data[0]['id']
            # Log interaction (non-critical - don't fail if this errors)
            try:
                self.add_interaction({
                    "client_id": client_id,
                    "summary": "Client added to CRM",
                    "type": "System",
                    "followup_needed": bool(data.get("next_followup")),
                    "followup_date": data.get("next_followup")
                })
            except Exception as e:
                # Log but don't fail client creation
                print(f"Warning: Failed to log interaction: {e}")
            return client_id
        else:
            raise Exception("Failed to add client: insert returned no data")

    def get_client(self, client_id: str) -> Optional[Dict]:
        """Get client by ID"""
        result = self.supabase.table("clients").select("*").eq("id", client_id).execute()
        return result.data[0] if result.data else None

    def update_client(self, client_id: str, updates: Dict):
        """Update client"""
        clean_updates = {k: (v if v != "" else None) for k, v in updates.items()}
        result = self.supabase.table("clients").update(clean_updates).eq("id", client_id).execute()
        return result.data

    def delete_client(self, client_id: str):
        """Delete a client"""
        result = self.supabase.table("clients").delete().eq("id", client_id).execute()
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
        clean_data = {k: v for k, v in project_data.items() if v != ""}
        data = {
            "client_id": clean_data["client_id"],
            "name": clean_data["name"]
        }
        for field in ["description", "start_date", "deadline", "status", "price", "paid_amount", "balance", "payment_terms", "files_link"]:
            if field in clean_data:
                data[field] = clean_data[field]
                
        if "start_date" not in data:
            data["start_date"] = datetime.now().date().isoformat()

        result = self.supabase.table("projects").insert(data).execute()
        return result.data[0]['id'] if result.data else None

    def update_project(self, project_id: str, updates: Dict):
        """Update project"""
        clean_updates = {k: (v if v != "" else None) for k, v in updates.items()}
        result = self.supabase.table("projects").update(clean_updates).eq("id", project_id).execute()
        return result.data
        
    def delete_project(self, project_id: str):
        """Delete a project"""
        result = self.supabase.table("projects").delete().eq("id", project_id).execute()
        return result.data

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
        clean_data = {k: v for k, v in interaction_data.items() if v != ""}
        data = {
            "client_id": clean_data["client_id"],
            "summary": clean_data["summary"]
        }
        for field in ["timestamp", "type", "outcome", "followup_needed", "followup_date"]:
            if field in clean_data:
                data[field] = clean_data[field]
                
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()

        result = self.supabase.table("interactions").insert(data).execute()

        # Update client's last_contact and next_followup
        if data.get("followup_needed") and data.get("followup_date"):
            self.update_client(data["client_id"], {
                "last_contact": datetime.now().date().isoformat(),
                "next_followup": data["followup_date"]
            })

        return result.data[0]['id'] if result.data else None

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
        
        clean_data = {k: v for k, v in invoice_data.items() if v != ""}
        
        data = {
            "client_id": clean_data["client_id"],
            "amount": clean_data["amount"],
            "due_date": clean_data["due_date"],
            "invoice_no": clean_data.get("invoice_no", f"INV-{datetime.now().strftime('%Y%m%d')}-{next_num:03d}")
        }
        
        for field in ["project_id", "status", "payment_date", "upi_link", "notes"]:
            if field in clean_data:
                data[field] = clean_data[field]

        result = self.supabase.table("invoices").insert(data).execute()
        return result.data[0]['id'] if result.data else None

    def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Get invoice by ID"""
        result = self.supabase.table("invoices").select("*").eq("id", invoice_id).execute()
        return result.data[0] if result.data else None

    def update_invoice(self, invoice_id: str, updates: Dict):
        """Update invoice"""
        result = self.supabase.table("invoices").update(updates).eq("id", invoice_id).execute()
        return result.data

    def delete_invoice(self, invoice_id: str):
        """Delete an invoice"""
        result = self.supabase.table("invoices").delete().eq("id", invoice_id).execute()
        return result.data

    def get_pending_invoices(self) -> List[Dict]:
        """Get all pending/overdue invoices"""
        result = self.supabase.table("invoices").select("*").in_("status", ["Pending", "Overdue"]).execute()
        return result.data

    def sync_project_financials(self, project_id: str):
        """Recalculate and update a project's paid_amount and balance from its paid invoices"""
        try:
            project = self.get_project(project_id)
            if not project:
                return
            # Sum all paid invoices for this project
            paid_invoices = self.supabase.table("invoices").select("amount").eq("project_id", project_id).eq("status", "Paid").execute()
            paid_amount = sum(float(inv.get("amount", 0)) for inv in (paid_invoices.data or []))
            price = float(project.get("price") or 0)
            balance = price - paid_amount
            self.supabase.table("projects").update({
                "paid_amount": paid_amount,
                "balance": balance
            }).eq("id", project_id).execute()
        except Exception as e:
            print(f"Warning: Failed to sync project financials for {project_id}: {e}")

    def mark_invoice_paid(self, invoice_id: str, payment_date: str = None):
        """Mark invoice as paid and sync linked project financials"""
        if not payment_date:
            payment_date = datetime.now().date().isoformat()
        # Get invoice first to find project_id
        invoice = self.get_invoice(invoice_id)
        result = self.update_invoice(invoice_id, {
            "status": "Paid",
            "payment_date": payment_date
        })
        # Sync project paid_amount & balance if linked
        if invoice and invoice.get("project_id"):
            self.sync_project_financials(invoice["project_id"])
        return result

    def get_overdue_invoices(self) -> List[Dict]:
        """Get overdue invoices (due date < today and status not Paid)"""
        today = datetime.now().date().isoformat()
        result = self.supabase.table("invoices").select("*").lt("due_date", today).neq("status", "Paid").execute()
        return result.data

    def generate_invoice_pdf(self, invoice_id: str) -> bytes:
        """Generate PDF invoice for download"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib.units import inch, cm
            from io import BytesIO
        except ImportError:
            raise ImportError("reportlab not installed. Run: pip install reportlab")
        
        # Get invoice data
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Get client and project data
        client = self.get_client(invoice["client_id"])
        project = None
        if invoice.get("project_id"):
            project = self.get_project(invoice["project_id"])
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch, leftMargin=1*inch, rightMargin=1*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#F4A31E')  # Your accent color
        )
        
        # Header: Your business info
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 12))
        
        # Your company details (customize these)
        company_info = [
            ["Your Business Name", ""],
            ["Web Development Services", ""],
            ["Bangalore, India", ""],
            ["contact@yourbusiness.com", ""],
            ["+91 9876543210", ""]
        ]
        
        company_table = Table(company_info, colWidths=[3*inch, 2*inch])
        company_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(company_table)
        story.append(Spacer(1, 30))
        
        # Invoice details
        invoice_info = [
            ["Invoice Number:", invoice.get("invoice_no", "N/A")],
            ["Date:", datetime.now().strftime("%B %d, %Y")],
            ["Due Date:", invoice.get("due_date", "N/A")],
            ["Status:", invoice.get("status", "Pending")]
        ]
        
        invoice_table = Table(invoice_info, colWidths=[1.5*inch, 3*inch])
        invoice_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(invoice_table)
        story.append(Spacer(1, 30))
        
        # Bill To (Client)
        if client:
            story.append(Paragraph("Bill To:", styles['Heading3']))
            client_info = [
                [client.get("name", "N/A"), ""],
                [client.get("company", "N/A"), ""],
                [client.get("email", "N/A"), ""],
                [client.get("phone", "N/A"), ""]
            ]
            client_table = Table(client_info, colWidths=[3*inch, 2*inch])
            client_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(client_table)
            story.append(Spacer(1, 20))
        
        # Project (if linked)
        if project:
            story.append(Paragraph("Project:", styles['Heading3']))
            project_info = [
                [project.get("name", "N/A"), ""],
                [project.get("description", "")[:100] + ("..." if len(project.get("description", "")) > 100 else ""), ""]
            ]
            project_table = Table(project_info, colWidths=[3*inch, 2*inch])
            project_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(project_table)
            story.append(Spacer(1, 20))
        
        # Amount Table
        story.append(Paragraph("Invoice Amount:", styles['Heading3']))
        amount_data = [
            ["Description", "Amount (₹)"],
            ["Service Fee", f"₹{float(invoice.get('amount', 0)):,.2f}"]
        ]
        
        if project:
            amount_data.insert(1, ["Project", project.get("name", "")])
        
        amount_table = Table(amount_data, colWidths=[4*inch, 1.5*inch])
        amount_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4A31E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(amount_table)
        story.append(Spacer(1, 30))
        
        # Payment Terms
        story.append(Paragraph("Payment Terms:", styles['Heading3']))
        terms = invoice.get("payment_terms", "50% advance, 50% on delivery")
        story.append(Paragraph(terms, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # UPI/QR (if available)
        if invoice.get("upi_link"):
            story.append(Paragraph("Pay via UPI:", styles['Heading3']))
            story.append(Paragraph(invoice["upi_link"], styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Notes
        if invoice.get("notes"):
            story.append(Paragraph("Notes:", styles['Heading3']))
            story.append(Paragraph(invoice["notes"], styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 50))
        story.append(Paragraph("Thank you for your business!", styles['Italic']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    # ========== TASKS ==========

    def add_task(self, task_data: Dict) -> str:
        """Create a task"""
        data = {
            "project_id": task_data["project_id"],
            "description": task_data["description"],
            "assignee": task_data.get("assignee", "Electro"),
            "priority": task_data.get("priority", "Medium"),
            "status": task_data.get("status", "Todo"),
            "due_date": task_data.get("due_date"),
            "hours_spent": task_data.get("hours_spent", 0)
        }
        
        data = {k: (v if v != "" else None) for k, v in data.items()}

        result = self.supabase.table("tasks").insert(data).execute()
        return result.data[0]['id'] if result.data else None

    def list_tasks(self, status: str = None) -> List[Dict]:
        """List all tasks"""
        query = self.supabase.table("tasks").select("*")
        if status:
            query = query.eq("status", status)
        result = query.order("due_date", desc=False).execute()
        return result.data

    def get_project_tasks(self, project_id: str) -> List[Dict]:
        """Get all tasks for a project"""
        result = self.supabase.table("tasks").select("*").eq("project_id", project_id).execute()
        return result.data

    def update_task(self, task_id: str, updates: Dict):
        """Update task"""
        result = self.supabase.table("tasks").update(updates).eq("id", task_id).execute()
        return result.data

    def delete_task(self, task_id: str):
        """Delete a task"""
        result = self.supabase.table("tasks").delete().eq("id", task_id).execute()
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
