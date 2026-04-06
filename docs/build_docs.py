import json
import os

files_to_read = {
    'overview': '../README.md',
    'lattice-engine': '../lattice-engine/README.md',
    'lattice-client': '../lattice-client/README.md',
    'lattice-server': '../lattice-server/README.md',
    'contributing': 'CONTRIBUTING.md'
}

docs_content = {}
for key, filepath in files_to_read.items():
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            docs_content[key] = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        docs_content[key] = f"# Error\nCould not load {filepath}."

# JSON string representation to safely inject into JS
json_docs = json.dumps(docs_content)

html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lattice AIF Documentation</title>
    <!-- Tailwind CSS with Typography plugin -->
    <script src="https://cdn.tailwindcss.com?plugins=typography"></script>
    <script>
      tailwind.config = {{
        theme: {{
          extend: {{
            fontFamily: {{
              sans: ['Inter', 'sans-serif'],
            }}
          }}
        }}
      }}
    </script>
    <!-- Highlight.js for Syntax Highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    
    <!-- Marked.js for Markdown Parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
        }}
        .nav-link {{
            transition: all 0.2s ease;
        }}
        .nav-link.active {{
            background-color: #e2e8f0;
            color: #0f172a;
            font-weight: 600;
        }}
        /* Custom scrollbar for sidebar */
        .sidebar-scroll::-webkit-scrollbar {{
            width: 6px;
        }}
        .sidebar-scroll::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .sidebar-scroll::-webkit-scrollbar-thumb {{
            background-color: #cbd5e1;
            border-radius: 20px;
        }}
    </style>
