import re, pathlib
code = pathlib.Path(r"C:\Users\Admin\.gemini\config\skills\excaliflow\scripts\generate_diagram.py").read_text(encoding="utf-8")
for m in re.finditer(r'<button[^>]*id=["\x27]([^"\x27]+)["\x27][^>]*>(.*?)</button>', code, re.DOTALL):
    print(f"Button ID: {m.group(1):25} Text: {m.group(2).strip()}")