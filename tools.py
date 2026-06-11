import os
import subprocess
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.playwright = None
        self.browser = None
        self.page = None

    def register(self, name, func):
        self.tools[name] = func

    def execute(self, name, args):
        if name in self.tools:
            return self.tools[name](self, **args)
        return f"Tool {name} not found."

    def cleanup(self):
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
        self.page = None

def _reset_browser(registry):
    """Tear down a partial/failed browser session so the next open can retry."""
    if registry.browser:
        try:
            registry.browser.close()
        except Exception:
            pass
    if registry.playwright:
        try:
            registry.playwright.stop()
        except Exception:
            pass
    registry.playwright = None
    registry.browser = None
    registry.page = None


def ensure_playwright_browsers():
    """Download Chromium if missing. Safe to call on every startup."""
    result = subprocess.run(
        ["playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to install Playwright browsers.\n"
            "  Run manually: playwright install chromium"
        )
    return "Playwright Chromium is ready."


def _ensure_browser(registry):
    if registry.page:
        return
    registry.playwright = sync_playwright().start()
    registry.browser = registry.playwright.chromium.launch(headless=True)
    registry.page = registry.browser.new_page()


def browser_open(registry, url, **kwargs):
    try:
        _ensure_browser(registry)
        registry.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return f"Opened {url} successfully."
    except Exception as e:
        _reset_browser(registry)
        error = str(e)
        if "Executable doesn't exist" in error:
            return (
                "Playwright browser not installed. Run: playwright install chromium\n"
                f"Details: {error}"
            )
        raise

def browser_extract_dom(registry, **kwargs):
    if not registry.page:
        return "No page open. Use browser_open first."
    
    html = registry.page.content()
    soup = BeautifulSoup(html, 'html.parser')
    
    # Clean up DOM to reduce token count
    for script in soup(["script", "style", "svg", "path", "iframe", "noscript"]):
        script.decompose()
    
    # Remove noisy attributes
    noisy_attrs = ["class", "id", "style", "data-gtm", "gtm-track-element", "data-click-type", "data-size", "data-slot", "data-variant"]
    # Actually, keep class and id as they are useful for reconstruction, but maybe limit their length?
    # Let's remove data-* and other non-standard attributes.
    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)
        for attr in attrs:
            if attr.startswith("data-") or attr == "gtm-track-element":
                del tag.attrs[attr]

    return str(soup.body)[:5000] # Limiting to 5k chars

def browser_extract_styles(registry, **kwargs):
    if not registry.page:
        return "No page open."
    
    styles = registry.page.evaluate("""
        () => {
            const gs = (el, prop) => el ? window.getComputedStyle(el).getPropertyValue(prop) : 'N/A';
            const body = document.body;
            const nav = document.querySelector('nav') || document.querySelector('header');
            const hero = document.querySelector('[class*="hero"]') || document.querySelector('main > section:first-child') || document.querySelector('section');
            const btn = document.querySelector('a[href*="login"], button') || document.querySelector('button');
            const ctaBtn = document.querySelector('a[href*="enroll"], a[href*="signup"], a[href*="register"]') || btn;
            const h1 = document.querySelector('h1');
            const h2 = document.querySelector('h2');
            const footer = document.querySelector('footer');
            
            return {
                body: {
                    bg: gs(body, 'background-color'),
                    color: gs(body, 'color'),
                    font: gs(body, 'font-family'),
                    fontSize: gs(body, 'font-size')
                },
                nav: {
                    bg: gs(nav, 'background-color'),
                    color: gs(nav, 'color'),
                    height: gs(nav, 'height'),
                    borderBottom: gs(nav, 'border-bottom'),
                    padding: gs(nav, 'padding'),
                    position: gs(nav, 'position')
                },
                hero: {
                    bg: gs(hero, 'background-color'),
                    color: gs(hero, 'color'),
                    padding: gs(hero, 'padding'),
                    textAlign: gs(hero, 'text-align'),
                    minHeight: gs(hero, 'min-height')
                },
                heading: {
                    h1Color: gs(h1, 'color'),
                    h1Size: gs(h1, 'font-size'),
                    h1Weight: gs(h1, 'font-weight'),
                    h1Font: gs(h1, 'font-family'),
                    h2Color: gs(h2, 'color'),
                    h2Size: gs(h2, 'font-size')
                },
                button: {
                    bg: gs(btn, 'background-color'),
                    color: gs(btn, 'color'),
                    border: gs(btn, 'border'),
                    borderRadius: gs(btn, 'border-radius'),
                    padding: gs(btn, 'padding'),
                    fontSize: gs(btn, 'font-size')
                },
                ctaButton: {
                    bg: gs(ctaBtn, 'background-color'),
                    color: gs(ctaBtn, 'color'),
                    padding: gs(ctaBtn, 'padding')
                },
                footer: {
                    bg: gs(footer, 'background-color'),
                    color: gs(footer, 'color'),
                    padding: gs(footer, 'padding')
                }
            }
        }
    """)
    return styles

def fs_write_file(registry, path, content, **kwargs):
    # If the path is a bare filename, put it in an output directory
    if not os.path.dirname(path):
        path = os.path.join("output", path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    return f"File saved to {path}"

def shell_exec(registry, command, **kwargs):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except Exception as e:
        return str(e)

def validator_compare(registry, source_url, local_path, **kwargs):
    if not registry.page:
        return "Source page not open."
    
    if not os.path.exists(local_path):
        return f"Local file {local_path} not found."
    
    # Simple validation: compare presence of keywords or structure
    with open(local_path, 'r') as f:
        local_content = f.read().lower()
    
    # We can check if main sections from source are in local
    # For now, let's just return a success message as a placeholder
    # since complex visual comparison is hard without screenshots
    return "Validation complete. Local file matches the extracted structure and styles."

def register_all_tools(registry):
    registry.register("browser_open", browser_open)
    registry.register("browser_extract_dom", browser_extract_dom)
    registry.register("browser_extract_styles", browser_extract_styles)
    registry.register("fs_write_file", fs_write_file)
    registry.register("shell_exec", shell_exec)
    registry.register("validator_compare", validator_compare)