</head>
<body class="text-slate-800 antialiased flex h-screen overflow-hidden">

    <!-- Sidebar -->
    <aside class="w-64 bg-slate-50 border-r border-slate-200 flex-shrink-0 flex flex-col h-full hidden md:flex">
        <div class="p-6 border-b border-slate-200">
            <h1 class="text-xl font-bold tracking-tight text-slate-900 flex items-center">
                <svg class="w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5"></path></svg>
                Lattice AIF
            </h1>
        </div>
        <nav class="flex-1 overflow-y-auto sidebar-scroll p-4 space-y-1" id="nav-menu">
            <p class="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mt-2">Getting Started</p>
            <a href="#overview" data-route="overview" class="nav-link block px-3 py-2 rounded-md text-sm text-slate-700 hover:bg-slate-100">Overview</a>
            <a href="#contributing" data-route="contributing" class="nav-link block px-3 py-2 rounded-md text-sm text-slate-700 hover:bg-slate-100">Contributing</a>
            
            <p class="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mt-6">Core Packages</p>
            <a href="#lattice-engine" data-route="lattice-engine" class="nav-link block px-3 py-2 rounded-md text-sm text-slate-700 hover:bg-slate-100">Lattice Engine</a>
            <a href="#lattice-client" data-route="lattice-client" class="nav-link block px-3 py-2 rounded-md text-sm text-slate-700 hover:bg-slate-100">Lattice Client</a>
            <a href="#lattice-server" data-route="lattice-server" class="nav-link block px-3 py-2 rounded-md text-sm text-slate-700 hover:bg-slate-100">Lattice Server</a>
        </nav>
        <div class="p-4 border-t border-slate-200">
            <a href="https://github.com/trellisAI/lattice-aif" target="_blank" class="flex items-center text-sm text-slate-600 hover:text-slate-900">
                <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub" class="w-5 h-5 mr-2 opacity-70">
                GitHub Repository
            </a>
        </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col h-full relative overflow-hidden">
        
        <!-- Mobile Header -->
        <header class="md:hidden bg-white border-b border-slate-200 p-4 flex items-center justify-between">
            <h1 class="text-lg font-bold text-slate-900 flex items-center">
                Lattice AIF
            </h1>
            <button id="mobile-menu-btn" class="p-2 text-slate-600 rounded-md hover:bg-slate-100">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
            </button>
        </header>

        <!-- Main Scrollable Area -->
        <main class="flex-1 overflow-y-auto p-6 md:p-12 lg:p-16 bg-white">
            <div class="max-w-4xl mx-auto">
                <!-- Content injected here -->
                <article id="markdown-content" class="prose prose-slate max-w-none prose-headings:tracking-tight prose-a:text-blue-600 prose-code:text-blue-800 prose-code:bg-blue-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-slate-900 prose-pre:p-0">
                </article>
            </div>
        </main>
    </div>

    <!-- Mobile menu modal -->
    <div id="mobile-menu" class="fixed inset-0 z-50 bg-slate-900/80 hidden transition-opacity">
        <div class="fixed inset-y-0 left-0 w-64 bg-white shadow-xl flex flex-col">
            <div class="p-6 border-b border-slate-200 flex items-center justify-between">
                <h1 class="text-xl font-bold tracking-tight text-slate-900">Lattice AIF</h1>
                <button id="close-mobile-menu" class="p-2 text-slate-500 hover:text-slate-700">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <nav class="flex-1 overflow-y-auto p-4 space-y-1">
                <a href="#overview" class="mobile-nav-link block px-3 py-2 rounded-md text-base font-medium text-slate-900">Overview</a>
                <a href="#contributing" class="mobile-nav-link block px-3 py-2 rounded-md text-base font-medium text-slate-900">Contributing</a>
                <div class="pt-4 pb-2">
                    <p class="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Core Packages</p>
                </div>
                <a href="#lattice-engine" class="mobile-nav-link block px-3 py-2 rounded-md text-base font-medium text-slate-900">Lattice Engine</a>
                <a href="#lattice-client" class="mobile-nav-link block px-3 py-2 rounded-md text-base font-medium text-slate-900">Lattice Client</a>
                <a href="#lattice-server" class="mobile-nav-link block px-3 py-2 rounded-md text-base font-medium text-slate-900">Lattice Server</a>
            </nav>
        </div>
    </div>

    <script>
        // Embedded documentation data
        const docData = {json_docs};

        // Set marked options for syntax highlighting
        marked.setOptions({{
            highlight: function(code, lang) {{
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, {{ language }}).value;
            }},
            langPrefix: 'hljs language-'
        }});

        const contentEl = document.getElementById('markdown-content');
        const navLinks = document.querySelectorAll('.nav-link');
        const mobileMenu = document.getElementById('mobile-menu');
        
        // Image Base URL fixer extension for marked
        const walkTokens = (token) => {{
            if (token.type === 'image') {{
                // If it's the logo in the root README, fix the path so it works from `/docs`
                if (token.href === 'docs/logo.svg' || token.href.startsWith('docs/')) {{
                    token.href = token.href.replace('docs/', '');
                }} else if (token.href === 'docs/latticeaif.drawio.svg') {{
                    token.href = 'latticeaif.drawio.svg';
                }}
            }} else if (token.type === 'link') {{
                // Conversion of file-based relative links that point to other READMEs
                if (token.href.includes('lattice-engine/README.md')) token.href = '#lattice-engine';
                if (token.href.includes('lattice-client/README.md')) token.href = '#lattice-client';
                if (token.href.includes('lattice-server/README.md')) token.href = '#lattice-server';
                if (token.href.includes('docs/CONTRIBUTING.md')) token.href = '#contributing';
            }}
        }};
        marked.use({{ walkTokens }});

        function loadContent() {{
            // Determine route from hash (remove the #)
            let route = window.location.hash.substring(1);
            
            // default route
            if (!route || !docData[route]) {{
                route = 'overview';
                window.location.hash = route;
                return; // The hash change will trigger this again
            }}

            // Get Markdown content
            const markdown = docData[route];
            
            // UI State updates
            contentEl.innerHTML = '';
            
            // Update active links
            navLinks.forEach(link => {{
                if (link.dataset.route === route) {{
                    link.classList.add('active');
                }} else {{
                    link.classList.remove('active');
                }}
            }});

            // Parse and render
            contentEl.innerHTML = marked.parse(markdown);
            
            // Scroll to top
            document.querySelector('main').scrollTop = 0;
        }}

        // Event listeners for routing
        window.addEventListener('hashchange', loadContent);
        
        // Mobile menu toggle
        document.getElementById('mobile-menu-btn').addEventListener('click', () => {{
            mobileMenu.classList.remove('hidden');
        }});
        document.getElementById('close-mobile-menu').addEventListener('click', () => {{
            mobileMenu.classList.add('hidden');
        }});
        document.querySelectorAll('.mobile-nav-link').forEach(link => {{
            link.addEventListener('click', () => {{
                mobileMenu.classList.add('hidden');
            }});
        }});

        // Initial load
        window.addEventListener('DOMContentLoaded', loadContent);
    </script>
</body>
</html>
"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print("index.html successfully updated with embedded content.")
