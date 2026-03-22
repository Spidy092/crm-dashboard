#!/usr/bin/env python3
"""
Stitch MCP Client + Code Generator
Complete workflow: generate UI design → export → code implementation
"""

import json
import requests
import re
from pathlib import Path

STITCH_MCP_URL = "https://stitch.googleapis.com/mcp"
API_KEY = "AQ.Ab8RN6KX742Rm1W6PwQKcSChMFcOJSlnYUIEcOztSH7Fh6vgag"

HEADERS = {
    "X-Goog-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

class StitchClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.request_id = 1
        self.project_id = None
        self.project_name = None
        self.design_system = None

    def _rpc(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params or {}}
        self.request_id += 1
        resp = self.session.post(STITCH_MCP_URL, json=payload, timeout=120)
        return resp.json()

    def initialize(self):
        return self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pm-dashboard", "version": "1.0.0"}
        })

    def create_project(self, title):
        """Create a new Stitch project"""
        result = self._rpc("tools/call", {
            "name": "create_project",
            "arguments": {"title": title}
        })
        if "error" in result:
            return result
        content = result.get("result", {}).get("content", [])
        if content:
            text = content[0].get("text", "")
            try:
                data = json.loads(text)
                self.project_name = data.get("name", "")
                match = re.search(r'projects/(\d+)', self.project_name)
                if match:
                    self.project_id = match.group(1)
                return {"success": True, "project_id": self.project_id, "project_name": self.project_name}
            except:
                return {"error": "Could not parse project creation response"}
        return {"error": "No content in response"}

    def create_screen(self, prompt, device_type="DESKTOP", model_id="GEMINI_3_1_PRO"):
        """Create the first screen using edit_screens with empty selectedScreenIds"""
        if not self.project_id:
            return {"error": "No project. Create one first."}

        result = self._rpc("tools/call", {
            "name": "edit_screens",
            "arguments": {
                "projectId": self.project_id,
                "selectedScreenIds": [],
                "prompt": prompt,
                "deviceType": device_type,
                "modelId": model_id
            }
        })
        if "error" in result:
            return result

        # Parse the response to extract screen info and design system
        content = result.get("result", {}).get("content", [])
        if not content:
            return {"error": "No content in response", "raw": result}

        # The first content item is a JSON string with outputComponents
        first_item = content[0]
        if "text" in first_item:
            try:
                data = json.loads(first_item["text"])
                output_components = data.get("outputComponents", [])
                if output_components:
                    screen_data = output_components[0]  # First component
                    self.design_system = screen_data.get("designSystem", {})
                    suggestions = []
                    for item in content[1:]:
                        if "suggestion" in item:
                            suggestions.append(item["suggestion"])
                    return {
                        "success": True,
                        "title": screen_data.get("title", "Untitled"),
                        "design_system": self.design_system,
                        "suggestions": suggestions,
                        "raw_response": screen_data,
                        "session_id": data.get("sessionId")
                    }
                else:
                    return {"error": "No outputComponents in first content", "data": data}
            except json.JSONDecodeError:
                return {"error": "Failed to parse JSON from first content", "text": first_item.get("text")}
        else:
            return {"error": "First content has no text field", "content": content}

    def list_screens(self):
        if not self.project_id:
            return {"error": "No project"}
        result = self._rpc("tools/call", {
            "name": "list_screens",
            "arguments": {"projectId": self.project_id}
        })
        if "error" in result:
            return result
        content = result.get("result", {}).get("content", [])
        if content:
            try:
                data = json.loads(content[0].get("text", "{}"))
                return {"screens": data.get("screens", [])}
            except:
                return {"screens": []}
        return {"screens": []}

    def generate_more_screens(self, prompts, base_screen_id=None):
        """Generate additional screens using edit_screens with a base screen ID"""
        if not self.project_id:
            return {"error": "No project"}

        # If we don't have a base screen ID, list screens to get one
        if not base_screen_id:
            screens = self.list_screens()
            if "error" in screens:
                return screens
            screen_list = screens.get("screens", [])
            if screen_list:
                base_screen_id = screen_list[0].get("screen_id") or screen_list[0].get("id")
            else:
                return {"error": "No base screen available"}

        results = []
        for prompt in prompts:
            result = self._rpc("tools/call", {
                "name": "edit_screens",
                "arguments": {
                    "projectId": self.project_id,
                    "selectedScreenIds": [base_screen_id],
                    "prompt": prompt
                }
            })
            if "error" in result:
                results.append({"prompt": prompt, "error": result["error"]})
            else:
                results.append({"prompt": prompt, "result": result.get("result", {})})
        return {"base_screen_id": base_screen_id, "results": results}

    def get_screen_details(self, screen_id):
        """Get full details of a screen including design specs"""
        result = self._rpc("tools/call", {
            "name": "get_screen",
            "arguments": {
                "name": f"projects/{self.project_id}/screens/{screen_id}",
                "projectId": self.project_id,
                "screenId": screen_id
            }
        })
        if "error" in result:
            return result
        return result.get("result", {})


