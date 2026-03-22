#!/bin/bash
# 📱 Telegram Quick Commands for Project Management
# Usage: source this file or run commands directly

WORKSPACE="$HOME/.nanobot/workspace"

# Project paths
declare -A PROJECTS=(
    ["coelum9"]="$WORKSPACE/coelum9"
    ["kruthi"]="$WORKSPACE/kruthi"
    ["acumen9"]="$WORKSPACE/acumen9-clone"
    ["webdev"]="$WORKSPACE/webdev-company"
)

# 📊 Show project status
pm_status() {
    echo "📊 PROJECT STATUS"
    echo "================="
    echo ""
    for name in "${!PROJECTS[@]}"; do
        path="${PROJECTS[$name]}"
        if [ -d "$path" ]; then
            files=$(find "$path" -type f | grep -v ".git/" | wc -l)
            size=$(du -sh "$path" 2>/dev/null | cut -f1)
            git_status=$(cd "$path" && git status --short 2>/dev/null | wc -l)
            
            if [ "$git_status" -gt 0 ]; then
                echo "⚠️  $name - $files files, $size ($git_status changes)"
            else
                echo "✅ $name - $files files, $size"
            fi
        else
            echo "❌ $name - Not found"
        fi
    done
}

# 📂 List files in project
pm_files() {
    local project="$1"
    if [ -z "$project" ]; then
        echo "Usage: pm_files <project>"
        return 1
    fi
    
    path="${PROJECTS[$project]}"
    if [ ! -d "$path" ]; then
        echo "❌ Project not found: $project"
        return 1
    fi
    
    echo "📂 FILES IN $project"
    echo "===================="
    find "$path" -type f | grep -v ".git/" | sed "s|$path/||" | sort
}

# 📄 Read file content
pm_read() {
    local project="$1"
    local file="$2"
    
    if [ -z "$project" ] || [ -z "$file" ]; then
        echo "Usage: pm_read <project> <file>"
        return 1
    fi
    
    path="${PROJECTS[$project]}"
    if [ ! -f "$path/$file" ]; then
        echo "❌ File not found: $file"
        return 1
    fi
    
    echo "📄 $project/$file"
    echo "=================="
    cat "$path/$file"
}

# 🚀 Push to GitHub
pm_push() {
    local project="$1"
    local message="${2:-Update from terminal}"
    
    if [ -z "$project" ]; then
        echo "Usage: pm_push <project> [message]"
        return 1
    fi
    
    path="${PROJECTS[$project]}"
    if [ ! -d "$path" ]; then
        echo "❌ Project not found: $project"
        return 1
    fi
    
    echo "🚀 PUSHING $project"
    echo "==================="
    
    cd "$path"
    git add .
    git commit -m "$message" 2>/dev/null
    
    if git push 2>/dev/null; then
        echo "✅ Pushed to GitHub!"
    else
        echo "⚠️ Push failed or no changes"
    fi
}

# 🔍 Git status
pm_git() {
    local project="$1"
    
    if [ -z "$project" ]; then
        echo "Usage: pm_git <project>"
        return 1
    fi
    
    path="${PROJECTS[$project]}"
    if [ ! -d "$path" ]; then
        echo "❌ Project not found: $project"
        return 1
    fi
    
    echo "🔍 GIT STATUS: $project"
    echo "======================="
    cd "$path"
    git status
}

# 🌐 Start dashboard server
pm_serve() {
    echo "🌐 STARTING DASHBOARD"
    echo "====================="
    cd "$WORKSPACE/pm-dashboard"
    bash start.sh
}

# 📸 Quick preview (screenshot)
pm_preview() {
    local project="$1"
    
    if [ -z "$project" ]; then
        echo "Usage: pm_preview <project>"
        return 1
    fi
    
    path="${PROJECTS[$project]}"
    if [ ! -d "$path" ]; then
        echo "❌ Project not found: $project"
        return 1
    fi
    
    echo "📸 PREVIEW: $project"
    echo "===================="
    echo "Open in browser: http://localhost:8080/preview/$project"
}

# Show help
pm_help() {
    echo "📱 PROJECT MANAGER COMMANDS"
    echo "==========================="
    echo ""
    echo "pm_status          - Show all projects"
    echo "pm_files <proj>    - List files"
    echo "pm_read <proj> <file> - Read file"
    echo "pm_push <proj> [msg] - Push to GitHub"
    echo "pm_git <proj>      - Git status"
    echo "pm_serve           - Start web dashboard"
    echo "pm_preview <proj>  - Preview URL"
    echo "pm_help            - Show this help"
    echo ""
    echo "Projects: coelum9, kruthi, acumen9, webdev"
}

# Export functions
export -f pm_status pm_files pm_read pm_push pm_git pm_serve pm_preview pm_help
