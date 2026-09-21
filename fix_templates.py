import os
import re

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to replace public titles/descriptors, but not break factual context.
    # The prompt says:
    # "Page <title> tags and the visible site wordmark in all templates"
    
    new_content = content
    # Handle KOHLER -> Plumbline in titles and wordmarks
    new_content = re.sub(r'(?i)KOHLER AI Bathroom Designer(?:\s*&\s*Planner)?', 'Plumbline', new_content)
    new_content = re.sub(r'(?i)KOHLER Spatial Studio & Planner', 'Plumbline', new_content)
    new_content = re.sub(r'(?i)KOHLER Spatial Architecture Studio', 'Plumbline', new_content)
    new_content = re.sub(r'(?i)KOHLER Architectural Studio', 'Plumbline', new_content)
    new_content = re.sub(r'css/kohler\.css', 'css/plumbline.css', new_content)
    new_content = re.sub(r'saved_kohler_canvas', 'saved_plumbline_canvas', new_content)
    new_content = re.sub(r'>KOHLER<', '>PLUMBLINE<', new_content)
    new_content = re.sub(r'\|\s*KOHLER', '| Plumbline', new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            replace_in_file(os.path.join(root, file))