def generate_code_from_design(design_info, framework="html"):
    """
    Generate actual code from Stitch design system.
    This analyzes the design tokens and produces HTML/CSS/React code.
    """
    ds = design_info.get("design_system", {})
    colors = ds.get("namedColors", {})
    fonts = ds.get("font", "system-ui")
    spacing_scale = ds.get("spacingScale", 4)

    # Extract primary colors
    primary = colors.get("primary", "#000000")
    primary_container = colors.get("primary_container", "#00174b")
    on_primary = colors.get("on_primary", "#ffffff")
    surface = colors.get("surface", "#f7f9fb")
    on_surface = colors.get("on_surface", "#191c1e")

    if framework == "html":
        css = f"""
:root {{
    --primary: {primary};
    --primary-container: {primary_container};
    --on-primary: {on_primary};
    --surface: {surface};
    --on-surface: {on_surface};
    --font-base: {fonts};
    --spacing-unit: {spacing_scale * 0.25}rem;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: var(--font-base), system-ui, sans-serif;
    background: var(--surface);
    color: var(--on-surface);
    line-height: 1.6;
}}
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: calc(var(--spacing-unit) * 4);
}}
.btn {{
    background: var(--primary);
    color: var(--on-primary);
    border: none;
    padding: calc(var(--spacing-unit) * 2) calc(var(--spacing-unit) * 4);
    border-radius: calc(var(--spacing-unit) * 2);
    font-weight: 600;
    cursor: pointer;
}}
.input {{
    width: 100%;
    padding: calc(var(--spacing-unit) * 2);
    border: 1px solid var(--on-surface);
    border-radius: calc(var(--spacing-unit) * 1);
    margin-bottom: calc(var(--spacing-unit) * 2);
    font-family: inherit;
}}
"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{design_info.get('title', 'Generated UI')}</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <h1>{design_info.get('title', 'Generated UI')}</h1>
        <p>Project ID: {design_info.get('project_id')}</p>
        <form>
            <input type="email" class="input" placeholder="Email" required>
            <input type="password" class="input" placeholder="Password" required>
            <button type="submit" class="btn">Sign In</button>
        </form>
    </div>
</body>
</html>"""
        return html

    elif framework == "react":
        # Generate React component with CSS modules
        title = design_info.get('title', 'GeneratedUI')
        component_name = re.sub(r'\s', '', title)  # Remove spaces for component name
        component = f"""import React, {{ useState }} from 'react';
import styles from './App.module.css';

const {component_name} = () => {{
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <div className={{styles.container}}>
      <h1 className={{styles.title}}>{title}</h1>
      <form onSubmit={{e => e.preventDefault()}}>
        <input
          type="email"
          className={{styles.input}}
          placeholder="Email"
          value={{email}}
          onChange={{e => setEmail(e.target.value)}}
          required
        />
        <input
          type="password"
          className={{styles.input}}
          placeholder="Password"
          value={{password}}
          onChange={{e => setPassword(e.target.value)}}
          required
        />
        <button type="submit" className={{styles.btn}}>Sign In</button>
      </form>
    </div>
  );
}};

export default {component_name};
"""
        css = f""".container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: calc(var(--spacing-unit) * 4);
  font-family: {fonts}, system-ui, sans-serif;
  background: {surface};
  color: {on_surface};
}}

.title {{
  font-size: 2rem;
  margin-bottom: 1rem;
}}

.input {{
  width: 100%;
  padding: calc(var(--spacing-unit) * 2);
  border: 1px solid {on_surface};
  border-radius: calc(var(--spacing-unit));
  margin-bottom: calc(var(--spacing-unit) * 2);
}}

.btn {{
  background: {primary};
  color: {on_primary};
  border: none;
  padding: calc(var(--spacing-unit) * 2) calc(var(--spacing-unit) * 4);
  border-radius: calc(var(--spacing-unit) * 2);
  font-weight: 600;
  cursor: pointer;
}}
"""
        return {"component": component, "css": css}
    else:
        return {"error": f"Unsupported framework: {framework}"}


