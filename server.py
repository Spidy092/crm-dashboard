#!/usr/bin/env python3
"""
📱 Project Manager Dashboard
Local web server for managing projects on Android/Termux
Access: http://localhost:8080 or http://YOUR_IP:8080
"""

import os
import json
import subprocess
import mimetypes
import traceback
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import sys
sys.path.insert(0, os.path.dirname(__file__))
try:
    from supabase_crm_client import SupabaseCRMClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Configuration
PORT = 8080
WORKSPACE = Path.home() / ".nanobot" / "workspace"
PROJECTS = {
    "coelum9": WORKSPACE / "coelum9",
    "kruthi": WORKSPACE / "kruthi",
    "acumen9-clone": WORKSPACE / "acumen9-clone",
    "webdev-company": WORKSPACE / "webdev-company",
}

class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler for project dashboard"""
    
    def is_authenticated(self):
        if not hasattr(self.server, "session_token"):
            return True
        from http import cookies
        if "Cookie" in self.headers:
            c = cookies.SimpleCookie(self.headers["Cookie"])
            if "crm_session" in c:
                return c["crm_session"].value == self.server.session_token
        return False

    def serve_login_ui(self):
        """Serve simple login page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CRM Login</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { background: #0a0a0a; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .login-box { background: #141414; padding: 40px; border-radius: 12px; border: 1px solid #333; width: 90%; max-width: 400px; text-align: center; }
                input { width: 100%; padding: 12px; margin: 20px 0; background: #000; border: 1px solid #333; color: white; border-radius: 8px; box-sizing: border-box; }
                button { background: #F4A31E; color: black; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; width: 100%; cursor: pointer; }
                .error { color: #ef4444; margin-bottom: 10px; display: none; }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h2>CRM Secure Login</h2>
                <div id="err" class="error">Invalid password</div>
                <form id="loginForm">
                    <input type="password" name="password" placeholder="Enter admin password" required>
                    <button type="submit">Login</button>
                </form>
            </div>
            <script>
                document.getElementById('loginForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const pwd = new FormData(e.target).get('password');
                    const res = await fetch('/api/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({password: pwd})
                    });
                    if (res.ok) { window.location.reload(); }
                    else { document.getElementById('err').style.display = 'block'; }
                });
            </script>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
        
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # Routes
        if path == "/" or path == "/index.html":
            self.serve_dashboard()
        elif path == "/api/projects":
            self.serve_projects_json()
        elif path.startswith("/api/files"):
            project = params.get("project", [""])[0]
            self.serve_files_json(project)
        elif path.startswith("/api/read"):
            project = params.get("project", [""])[0]
            file = params.get("file", [""])[0]
            self.serve_file_content(project, file)
        elif path == "/crm":
            if not self.is_authenticated():
                self.serve_login_ui()
                return
            self.serve_crm_ui()
        elif path.startswith("/api/crm/"):
            if not self.is_authenticated():
                self.send_response(401)
                self.end_headers()
                return
            if path == "/api/crm/clients":
                self.handle_crm_list_clients()
            elif path == "/api/crm/projects":
                self.handle_crm_list_projects()
            elif path == "/api/crm/stats":
                self.handle_crm_stats()
            elif path == "/api/crm/invoices/pending":
                self.handle_crm_pending_invoices()
            elif path == "/api/crm/tasks":
                self.handle_crm_list_tasks()
            elif path.startswith("/api/crm/client/"):
                client_id = path.split("/")[4]
                if path.endswith("/interactions"):
                    self.handle_crm_get_client_interactions(client_id)
                else:
                    self.handle_crm_get_client(client_id)
        elif path.startswith("/preview/"):
            project = path.split("/")[2]
            parts = path.split("/")
            project = parts[2] if len(parts) > 2 else ""
            if len(parts) > 3:
                subpath = "/".join(parts[3:])
                self.serve_project_file(project, subpath)
            else:
                self.serve_preview(project)
        elif path.startswith("/project/"):
            parts = path.split("/")
            project = parts[2] if len(parts) > 2 else ""
            file_path = "/".join(parts[3:]) if len(parts) > 3 else ""
            self.serve_project_file(project, file_path)
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == "/api/push":
            self.handle_push(data)
        elif path == "/api/login":
            pwd = data.get("password")
            if pwd == os.environ.get("ADMIN_PASSWORD", "admin123"):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Set-Cookie', f'crm_session={self.server.session_token}; Path=/; HttpOnly')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            else:
                self.send_json({"error": "Invalid password"}, 401)
        elif path == "/api/save":
            self.handle_save(data)
        elif path == "/api/create":
            self.handle_create(data)
        elif path.startswith("/api/crm/"):
            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return
            if path == "/api/crm/client":
                self.handle_crm_add_client(data)
            elif path == "/api/crm/project":
                self.handle_crm_add_project(data)
            elif path == "/api/crm/invoice":
                self.handle_crm_add_invoice(data)
            elif path == "/api/crm/task":
                self.handle_crm_add_task(data)
            elif path == "/api/crm/interaction":
                self.handle_crm_add_interaction(data)
            else:
                self.send_error(404)
        elif path == "/api/crm/invoice":
            self.handle_crm_add_invoice(data)
        elif path == "/health":
            self.handle_health()
        elif path == "/api/crm/stats":
            self.handle_crm_stats()
        elif path == "/api/crm/invoices/pending":
            self.handle_crm_pending_invoices()
        elif path == "/api/crm/tasks":
            self.handle_crm_list_tasks()
        elif path == "/api/crm/interaction":
            self.handle_crm_add_interaction(data)
        else:
            self.send_error(404)
    
    def do_PUT(self):
        """Handle PUT requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
            
        if path.startswith("/api/crm/"):
            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return
        
        if path.startswith("/api/crm/client/"):
            client_id = path.split("/")[4]
            self.handle_crm_update_client(client_id, data)
        elif path.startswith("/api/crm/invoice/"):
            invoice_id = path.split("/")[4]
            self.handle_crm_mark_invoice_paid(invoice_id)
        elif path.startswith("/api/crm/project/"):
            project_id = path.split("/")[4]
            self.handle_crm_update_project(project_id, data)
        elif path.startswith("/api/crm/task/"):
            task_id = path.split("/")[4]
            self.handle_crm_update_task(task_id, data)
        else:
            self.send_error(404)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith("/api/crm/"):
            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return
                
            parts = path.split("/")
            if len(parts) >= 5:
                entity = parts[3]
                entity_id = parts[4]
                
                try:
                    crm = SupabaseCRMClient()
                    if entity == "client":
                        crm.delete_client(entity_id)
                    elif entity == "project":
                        crm.delete_project(entity_id)
                    elif entity == "invoice":
                        crm.delete_invoice(entity_id)
                    elif entity == "task":
                        crm.delete_task(entity_id)
                    else:
                        self.send_json({"error": "Unknown entity"}, 400)
                        return
                    self.send_json({"success": True})
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
            else:
                self.send_error(404)
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve main dashboard HTML"""
        html = self.get_dashboard_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    
    # ========== CRM HANDLERS ==========
    
    def serve_crm_ui(self):
        """Serve CRM page"""
        html = self.get_crm_ui_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_crm_list_clients(self):
        """Return all clients as JSON"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        try:
            crm = SupabaseCRMClient()
            clients = crm.list_clients()
            self.send_json({"clients": clients})
        except Exception as e:
            self.send_json({"error": str(e), "setup_required": True}, 500)
    
    def handle_crm_add_client(self, data):
        """Add new client"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        
        required = ["name", "phone", "email", "company", "project_type"]
        for field in required:
            if not data.get(field):
                self.send_json({"error": f"Missing required field: {field}"}, 400)
                return
        
        try:
            crm = SupabaseCRMClient()
            client_id = crm.add_client(data)
            self.send_json({"success": True, "client_id": client_id})
        except Exception as e:
            # Log full traceback to stderr (captured by Render logs)
            traceback.print_exc()
            self.send_json({"error": str(e), "type": type(e).__name__}, 500)
    
    def handle_crm_get_client(self, client_id):
        """Get a specific client"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed"}, 500)
            return
            
        try:
            crm = SupabaseCRMClient()
            client = crm.get_client(client_id)
            if client:
                self.send_json({"success": True, "client": client})
            else:
                self.send_json({"error": "Client not found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_crm_get_client_interactions(self, client_id):
        """Get interactions for a specific client"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed"}, 500)
            return
        
        try:
            crm = SupabaseCRMClient()
            interactions = crm.get_interactions(client_id)
            self.send_json({"success": True, "interactions": interactions})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_crm_update_client(self, client_id, data):
        """Update client"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        try:
            crm = SupabaseCRMClient()
            crm.update_client(client_id, data)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_crm_update_project(self, project_id, data):
        """Update project"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        try:
            crm = SupabaseCRMClient()
            crm.update_project(project_id, data)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_crm_list_projects(self):
        """List all projects"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        try:
            crm = SupabaseCRMClient()
            projects = crm.list_projects()
            self.send_json({"projects": projects})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_crm_add_project(self, data):
        """Add new project"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        
        required = ["client_id", "name", "price"]
        for field in required:
            if not data.get(field):
                self.send_json({"error": f"Missing required field: {field}"}, 400)
                return
        
        try:
            crm = SupabaseCRMClient()
            project_id = crm.add_project(data)
            self.send_json({"success": True, "project_id": project_id})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_crm_add_invoice(self, data):
        """Add new invoice"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
            
        required = ["client_id", "amount", "due_date"]
        for field in required:
            if not data.get(field):
                self.send_json({"error": f"Missing required field: {field}"}, 400)
                return
                
        try:
            crm = SupabaseCRMClient()
            invoice_id = crm.add_invoice(data)
            # If invoice is created as Paid directly, sync project financials immediately
            if data.get("project_id") and data.get("status") == "Paid":
                crm.sync_project_financials(data["project_id"])
            self.send_json({"success": True, "invoice_id": invoice_id})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_crm_stats(self):
        """Get CRM dashboard stats"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        try:
            crm = SupabaseCRMClient()
            stats = crm.get_dashboard_stats()
            self.send_json(stats)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_crm_pending_invoices(self):
        """List pending invoices"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        try:
            crm = SupabaseCRMClient()
            invoices = crm.get_pending_invoices()
            self.send_json({"invoices": invoices})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_crm_add_interaction(self, data):
        """Log interaction"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        
        if not data.get("client_id") or not data.get("summary"):
            self.send_json({"error": "client_id and summary required"}, 400)
            return
        
        try:
            crm = SupabaseCRMClient()
            interaction_id = crm.add_interaction(data)
            self.send_json({"success": True, "interaction_id": interaction_id})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_crm_mark_invoice_paid(self, invoice_id):
        """Mark invoice as paid via PUT"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed. Run: pip install supabase", "setup_required": True}, 500)
            return
        try:
            crm = SupabaseCRMClient()
            crm.mark_invoice_paid(invoice_id)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_health(self):
        """Health check endpoint"""
        from datetime import datetime
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "supabase_available": SUPABASE_AVAILABLE
        }
        # Test Supabase connection if available
        if SUPABASE_AVAILABLE:
            try:
                crm = SupabaseCRMClient()
                stats = crm.get_dashboard_stats()
                health["supabase_connected"] = True
                health["database"] = "connected"
            except Exception as e:
                health["supabase_connected"] = False
                health["database"] = f"error: {str(e)}"
        else:
            health["supabase_connected"] = False
            health["database"] = "supabase package not installed"
        
        self.send_json(health)
    
    def handle_crm_list_tasks(self):
        """List tasks"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed", "setup_required": True}, 500)
            return
            
        try:
            crm = SupabaseCRMClient()
            tasks = crm.list_tasks()
            self.send_json({"success": True, "tasks": tasks})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_crm_add_task(self, data):
        """Add new task"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed"}, 500)
            return
            
        try:
            crm = SupabaseCRMClient()
            task_id = crm.add_task(data)
            self.send_json({"success": True, "task_id": task_id})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_crm_update_task(self, task_id, data):
        """Update task"""
        if not SUPABASE_AVAILABLE:
            self.send_json({"error": "Supabase not installed"}, 500)
            return
            
        try:
            crm = SupabaseCRMClient()
            crm.update_task(task_id, data)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def serve_projects_json(self):
        """Return list of projects as JSON"""
        projects = []
        for name, path in PROJECTS.items():
            if path.exists():
                files = list(self.get_project_files(path))
                projects.append({
                    "name": name,
                    "path": str(path),
                    "files": len(files),
                    "size": self.get_dir_size(path)
                })
        
        self.send_json({"projects": projects})
    
    def serve_files_json(self, project):
        """Return files in a project"""
        if project not in PROJECTS:
            self.send_json({"error": "Project not found"}, 404)
            return
        
        path = PROJECTS[project]
        files = []
        
        for f in self.get_project_files(path):
            rel_path = f.relative_to(path)
            files.append({
                "name": f.name,
                "path": str(rel_path),
                "size": f.stat().st_size,
                "type": self.get_file_type(f)
            })
        
        self.send_json({"files": files})
    
    def serve_file_content(self, project, file):
        """Return file content"""
        if project not in PROJECTS:
            self.send_json({"error": "Project not found"}, 404)
            return
        
        file_path = PROJECTS[project] / file
        
        if not file_path.exists():
            self.send_json({"error": "File not found"}, 404)
            return
        
        try:
            content = file_path.read_text(encoding='utf-8')
            self.send_json({
                "content": content,
                "path": file,
                "size": file_path.stat().st_size
            })
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def serve_preview(self, project):
        """Serve project for preview (like a web server)"""
        if project not in PROJECTS:
            self.send_error(404)
            return
        
        path = PROJECTS[project]
        
        # Try common index files
        for index in ["index.shtml", "index.html", "index.htm"]:
            index_path = path / index
            if index_path.exists():
                content = index_path.read_text(encoding='utf-8')
                # Process SSI includes (basic)
                content = self.process_ssi(content, path)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode())
                return
        
        self.send_error(404, "No index file found")
    
    def serve_project_file(self, project, file_path):
        """Serve a specific file from a project"""
        if project not in PROJECTS:
            self.send_error(404)
            return
        
        full_path = PROJECTS[project] / file_path
        
        if not full_path.exists():
            self.send_error(404)
            return
        
        mime_type = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
        
        try:
            if mime_type.startswith("text/") or mime_type in ["application/javascript", "application/json"]:
                content = full_path.read_text(encoding='utf-8')
                self.send_response(200)
                self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                content = full_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_push(self, data):
        """Push project to GitHub"""
        project = data.get("project", "")
        message = data.get("message", "Update from dashboard")
        
        if project not in PROJECTS:
            self.send_json({"error": "Project not found"}, 404)
            return
        
        path = PROJECTS[project]
        
        try:
            # Git add
            subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
            
            # Git commit
            result = subprocess.run(
                ["git", "-C", str(path), "commit", "-m", message],
                capture_output=True, text=True
            )
            
            if result.returncode != 0 and "nothing to commit" in result.stdout:
                self.send_json({"status": "no_changes", "message": "Nothing to commit"})
                return
            
            # Git push
            result = subprocess.run(
                ["git", "-C", str(path), "push"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                self.send_json({"status": "success", "message": "Pushed to GitHub!"})
            else:
                self.send_json({"status": "error", "message": result.stderr})
                
        except subprocess.TimeoutExpired:
            self.send_json({"status": "timeout", "message": "Push timed out"})
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)})
    
    def handle_save(self, data):
        """Save file content"""
        project = data.get("project", "")
        file = data.get("file", "")
        content = data.get("content", "")
        
        if project not in PROJECTS:
            self.send_json({"error": "Project not found"}, 404)
            return
        
        file_path = PROJECTS[project] / file
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            self.send_json({"status": "success", "message": "File saved!"})
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)})
    
    def handle_create(self, data):
        """Create new file"""
        project = data.get("project", "")
        file = data.get("file", "")
        content = data.get("content", "")
        
        if project not in PROJECTS:
            self.send_json({"error": "Project not found"}, 404)
            return
        
        file_path = PROJECTS[project] / file
        
        if file_path.exists():
            self.send_json({"error": "File already exists"}, 400)
            return
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            self.send_json({"status": "success", "message": "File created!"})
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)})
    
    def process_ssi(self, content, base_path):
        """Process basic SSI includes"""
        import re
        
        def replace_include(match):
            include_file = match.group(1)
            include_path = base_path / include_file
            if include_path.exists():
                return include_path.read_text(encoding='utf-8')
            return f"<!-- Include not found: {include_file} -->"
        
        # Replace <!--#include file="..." -->
        content = re.sub(
            r'<!--#include\s+file="([^"]+)"\s*-->',
            replace_include,
            content
        )
        
        # Replace <!--#include virtual="..." -->
        content = re.sub(
            r'<!--#include\s+virtual="([^"]+)"\s*-->',
            replace_include,
            content
        )
        
        return content
    
    def get_project_files(self, path, extensions=None):
        """Get all files in a project"""
        if extensions is None:
            extensions = {'.html', '.shtml', '.css', '.js', '.json', '.md', '.txt', '.php'}
        
        for f in path.rglob("*"):
            if f.is_file() and not any(x in str(f) for x in ['.git/', 'node_modules/']):
                if f.suffix.lower() in extensions or not extensions:
                    yield f
    
    def get_dir_size(self, path):
        """Get directory size in bytes"""
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total
    
    def get_file_type(self, path):
        """Get file type category"""
        ext = path.suffix.lower()
        types = {
            '.html': 'html', '.shtml': 'html', '.htm': 'html',
            '.css': 'css',
            '.js': 'javascript',
            '.json': 'json',
            '.md': 'markdown',
            '.png': 'image', '.jpg': 'image', '.jpeg': 'image', '.gif': 'image', '.svg': 'image', '.webp': 'image',
            '.php': 'php',
        }
        return types.get(ext, 'other')
    
    def send_json(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def get_dashboard_html(self):
        """Generate dashboard HTML"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📱 Project Dashboard</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0a0a0a;
            --card: #141414;
            --border: #222;
            --text: #fff;
            --muted: #888;
            --accent: #F4A31E;
            --green: #22c55e;
            --red: #ef4444;
            --blue: #3b82f6;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        .header {
            background: var(--card);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.2rem;
            font-weight: 700;
        }
        .logo i { color: var(--accent); }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            color: var(--green);
        }
        .status::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--green);
            border-radius: 50%;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }
        .grid {
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 24px;
            min-height: calc(100vh - 100px);
        }
        .sidebar {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
        }
        .sidebar h3 {
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 12px;
            letter-spacing: 1px;
        }
        .project-list {
            list-style: none;
        }
        .project-item {
            padding: 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 4px;
        }
        .project-item:hover { background: var(--border); }
        .project-item.active { background: var(--accent); color: #000; }
        .project-item .name { font-weight: 600; }
        .project-item .meta { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
        .project-item.active .meta { color: rgba(0,0,0,0.6); }
        .main {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .toolbar {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .btn {
            padding: 8px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--card);
            color: var(--text);
            cursor: pointer;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .btn:hover { border-color: var(--accent); }
        .btn-primary { background: var(--accent); color: #000; border-color: var(--accent); }
        .btn-primary:hover { opacity: 0.9; }
        .editor-area {
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 16px;
            flex: 1;
        }
        .file-list {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            overflow-y: auto;
            max-height: calc(100vh - 250px);
        }
        .file-item {
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .file-item:hover { background: var(--border); }
        .file-item.active { background: var(--accent); color: #000; }
        .file-item i { width: 16px; text-align: center; }
        .editor {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            display: flex;
            flex-direction: column;
        }
        .editor-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .editor-tabs {
            display: flex;
            gap: 8px;
        }
        .tab {
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            background: var(--border);
        }
        .tab.active { background: var(--accent); color: #000; }
        .editor-content {
            flex: 1;
            position: relative;
        }
        .editor-content textarea {
            width: 100%;
            height: 100%;
            min-height: 400px;
            background: transparent;
            border: none;
            color: var(--text);
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85rem;
            padding: 16px;
            resize: none;
            outline: none;
        }
        .preview-frame {
            width: 100%;
            height: 100%;
            min-height: 400px;
            border: none;
            background: #fff;
            border-radius: 0 0 12px 12px;
        }
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 12px 24px;
            border-radius: 8px;
            background: var(--green);
            color: #000;
            font-weight: 600;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
        }
        .toast.show { transform: translateY(0); opacity: 1; }
        .toast.error { background: var(--red); color: #fff; }
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--muted);
            gap: 12px;
        }
        .empty-state i { font-size: 3rem; }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .sidebar { display: none; }
            .editor-area { grid-template-columns: 1fr; }
            .file-list { max-height: 200px; }
        }
    </style>
</head>
<body>
        <div class="header">
            <div class="logo">
                <i class="fas fa-rocket"></i>
                <span>Project Dashboard</span>
            </div>
            <div style="display: flex; gap: 16px; align-items: center;">
                <a href="/crm" style="color: var(--accent); text-decoration: none; font-weight: 600; font-size: 0.9rem;">
                    <i class="fas fa-users"></i> CRM
                </a>
                <div class="status">Server Running</div>
            </div>
        </div>
    
    <div class="container">
        <div class="grid">
            <div class="sidebar">
                <h3>Projects</h3>
                <ul class="project-list" id="projectList">
                    <li class="empty-state" style="padding: 20px;">
                        <i class="fas fa-folder-open"></i>
                        <span>Loading...</span>
                    </li>
                </ul>
            </div>
            
            <div class="main">
                <div class="toolbar">
                    <button class="btn" onclick="refreshProjects()">
                        <i class="fas fa-sync"></i> Refresh
                    </button>
                    <button class="btn" onclick="openPreview()">
                        <i class="fas fa-eye"></i> Preview
                    </button>
                    <button class="btn" onclick="saveFile()">
                        <i class="fas fa-save"></i> Save
                    </button>
                    <button class="btn btn-primary" onclick="pushToGithub()">
                        <i class="fab fa-github"></i> Push
                    </button>
                </div>
                
                <div class="editor-area">
                    <div class="file-list" id="fileList">
                        <div class="empty-state">
                            <i class="fas fa-file-code"></i>
                            <span>Select a project</span>
                        </div>
                    </div>
                    
                    <div class="editor">
                        <div class="editor-header">
                            <div class="editor-tabs">
                                <div class="tab active" onclick="switchTab('code')">Code</div>
                                <div class="tab" onclick="switchTab('preview')">Preview</div>
                            </div>
                            <span id="currentFile" style="font-size: 0.8rem; color: var(--muted);">No file selected</span>
                        </div>
                        <div class="editor-content" id="editorContent">
                            <div class="empty-state">
                                <i class="fas fa-code"></i>
                                <span>Select a file to edit</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        let currentProject = null;
        let currentFile = null;
        let currentTab = 'code';
        
        // Load projects on start
        document.addEventListener('DOMContentLoaded', loadProjects);
        
        async function loadProjects() {
            try {
                const res = await fetch('/api/projects');
                const data = await res.json();
                renderProjects(data.projects);
            } catch (e) {
                showToast('Failed to load projects', 'error');
            }
        }
        
        function renderProjects(projects) {
            const list = document.getElementById('projectList');
            if (!projects.length) {
                list.innerHTML = '<li class="empty-state"><i class="fas fa-folder-open"></i><span>No projects</span></li>';
                return;
            }
            
            list.innerHTML = projects.map(p => `
                <li class="project-item" onclick="selectProject('${p.name}')">
                    <div class="name">${p.name}</div>
                    <div class="meta">${p.files} files · ${formatSize(p.size)}</div>
                </li>
            `).join('');
        }
        
        async function selectProject(name) {
            currentProject = name;
            currentFile = null;
            
            // Update UI
            document.querySelectorAll('.project-item').forEach(el => el.classList.remove('active'));
            event.target.closest('.project-item').classList.add('active');
            
            // Load files
            try {
                const res = await fetch(`/api/files?project=${name}`);
                const data = await res.json();
                renderFiles(data.files);
            } catch (e) {
                showToast('Failed to load files', 'error');
            }
        }
        
        function renderFiles(files) {
            const list = document.getElementById('fileList');
            if (!files.length) {
                list.innerHTML = '<div class="empty-state"><i class="fas fa-file"></i><span>No files</span></div>';
                return;
            }
            
            const icons = {
                'html': 'fa-code',
                'css': 'fa-css3-alt',
                'javascript': 'fa-js',
                'json': 'fa-brackets-curly',
                'markdown': 'fa-file-lines',
                'image': 'fa-image',
                'php': 'fa-php',
                'other': 'fa-file'
            };
            
            list.innerHTML = files.map(f => `
                <div class="file-item" onclick="selectFile('${f.path}')">
                    <i class="fas ${icons[f.type] || icons.other}"></i>
                    <span>${f.name}</span>
                </div>
            `).join('');
        }
        
        async function selectFile(path) {
            currentFile = path;
            
            // Update UI
            document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
            event.target.closest('.file-item').classList.add('active');
            document.getElementById('currentFile').textContent = path;
            
            // Load content
            try {
                const res = await fetch(`/api/read?project=${currentProject}&file=${encodeURIComponent(path)}`);
                const data = await res.json();
                showEditor(data.content);
            } catch (e) {
                showToast('Failed to load file', 'error');
            }
        }
        
        function showEditor(content) {
            const editor = document.getElementById('editorContent');
            editor.innerHTML = `<textarea id="codeEditor">${escapeHtml(content)}</textarea>`;
        }
        
        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            
            if (tab === 'preview' && currentProject) {
                const editor = document.getElementById('editorContent');
                editor.innerHTML = `<iframe class="preview-frame" src="/preview/${currentProject}"></iframe>`;
            } else if (tab === 'code' && currentFile) {
                selectFile(currentFile);
            }
        }
        
        async function saveFile() {
            if (!currentProject || !currentFile) {
                showToast('Select a file first', 'error');
                return;
            }
            
            const content = document.getElementById('codeEditor')?.value;
            if (!content) {
                showToast('No content to save', 'error');
                return;
            }
            
            try {
                const res = await fetch('/api/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project: currentProject, file: currentFile, content })
                });
                const data = await res.json();
                showToast(data.message, data.status === 'success' ? 'success' : 'error');
            } catch (e) {
                showToast('Failed to save', 'error');
            }
        }
        
        async function pushToGithub() {
            if (!currentProject) {
                showToast('Select a project first', 'error');
                return;
            }
            
            const message = prompt('Commit message:', 'Update from dashboard');
            if (!message) return;
            
            showToast('Pushing to GitHub...', 'success');
            
            try {
                const res = await fetch('/api/push', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project: currentProject, message })
                });
                const data = await res.json();
                showToast(data.message, data.status === 'success' ? 'success' : 'error');
            } catch (e) {
                showToast('Failed to push', 'error');
            }
        }
        
        function openPreview() {
            if (!currentProject) {
                showToast('Select a project first', 'error');
                return;
            }
            window.open(`/preview/${currentProject}`, '_blank');
        }
        
        function refreshProjects() {
            loadProjects();
            showToast('Refreshed!', 'success');
        }
        
        function showToast(msg, type = 'success') {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.className = `toast show ${type}`;
            setTimeout(() => toast.className = 'toast', 3000);
        }
        
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
        
        function escapeHtml(str) {
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
         }
     </script>
 </body>
 </html>'''
     
    def get_crm_ui_html(self):
        """Generate CRM page"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>&#x1F4CA; CRM - Client Management</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0a0a0a;
            --card: #141414;
            --border: #222;
            --text: #fff;
            --muted: #888;
            --accent: #F4A31E;
            --green: #22c55e;
            --red: #ef4444;
            --blue: #3b82f6;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        .header {
            background: var(--card);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.2rem;
            font-weight: 700;
        }
        .logo i { color: var(--accent); }
        .back-link {
            color: var(--muted);
            text-decoration: none;
            font-size: 0.9rem;
        }
        .back-link:hover { color: var(--text); }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }
        .stat-card .label {
            color: var(--muted);
            font-size: 0.85rem;
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
        }
        .stat-card .sub {
            font-size: 0.8rem;
            color: var(--muted);
            margin-top: 4px;
        }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        h1 { font-size: 1.8rem; margin-bottom: 8px; }
        h2 { font-size: 1.3rem; margin-bottom: 16px; }
        .subtitle { color: var(--muted); margin-bottom: 24px; }
        .btn {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
        }
        .btn:hover { opacity: 0.9; }
        .btn-secondary {
            background: var(--border);
            color: var(--text);
        }
        .btn-sm {
            padding: 6px 12px;
            font-size: 0.8rem;
        }
        .form-group {
            margin-bottom: 16px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 600;
            color: var(--muted);
            font-size: 0.85rem;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            background: #0a0a0a;
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 0.95rem;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--accent);
        }
        .row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th {
            color: var(--muted);
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }
        tr:hover { background: rgba(255,255,255,0.02); }
        .status {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }
        .status-Lead { background: rgba(59, 130, 246, 0.2); color: var(--blue); }
        .status-Prospect { background: rgba(234, 179, 8, 0.2); color: #eab308; }
        .status-Client { background: rgba(34, 197, 94, 0.2); color: var(--green); }
        .status-Past { background: var(--muted); color: #999; }
        .status-Dropped { background: rgba(239, 68, 68, 0.2); color: var(--red); }
        .badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            background: var(--border);
        }
        .actions {
            display: flex;
            gap: 8px;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            max-width: 600px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .close-modal {
            background: none;
            border: none;
            color: var(--muted);
            font-size: 1.5rem;
            cursor: pointer;
        }
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
        }
        .tab {
            padding: 8px 16px;
            background: none;
            border: none;
            color: var(--muted);
            cursor: pointer;
            border-radius: 8px;
            font-weight: 600;
        }
        .tab.active {
            background: var(--accent);
            color: #000;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .alert {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
        }
        .alert-success { background: rgba(34, 197, 94, 0.1); border: 1px solid var(--green); color: var(--green); }
        .alert-error { background: rgba(239, 68, 68, 0.1); border: 1px solid var(--red); color: var(--red); }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--muted);
        }
        .empty-state i { font-size: 3rem; margin-bottom: 16px; opacity: 0.5; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <a href="/" class="back-link"><i class="fas fa-arrow-left"></i></a>
            <i class="fas fa-users"></i>
            <span>CRM - Client Management</span>
        </div>
        <div>
            <button class="btn btn-sm" onclick="openModal('addClientModal')">
                <i class="fas fa-plus"></i> Add Client
            </button>
        </div>
    </div>
    
    <div class="container">
        <!-- Stats -->
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="label">Total Clients</div>
                <div class="value" id="stat-total">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Leads</div>
                <div class="value" id="stat-leads">-</div>
                <div class="sub">Need follow-up</div>
            </div>
            <div class="stat-card">
                <div class="label">Active Projects</div>
                <div class="value" id="stat-projects">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Pending Invoices</div>
                <div class="value" id="stat-pending">-</div>
                <div class="sub" id="stat-pending-amount">₹0</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('clients')">Clients</button>
            <button class="tab" onclick="switchTab('projects')">Projects</button>
            <button class="tab" onclick="switchTab('invoices')">Invoices</button>
            <button class="tab" onclick="switchTab('tasks')">Tasks</button>
        </div>

        <!-- Clients Tab -->
        <div id="tab-clients" class="tab-content active">
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <h2>All Clients</h2>
                    <input type="text" id="search-client" placeholder="Search..." style="width:250px;" onkeyup="filterClients()">
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Company</th>
                            <th>Phone</th>
                            <th>Status</th>
                            <th>Budget</th>
                            <th>Next Follow-up</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="clients-table">
                        <tr><td colspan="7" class="empty-state">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Projects Tab -->
        <div id="tab-projects" class="tab-content">
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <h2>Projects</h2>
                    <button class="btn btn-sm" onclick="openModal('addProjectModal')">
                        <i class="fas fa-plus"></i> Add Project
                    </button>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Client</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Price</th>
                            <th>Paid</th>
                            <th>Balance</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="projects-table">
                        <tr><td colspan="8" class="empty-state">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Invoices Tab -->
        <div id="tab-invoices" class="tab-content">
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <h2>Pending Invoices</h2>
                    <button class="btn btn-sm" onclick="openModal('addInvoiceModal')">
                        <i class="fas fa-plus"></i> Create Invoice
                    </button>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Invoice #</th>
                            <th>Client</th>
                            <th>Project</th>
                            <th>Amount</th>
                            <th>Due Date</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="invoices-table">
                        <tr><td colspan="7" class="empty-state">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Tasks Tab -->
        <div id="tab-tasks" class="tab-content">
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <h2>Tasks</h2>
                    <button class="btn btn-sm" onclick="openModal('addTaskModal')">
                        <i class="fas fa-plus"></i> Add Task
                    </button>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th>Project</th>
                            <th>Assignee</th>
                            <th>Status</th>
                            <th>Priority</th>
                            <th>Due Date</th>
                            <th>Hours</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="tasks-table">
                        <tr><td colspan="8" class="empty-state">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Add Client Modal -->
    <div id="addClientModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Add New Client</h2>
                <button class="close-modal" onclick="closeModal('addClientModal')">&times;</button>
            </div>
            <form id="addClientForm">
                <div class="row">
                    <div class="form-group">
                        <label>Name *</label>
                        <input type="text" name="name" required>
                    </div>
                    <div class="form-group">
                        <label>Company *</label>
                        <input type="text" name="company" required>
                    </div>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Phone *</label>
                        <input type="tel" name="phone" required>
                    </div>
                    <div class="form-group">
                        <label>Email *</label>
                        <input type="email" name="email" required>
                    </div>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Source</label>
                        <select name="source">
                            <option value="WhatsApp">WhatsApp</option>
                            <option value="Referral">Referral</option>
                            <option value="Facebook">Facebook</option>
                            <option value="Instagram">Instagram</option>
                            <option value="Google">Google</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Status</label>
                        <select name="status">
                            <option value="Lead">Lead</option>
                            <option value="Prospect">Prospect</option>
                            <option value="Client">Client</option>
                        </select>
                    </div>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Project Type *</label>
                        <select name="project_type">
                            <option value="Website">Website</option>
                            <option value="App">Mobile App</option>
                            <option value="Automation">Automation</option>
                            <option value="IoT">IoT</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Budget (₹)</label>
                        <input type="number" name="budget" placeholder="e.g., 25000">
                    </div>
                </div>
                <div class="form-group">
                    <label>Notes</label>
                    <textarea name="notes" rows="3"></textarea>
                </div>
                <div class="form-group">
                    <label>Next Follow-up (optional)</label>
                    <input type="date" name="next_followup">
                </div>
                <button type="submit" class="btn">Add Client</button>
            </form>
        </div>
    </div>

    <!-- Add Project Modal -->
    <div id="addProjectModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Add New Project</h2>
                <button class="close-modal" onclick="closeModal('addProjectModal')">&times;</button>
            </div>
            <form id="addProjectForm">
                <div class="form-group">
                    <label>Client *</label>
                    <select name="client_id" id="project-client-select" required>
                        <option value="">Select client...</option>
                    </select>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Project Name *</label>
                        <input type="text" name="name" required>
                    </div>
                    <div class="form-group">
                        <label>Price (₹) *</label>
                        <input type="number" name="price" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="3"></textarea>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Start Date</label>
                        <input type="date" name="start_date">
                    </div>
                    <div class="form-group">
                        <label>Deadline</label>
                        <input type="date" name="deadline">
                    </div>
                </div>
                <div class="form-group">
                    <label>Payment Terms</label>
                    <input type="text" name="payment_terms" value="50% advance, 50% delivery">
                </div>
                <button type="submit" class="btn">Add Project</button>
            </form>
        </div>
    </div>

    <!-- Add Invoice Modal -->
    <div id="addInvoiceModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Create New Invoice</h2>
                <button class="close-modal" onclick="closeModal('addInvoiceModal')">&times;</button>
            </div>
            <form id="addInvoiceForm">
                <div class="form-group">
                    <label>Client *</label>
                    <select name="client_id" id="invoice-client-select" required onchange="filterInvoiceProjects(this.value)">
                        <option value="">Select client...</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Project (optional)</label>
                    <select name="project_id" id="invoice-project-select">
                        <option value="">Select client first...</option>
                    </select>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Amount (₹) *</label>
                        <input type="number" name="amount" required>
                    </div>
                    <div class="form-group">
                        <label>Due Date *</label>
                        <input type="date" name="due_date" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <option value="Pending">Pending</option>
                        <option value="Paid">Paid</option>
                        <option value="Overdue">Overdue</option>
                        <option value="Cancelled">Cancelled</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Notes</label>
                    <textarea name="notes" rows="3"></textarea>
                </div>
                </div>
                <button type="submit" class="btn">Create Invoice</button>
            </form>
        </div>
    </div>

    <!-- Add Task Modal -->
    <div id="addTaskModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Create New Task</h2>
                <button class="close-modal" onclick="closeModal('addTaskModal')">&times;</button>
            </div>
            <form id="addTaskForm">
                <div class="form-group">
                    <label>Project *</label>
                    <select name="project_id" id="task-project-select" required>
                        <option value="">Select project...</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Description *</label>
                    <input type="text" name="description" required>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Assignee</label>
                        <input type="text" name="assignee" placeholder="e.g. Electro">
                    </div>
                    <div class="form-group">
                        <label>Due Date</label>
                        <input type="date" name="due_date">
                    </div>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Status</label>
                        <select name="status">
                            <option value="Todo">Todo</option>
                            <option value="In Progress">In Progress</option>
                            <option value="Done">Done</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select name="priority">
                            <option value="Low">Low</option>
                            <option value="Medium" selected>Medium</option>
                            <option value="High">High</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn">Create Task</button>
            </form>
        </div>
    </div>

    <!-- View Client Modal -->
    <div id="viewClientModal" class="modal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2>Client Profile</h2>
                <button class="close-modal" onclick="closeModal('viewClientModal')">&times;</button>
            </div>
            <div id="clientProfileDetails" style="margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <!-- Filled via JS -->
            </div>
            <h3>Interaction History</h3>
            <div id="clientInteractionsTimeline" style="margin-top: 10px; max-height: 400px; overflow-y: auto;">
                <!-- Filled via JS -->
            </div>
        </div>
    </div>

    <!-- Alert Area -->
    <div id="alert-area" style="position:fixed;top:20px;right:20px;z-index:2000;max-width:300px;"></div>

    <script>
        // Global state
        let clients = [];
        let projects = [];
        let invoices = [];
        let tasks = [];

        // Init
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadClients();
            loadProjects();
            loadInvoices();
            loadTasks();
            populateClientSelect();
            populateProjectSelect();
        });

        // Tab switching
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
            if (tab === 'tasks') loadTasks();
        }

        // Modal functions
        function openModal(id) {
            document.getElementById(id).classList.add('active');
        }
        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }

        // Alert
        function showAlert(msg, type = 'success') {
            const area = document.getElementById('alert-area');
            area.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
            setTimeout(() => area.innerHTML = '', 5000);
        }

        // Load stats
        async function loadStats() {
            try {
                const res = await fetch('/api/crm/stats');
                const data = await res.json();
                if (data.error) {
                    if (data.setup_required) {
                        showSetupMessage();
                    } else {
                        throw new Error(data.error);
                    }
                    return;
                }
                document.getElementById('stat-total').textContent = data.total_clients;
                document.getElementById('stat-leads').textContent = data.leads;
                document.getElementById('stat-projects').textContent = data.active_projects;
                document.getElementById('stat-pending').textContent = data.pending_invoices_count;
                document.getElementById('stat-pending-amount').textContent = '₹' + data.pending_invoices_amount.toLocaleString();
            } catch (e) {
                console.error('Stats load failed:', e);
            }
        }
        
        function showSetupMessage() {
            const statsGrid = document.getElementById('stats-grid');
            statsGrid.innerHTML = `
                <div class="stat-card" style="grid-column: 1/-1; text-align: center; padding: 40px;">
                    <h2 style="color: var(--accent); margin-bottom: 16px;">CRM Setup Required</h2>
                    <p style="margin-bottom: 16px;">To use the CRM, you need to set up Google Sheets API integration.</p>
                    <ol style="text-align: left; max-width: 600px; margin: 0 auto 20px;">
                        <li>Create a Google Cloud Project</li>
                        <li>Enable Google Sheets API</li>
                        <li>Create a Service Account and download JSON key</li>
                        <li>Save the JSON key to: <code>~/.nanobot/workspace/google-credentials.json</code></li>
                        <li>Create a Google Sheet with 5 tabs: Clients, Projects, Interactions, Invoices, Tasks</li>
                        <li>Share the Sheet with the service account email (Editor access)</li>
                        <li>Save the Sheet ID to: <code>~/.nanobot/workspace/crm_sheet_id.txt</code></li>
                    </ol>
                    <p>See <code>crm_sheet_structure.md</code> for detailed instructions.</p>
                </div>
            `;
        }

        // Load clients
        async function loadClients() {
            try {
                const res = await fetch('/api/crm/clients');
                const data = await res.json();
                if (data.error) {
                    if (data.setup_required) {
                        showSetupMessage();
                        return;
                    }
                    throw new Error(data.error);
                }
                clients = data.clients;
                renderClients(clients);
            } catch (e) {
                showAlert('Failed to load clients: ' + e.message, 'error');
            }
        }

        function renderClients(list) {
            const tbody = document.getElementById('clients-table');
            if (list.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No clients found</td></tr>';
                return;
            }
            tbody.innerHTML = list.map(c => `
                <tr>
                    <td><strong>${escapeHtml(c.name)}</strong><br><small>${escapeHtml(c.email)}</small></td>
                    <td>${escapeHtml(c.company)}</td>
                    <td>${escapeHtml(c.phone)}</td>
                    <td><span class="status status-${c.status}">${c.status}</span></td>
                    <td>₹${Number(c.budget || 0).toLocaleString()}</td>
                    <td>${c.next_followup || '-'}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="viewClient('${c.id}')">View</button>
                        <button class="btn btn-sm" onclick="addInteraction('${c.id}')">Log</button>
                        <button class="btn btn-sm btn-secondary" style="color:var(--red);" onclick="deleteRecord('client', '${c.id}')" title="Delete"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }

        function filterClients() {
            const query = document.getElementById('search-client').value.toLowerCase();
            const filtered = clients.filter(c => 
                c.name.toLowerCase().includes(query) ||
                c.company.toLowerCase().includes(query) ||
                c.phone.includes(query)
            );
            renderClients(filtered);
        }

        // Load projects
        async function loadProjects() {
            try {
                if (clients.length === 0) await loadClients(); // Ensure clients are loaded
                const res = await fetch('/api/crm/projects');
                const data = await res.json();
                if (data.error) {
                    if (data.setup_required) {
                        showSetupMessage();
                        return;
                    }
                    throw new Error(data.error);
                }
                projects = data.projects;
                renderProjects(projects);
            } catch (e) {
                showAlert('Failed to load projects: ' + e.message, 'error');
            }
        }

        function getClientName(id) {
            const client = clients.find(c => c.id === id);
            return client ? escapeHtml(client.name) : escapeHtml(id);
        }

        function renderProjects(list) {
            const tbody = document.getElementById('projects-table');
            if (list.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No projects found</td></tr>';
                return;
            }
            tbody.innerHTML = list.map(p => `
                <tr>
                    <td><span class="badge" title="${p.id}">${p.id.substring(0, 8)}...</span></td>
                    <td>${getClientName(p.client_id)}</td>
                    <td><strong>${escapeHtml(p.name)}</strong></td>
                    <td><span class="status status-${p.status.replace(' ', '-').toLowerCase()}">${p.status}</span></td>
                    <td>₹${Number(p.price || 0).toLocaleString()}</td>
                    <td>₹${Number(p.paid_amount || 0).toLocaleString()}</td>
                    <td>₹${Number(p.balance || 0).toLocaleString()}</td>
                    <td class="actions">
                        <button class="btn btn-sm" onclick="updateProjectPayment('${p.id}', ${p.price || 0}, ${p.paid_amount || 0})">Update</button>
                        <button class="btn btn-sm btn-secondary" style="color:var(--red);" onclick="deleteRecord('project', '${p.id}')" title="Delete"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }

        async function updateProjectPayment(id, price, currentPaid) {
            const newPaidStr = prompt(`Update Payment:\nTotal Price: ₹${price}\nCurrent Paid: ₹${currentPaid}\n\nEnter new total Paid Amount:`, currentPaid);
            if (newPaidStr === null) return;
            
            const newPaid = Number(newPaidStr);
            if (isNaN(newPaid)) {
                showAlert('Invalid amount entered', 'error');
                return;
            }
            
            const newBalance = price - newPaid;
            
            try {
                const res = await fetch(`/api/crm/project/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        paid_amount: newPaid,
                        balance: newBalance
                    })
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                
                showAlert('Payment updated!');
                loadProjects();
            } catch (e) {
                showAlert('Failed to update: ' + e.message, 'error');
            }
        }

        // Load invoices
        async function loadInvoices() {
            try {
                if (clients.length === 0) await loadClients(); // Ensure clients are loaded
                const res = await fetch('/api/crm/invoices/pending');
                const data = await res.json();
                if (data.error) {
                    if (data.setup_required) {
                        showSetupMessage();
                        return;
                    }
                    throw new Error(data.error);
                }
                invoices = data.invoices;
                renderInvoices(invoices);
            } catch (e) {
                showAlert('Failed to load invoices: ' + e.message, 'error');
            }
        }

        function renderInvoices(list) {
            const tbody = document.getElementById('invoices-table');
            if (list.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No pending invoices</td></tr>';
                return;
            }
            tbody.innerHTML = list.map(inv => `
                <tr>
                    <td>${inv.invoice_no}</td>
                    <td>${getClientName(inv.client_id)}</td>
                    <td>${inv.project_id ? getProjectName(inv.project_id) : '<span style="color:var(--muted)">—</span>'}</td>
                    <td>₹${Number(inv.amount).toLocaleString()}</td>
                    <td>${inv.due_date}</td>
                    <td><span class="status status-${inv.status}">${inv.status}</span></td>
                    <td class="actions">
                        <button class="btn btn-sm" onclick="markPaid('${inv.id}')">Mark Paid</button>
                        <button class="btn btn-sm btn-secondary" style="color:var(--red);" onclick="deleteRecord('invoice', '${inv.id}')" title="Delete"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }

        function getProjectName(id) {
            const project = projects.find(p => p.id === id);
            return project ? escapeHtml(project.name) : '<span style="color:var(--muted)">—</span>';
        }

        // Filter the invoice modal's project dropdown based on selected client
        function filterInvoiceProjects(clientId) {
            const sel = document.getElementById('invoice-project-select');
            if (!sel) return;
            const clientProjects = projects.filter(p => p.client_id === clientId);
            if (clientProjects.length === 0) {
                sel.innerHTML = '<option value="">No projects for this client</option>';
            } else {
                sel.innerHTML = '<option value="">No specific project</option>' +
                    clientProjects.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
            }
        }

        // Populate project select in add task modal
        async function populateProjectSelect() {
            const selectTaskProj = document.getElementById('task-project-select');
            if (!selectTaskProj) return;
            if (projects.length === 0) await loadProjects();
            selectTaskProj.innerHTML = '<option value="">Select project...</option>' +
                projects.map(p => `<option value="${p.id}">${escapeHtml(p.name)} (${getClientName(p.client_id)})</option>`).join('');
            // Also reset invoice project select
            const invProjSel = document.getElementById('invoice-project-select');
            if (invProjSel) invProjSel.innerHTML = '<option value="">Select client first...</option>';
        }

        // Load tasks
        async function loadTasks() {
            try {
                if (projects.length === 0) await loadProjects();
                const res = await fetch('/api/crm/tasks');
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                tasks = data.tasks;
                renderTasks();
            } catch (e) {
                showAlert('Failed to load tasks: ' + e.message, 'error');
            }
        }

        function getProjectName(id) {
            const project = projects.find(p => p.id === id);
            return project ? escapeHtml(project.name) : escapeHtml(id);
        }

        function renderTasks() {
            const tbody = document.getElementById('tasks-table');
            if (tasks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No tasks found</td></tr>';
                return;
            }
            tbody.innerHTML = tasks.map(t => `
                <tr>
                    <td><strong>${escapeHtml(t.description)}</strong></td>
                    <td>${getProjectName(t.project_id)}</td>
                    <td>${escapeHtml(t.assignee || '-')}</td>
                    <td>
                        <select onchange="updateTaskStatus('${t.id}', this.value)" style="padding:4px; max-width:120px; font-size:0.8rem; background:var(--bg); color:var(--text); border:1px solid var(--border); border-radius:4px;">
                            <option value="Todo" ${t.status === 'Todo' ? 'selected' : ''}>Todo</option>
                            <option value="In Progress" ${t.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                            <option value="Done" ${t.status === 'Done' ? 'selected' : ''}>Done</option>
                        </select>
                    </td>
                    <td><span class="badge" ${t.priority==='High'?'style="background:var(--red);color:#fff;"':''}>${t.priority}</span></td>
                    <td>${t.due_date || '-'}</td>
                    <td>${t.hours_spent || 0}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" style="color:var(--red);" onclick="deleteRecord('task', '${t.id}')" title="Delete"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }

        async function updateTaskStatus(id, newStatus) {
            try {
                const res = await fetch(`/api/crm/task/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                showAlert('Task status updated');
                loadTasks();
            } catch (err) {
                showAlert('Failed to update status: ' + err.message, 'error');
                loadTasks(); // Reset dropdown
            }
        }

        // Populate client select in add project and add invoice modal
        async function populateClientSelect() {
            const selectProject = document.getElementById('project-client-select');
            const selectInvoice = document.getElementById('invoice-client-select');
            if (clients.length === 0) await loadClients();
            const options = '<option value="">Select client...</option>' +
                clients.map(c => `<option value="${c.id}">${escapeHtml(c.name)} (${escapeHtml(c.company)})</option>`).join('');
            if(selectProject) selectProject.innerHTML = options;
            if(selectInvoice) selectInvoice.innerHTML = options;
        }

        // Add client form
        document.getElementById('addClientForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            try {
                const res = await fetch('/api/crm/client', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.error) throw new Error(result.error);
                showAlert('Client added successfully!');
                closeModal('addClientModal');
                e.target.reset();
                loadClients();
                loadStats();
                populateClientSelect();
            } catch (err) {
                showAlert('Error: ' + err.message, 'error');
            }
        });

        // Add project form
        document.getElementById('addProjectForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            try {
                const res = await fetch('/api/crm/project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.error) throw new Error(result.error);
                showAlert('Project added!');
                closeModal('addProjectModal');
                e.target.reset();
                loadProjects();
                loadStats();
            } catch (err) {
                showAlert('Error: ' + err.message, 'error');
            }
        });

        // Add invoice form
        const addInvoiceForm = document.getElementById('addInvoiceForm');
        if (addInvoiceForm) {
            addInvoiceForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                try {
                    const res = await fetch('/api/crm/invoice', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    const result = await res.json();
                    if (result.error) throw new Error(result.error);
                    showAlert('Invoice created!');
                    closeModal('addInvoiceModal');
                    e.target.reset();
                    loadInvoices();
                    loadStats();
                } catch (err) {
                    showAlert('Error: ' + err.message, 'error');
                }
            });
        }

        // Add task form
        const addTaskForm = document.getElementById('addTaskForm');
        if (addTaskForm) {
            addTaskForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                try {
                    const res = await fetch('/api/crm/task', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    const result = await res.json();
                    if (result.error) throw new Error(result.error);
                    showAlert('Task created!');
                    closeModal('addTaskModal');
                    e.target.reset();
                    loadTasks();
                } catch (err) {
                    showAlert('Error: ' + err.message, 'error');
                }
            });
        }

        // Mark invoice paid
        async function markPaid(invoiceId) {
            if (!confirm('Mark this invoice as paid?')) return;
            try {
                const res = await fetch('/api/crm/invoice/' + invoiceId, { method: 'PUT' });
                const result = await res.json();
                if (result.error) throw new Error(result.error);
                showAlert('Invoice marked as paid!');
                loadInvoices();
                loadStats();
            } catch (err) {
                showAlert('Error: ' + err.message, 'error');
            }
        }

        async function deleteRecord(type, id) {
            if (!confirm(`Are you sure you want to delete this ${type}? This action cannot be undone.`)) return;
            try {
                const res = await fetch(`/api/crm/${type}/${id}`, { method: 'DELETE' });
                const result = await res.json();
                if (result.error) throw new Error(result.error);
                showAlert(`${type.charAt(0).toUpperCase() + type.slice(1)} deleted successfully!`);
                if (type === 'client') { loadClients(); populateClientSelect(); }
                if (type === 'project') loadProjects();
                if (type === 'invoice') loadInvoices();
                loadStats();
            } catch (err) {
                showAlert('Error: ' + err.message, 'error');
            }
        }

        // View client details
        async function viewClient(clientId) {
            const client = clients.find(c => c.id === clientId);
            if (!client) return;
            
            const profileHtml = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div><strong>Name:</strong> ${escapeHtml(client.name)}</div>
                    <div><strong>Company:</strong> ${escapeHtml(client.company)}</div>
                    <div><strong>Phone:</strong> ${client.phone}</div>
                    <div><strong>Email:</strong> ${escapeHtml(client.email)}</div>
                    <div><strong>Status:</strong> <span class="status status-${client.status.replace(' ', '-').toLowerCase()}">${client.status}</span></div>
                    <div><strong>Budget:</strong> ₹${Number(client.budget || 0).toLocaleString()}</div>
                    <div style="grid-column: 1 / -1;"><strong>Notes:</strong> ${escapeHtml(client.notes || 'None')}</div>
                </div>
            `;
            document.getElementById('clientProfileDetails').innerHTML = profileHtml;
            document.getElementById('clientInteractionsTimeline').innerHTML = '<div style="padding: 10px; color: var(--muted);">Loading history...</div>';
            
            openModal('viewClientModal');

            try {
                const res = await fetch(`/api/crm/client/${clientId}/interactions`);
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                
                const tl = document.getElementById('clientInteractionsTimeline');
                if (!data.interactions || data.interactions.length === 0) {
                    tl.innerHTML = '<div style="padding: 10px; color: var(--muted); border-left: 2px solid var(--border); margin-left: 10px;">No interaction history found.</div>';
                    return;
                }
                
                tl.innerHTML = data.interactions.map(int => `
                    <div style="padding: 15px; margin-bottom: 10px; border-left: 2px solid var(--border); margin-left: 10px; position: relative; background: #0a0a0a; border-radius: 4px;">
                        <div style="position: absolute; left: -6px; top: 15px; width: 10px; height: 10px; border-radius: 50%; background: var(--accent);"></div>
                        <div style="font-size: 0.8rem; color: var(--muted); margin-bottom: 4px;">
                            ${new Date(int.timestamp).toLocaleString()} • <span class="badge">${int.type || 'Note'}</span>
                        </div>
                        <div style="font-weight: 500;">${escapeHtml(int.summary)}</div>
                    </div>
                `).join('');
            } catch (err) {
                document.getElementById('clientInteractionsTimeline').innerHTML = `<div style="color: var(--red);">Error loading history: ${err.message}</div>`;
            }
        }

        // Add interaction (quick log)
        function addInteraction(clientId) {
            const summary = prompt('Log interaction (e.g., "Called client, discussed requirements"):');
            if (!summary) return;
            fetch('/api/crm/interaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: clientId,
                    summary: summary,
                    type: 'Note',
                    followup_needed: confirm('Schedule follow-up?')
                })
            }).then(r => r.json()).then(result => {
                if (result.error) alert('Error: ' + result.error);
                else {
                    showAlert('Interaction logged');
                    loadClients();
                    loadStats();
                }
            });
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
    </script>
</body>
</html>'''
    
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def get_local_ip():
    """Get local IP address"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"


def main():
    """Start the server"""
    ip = get_local_ip()
    
    print("=" * 50)
    print("📱 PROJECT DASHBOARD")
    print("=" * 50)
    print()
    print(f"🌐 Local:   http://localhost:{PORT}")
    print(f"🌐 Network: http://{ip}:{PORT}")
    print()
    print("📂 Projects:")
    for name, path in PROJECTS.items():
        exists = "✅" if path.exists() else "❌"
        print(f"   {exists} {name}")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    print(f"🔒 Security active. Default admin password: {admin_pass}")
    print("=" * 50)
    
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    import uuid
    server.session_token = str(uuid.uuid4())
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
