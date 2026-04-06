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
<html lang="en" class="antialiased scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lattice AIF Documentation</title>
    
    <!-- Tailwind CSS with Typography -->
    <script src="https://cdn.tailwindcss.com?plugins=typography"></script>
    <script>
      tailwind.config = {{
        darkMode: 'class',
        theme: {{
          extend: {{
            fontFamily: {{
              sans: ['Inter', 'sans-serif'],
            }},
            colors: {{
              brand: {{
                50: '#eff6ff', 100: '#dbeafe', 400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 900: '#1e3a8a'
              }}
            }},
            typography: (theme) => ({{
              DEFAULT: {{
                css: {{
                  maxWidth: '100%',
                  color: theme('colors.slate.600'),
                  h1: {{ color: theme('colors.slate.900'), fontWeight: '800', letterSpacing: '-0.025em' }},
                  h2: {{ color: theme('colors.slate.900'), fontWeight: '700', letterSpacing: '-0.025em', marginTop: '2em' }},
                  h3: {{ color: theme('colors.slate.900'), fontWeight: '600' }},
                  'code::before': {{ content: '""' }},
                  'code::after': {{ content: '""' }},
                  code: {{
                    color: theme('colors.rose.500'),
                    backgroundColor: theme('colors.slate.100'),
                    padding: '0.25rem 0.375rem',
                    borderRadius: '0.375rem',
                    fontWeight: '500',
                    fontSize: '0.875em',
                  }},
                  a: {{
                    color: theme('colors.brand.600'),
                    textDecoration: 'none',
                    fontWeight: '500',
                    '&:hover': {{ textDecoration: 'underline' }},
                  }},
                  blockquote: {{
                    borderLeftColor: theme('colors.brand.500'),
                    backgroundColor: theme('colors.brand.50'),
                    padding: '1rem',
                    borderRadius: '0.5rem',
                    fontStyle: 'normal',
                    color: theme('colors.slate.700'),
                  }}
                }}
              }},
              invert: {{
                css: {{
                  color: theme('colors.slate.300'),
                  h1: {{ color: theme('colors.white') }},
                  h2: {{ color: theme('colors.white') }},
                  h3: {{ color: theme('colors.slate.100') }},
                  code: {{
                    color: theme('colors.rose.400'),
                    backgroundColor: theme('colors.slate.800'),
                  }},
                  a: {{
                    color: theme('colors.brand.400'),
                  }},
                  blockquote: {{
                    backgroundColor: theme('colors.brand.900'),
                    borderColor: theme('colors.brand.400'),
                    color: theme('colors.slate.200'),
                  }}
                }}
              }}
            }})
          }}
        }}
      }}
    </script>
    
    <!-- Highlight.js for Syntax Highlighting (Atom One Dark theme for premium look) -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    
    <!-- Marked.js for Markdown Parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            -webkit-font-smoothing: antialiased;
        }}
        
        .nav-link {{
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }}
        
        /* Modern active state with left border accent */
        .nav-link.active {{
            background-color: #eff6ff; /* brand-50 */
            color: #2563eb; /* brand-600 */
            font-weight: 600;
        }}
        
        .dark .nav-link.active {{
            background-color: rgba(30, 58, 138, 0.4); /* brand-900 w/ opacity */
            color: #60a5fa; /* brand-400 */
        }}
        
        .nav-link.active::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background-color: #3b82f6; /* brand-500 */
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }}

        /* Elegant custom scrollbar */
        .sidebar-scroll::-webkit-scrollbar {{ width: 5px; height: 5px; }}
        .sidebar-scroll::-webkit-scrollbar-track {{ background: transparent; }}
        .sidebar-scroll::-webkit-scrollbar-thumb {{ background-color: #cbd5e1; border-radius: 10px; }}
        .dark .sidebar-scroll::-webkit-scrollbar-thumb {{ background-color: #475569; }}
        .sidebar-scroll:hover::-webkit-scrollbar-thumb {{ background-color: #94a3b8; }}

        /* Prism/Highlight JS pre padding fix */
        pre code.hljs {{
            padding: 1.25rem;
            border-radius: 0.75rem;
            font-size: 0.875rem;
            line-height: 1.5;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }}
    </style>
</head>
<body class="bg-white text-slate-800 dark:bg-slate-950 dark:text-slate-300 flex h-screen overflow-hidden transition-colors duration-300">

    <!-- Desktop Sidebar (Glassmorphism effect) -->
    <aside class="w-72 bg-slate-50/80 dark:bg-slate-900/80 backdrop-blur-xl border-r border-slate-200 dark:border-slate-800 flex-shrink-0 flex flex-col h-full hidden md:flex z-10 transition-colors duration-300">
        <div class="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <h1 class="text-xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center">
                <svg class="w-6 h-6 mr-2 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5"></path>
                </svg>
                Lattice AIF
            </h1>
            <!-- Dark Mode Toggle Desktop -->
            <button id="theme-toggle" class="p-2 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors">
                <svg id="theme-toggle-dark-icon" class="w-5 h-5 hidden" fill="currentColor" viewBox="0 0 20 20"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path></svg>
                <svg id="theme-toggle-light-icon" class="w-5 h-5 hidden" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"></path></svg>
            </button>
        </div>
        
        <nav class="flex-1 overflow-y-auto sidebar-scroll px-4 py-6 space-y-1" id="nav-menu">
            <p class="px-3 py-2 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Getting Started</p>
            <a href="#overview" data-route="overview" class="nav-link block px-3 py-2.5 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">Overview</a>
            <a href="#contributing" data-route="contributing" class="nav-link block px-3 py-2.5 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">Contributing</a>
            
            <p class="px-3 py-2 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mt-8">Core Packages</p>
            <a href="#lattice-engine" data-route="lattice-engine" class="nav-link block px-3 py-2.5 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">Lattice Engine</a>
            <a href="#lattice-client" data-route="lattice-client" class="nav-link block px-3 py-2.5 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">Lattice Client</a>
            <a href="#lattice-server" data-route="lattice-server" class="nav-link block px-3 py-2.5 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">Lattice Server</a>
        </nav>
        
        <div class="p-4 border-t border-slate-200 dark:border-slate-800">
            <a href="https://github.com/trellisAI/lattice-aif" target="_blank" class="flex items-center text-sm font-medium text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors">
                <svg class="w-5 h-5 mr-3 opacity-80" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                GitHub Repository
            </a>
        </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col h-full relative overflow-hidden bg-white dark:bg-slate-950 transition-colors duration-300">
        
        <!-- Mobile Header (Glassmorphism) -->
        <header class="md:hidden bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl border-b border-slate-200 dark:border-slate-800 p-4 flex items-center justify-between sticky top-0 z-20">
            <h1 class="text-lg font-bold text-slate-900 dark:text-white flex items-center">
                <svg class="w-5 h-5 mr-2 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5"></path>
                </svg>
                Lattice AIF
            </h1>
            <div class="flex items-center space-x-2">
                <button id="mobile-theme-toggle" class="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg">
                   <!-- icons injected via JS to mirror desktop -->
                </button>
                <button id="mobile-menu-btn" class="p-2 text-slate-600 dark:text-slate-400 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                </button>
            </div>
        </header>

        <!-- Main Scrollable Area -->
        <main id="main-scroll-area" class="flex-1 overflow-y-auto px-6 py-10 md:px-12 md:py-16 lg:px-24">
            <div class="max-w-4xl mx-auto">                
                <!-- Content injected here -->
                <article id="markdown-content" class="prose prose-slate dark:prose-invert prose-lg max-w-none transition-opacity duration-300">
                    <!-- The generated HTML goes here -->
                </article>
                
                <!-- Footer within content limits -->
                <footer class="mt-20 pt-8 border-t border-slate-200 dark:border-slate-800 flex flex-col md:flex-row justify-between items-center text-sm text-slate-500">
                    <p>© 2026 Lattice AIF. Released under MIT License.</p>
                    <a href="#" onclick="window.scrollTo(0,0)" class="mt-4 md:mt-0 hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Back to top ↑</a>
                </footer>
            </div>
        </main>
    </div>

    <!-- Mobile menu modal -->
    <div id="mobile-menu" class="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm hidden transition-opacity">
        <div class="fixed inset-y-0 right-0 w-72 bg-white dark:bg-slate-900 shadow-2xl flex flex-col transform transition-transform">
            <div class="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <h1 class="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Menu</h1>
                <button id="close-mobile-menu" class="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white bg-slate-100 dark:bg-slate-800 rounded-full">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <nav class="flex-1 overflow-y-auto p-4 space-y-1">
                <a href="#overview" class="mobile-nav-link block px-4 py-3 rounded-xl text-base font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">Overview</a>
                <a href="#contributing" class="mobile-nav-link block px-4 py-3 rounded-xl text-base font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">Contributing</a>
                <div class="pt-6 pb-2">
                    <p class="px-4 text-xs font-bold text-brand-500 uppercase tracking-widest">Core Packages</p>
                </div>
                <a href="#lattice-engine" class="mobile-nav-link block px-4 py-3 rounded-xl text-base font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">Lattice Engine</a>
                <a href="#lattice-client" class="mobile-nav-link block px-4 py-3 rounded-xl text-base font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">Lattice Client</a>
                <a href="#lattice-server" class="mobile-nav-link block px-4 py-3 rounded-xl text-base font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">Lattice Server</a>
            </nav>
        </div>
    </div>

    <script>
        // Theme initialization
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
            document.documentElement.classList.add('dark');
        }} else {{
            document.documentElement.classList.remove('dark');
        }}

        // Embedded documentation data
        const docData = {json_docs};

        // Set marked options for syntax highlighting
        marked.setOptions({{
            highlight: function(code, lang) {{
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, {{ language }}).value;
            }},
            langPrefix: 'hljs language-',
            gfm: true
        }});

        const contentEl = document.getElementById('markdown-content');
        const navLinks = document.querySelectorAll('.nav-link');
        const mobileMenu = document.getElementById('mobile-menu');
        
        // Image Base URL fixer extension for marked
        const walkTokens = (token) => {{
            if (token.type === 'image') {{
                if (token.href === 'docs/logo.svg' || token.href.startsWith('docs/')) {{
                    token.href = token.href.replace('docs/', '');
                }} else if (token.href === 'docs/latticeaif.drawio.svg') {{
                    token.href = 'latticeaif.drawio.svg';
                }}
            }} else if (token.type === 'link') {{
                if (token.href.includes('lattice-engine/README.md')) token.href = '#lattice-engine';
                if (token.href.includes('lattice-client/README.md')) token.href = '#lattice-client';
                if (token.href.includes('lattice-server/README.md')) token.href = '#lattice-server';
                if (token.href.includes('docs/CONTRIBUTING.md')) token.href = '#contributing';
            }}
        }};
        marked.use({{ walkTokens }});

        function loadContent() {{
            let route = window.location.hash.substring(1);
            if (!route || !docData[route]) {{
                route = 'overview';
                window.location.hash = route;
                return; 
            }}

            // Smooth fade effect
            contentEl.style.opacity = '0';
            
            setTimeout(() => {{
                // Update content
                contentEl.innerHTML = marked.parse(docData[route]);
                
                // Update active links
                navLinks.forEach(link => {{
                    if (link.dataset.route === route) {{
                        link.classList.add('active');
                    }} else {{
                        link.classList.remove('active');
                    }}
                }});
                
                // Scroll to top
                document.getElementById('main-scroll-area').scrollTop = 0;
                
                // Fade in
                contentEl.style.opacity = '1';
            }}, 150);
        }}

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

        // Dark mode toggle logic
        const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
        const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');

        function updateThemeIcons() {{
            if (document.documentElement.classList.contains('dark')) {{
                themeToggleLightIcon.classList.remove('hidden');
                themeToggleDarkIcon.classList.add('hidden');
            }} else {{
                themeToggleLightIcon.classList.add('hidden');
                themeToggleDarkIcon.classList.remove('hidden');
            }}
        }}

        const toggleTheme = () => {{
            document.documentElement.classList.toggle('dark');
            if (document.documentElement.classList.contains('dark')) {{
                localStorage.theme = 'dark';
            }} else {{
                localStorage.theme = 'light';
            }}
            updateThemeIcons();
        }};

        document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
        
        // Mirror mobile button
        const mobileThemeToggle = document.getElementById('mobile-theme-toggle');
        mobileThemeToggle.innerHTML = document.getElementById('theme-toggle').innerHTML;
        mobileThemeToggle.addEventListener('click', () => {{
            toggleTheme();
            mobileThemeToggle.innerHTML = document.getElementById('theme-toggle').innerHTML;
            updateThemeIcons(); // Resync classes inside the copied HTML
        }});
        
        // Initial setup
        updateThemeIcons();
        window.addEventListener('DOMContentLoaded', loadContent);

    </script>
</body>
</html>
"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print("index.html successfully updated with premium embedded content.")