def generate_ui_design(prompt, screens=None, style="modern", platform="web", framework="html"):
    """
    Complete workflow: create project → generate screens → return code.
    """
    client = StitchClient()
    init = client.initialize()
    if "error" in init:
        return {"error": f"Init failed: {init['error']}"}

    # Create project
    proj_title = f"PM Dashboard - {prompt[:30]}..."
    create = client.create_project(proj_title)
    if "error" in create:
        return create

    # Create first screen using edit_screens with empty selectedScreenIds
    first_screen = client.create_screen(prompt)
    if "error" in first_screen:
        return {"error": first_screen["error"], "project_id": client.project_id}

    # Generate additional screens if requested
    all_screens = [{"screen": "main", "data": first_screen}]
    if screens:
        # Use the first screen as base to generate others
        more = client.generate_more_screens(screens)
        if "error" not in more:
            all_screens.extend([{"screen": s, "data": r} for s, r in zip(screens, more["results"])])

    # Generate code from the design system
    code = generate_code_from_design({
        "project_id": client.project_id,
        "title": first_screen.get("title", "Generated UI"),
        "design_system": first_screen.get("design_system", {}),
        "screens": all_screens
    }, framework=framework)

    return {
        "project_id": client.project_id,
        "project_name": client.project_name,
        "screens": all_screens,
        "design_system": first_screen.get("design_system"),
        "code": code
    }


if __name__ == "__main__":
    print("=== Stitch MCP Client + Code Generator ===\n")

    result = generate_ui_design(
        prompt="Modern login page for a fitness app",
        screens=["dashboard", "profile"],
        style="minimal",
        platform="web",
        framework="html"
    )

    if "error" in result:
        print("ERROR:", result["error"])
    else:
        print(f"Project ID: {result['project_id']}")
        print(f"Generated {len(result['screens'])} screens")
        print("\n--- Generated Code (first 500 chars) ---")
        if isinstance(result["code"], dict):
            print("React Component:", result["code"]["component"][:300])
            print("\nCSS:", result["code"]["css"][:300])
        else:
            print(result["code"][:500])

        # Save code to file
        output_dir = Path("stitch_output")
        output_dir.mkdir(exist_ok=True)
        if isinstance(result["code"], dict):
            (output_dir / "App.jsx").write_text(result["code"]["component"])
            (output_dir / "App.module.css").write_text(result["code"]["css"])
            print("\nSaved to stitch_output/")
        else:
            (output_dir / "index.html").write_text(result["code"])
            print("\nSaved to stitch_output/index.html")
