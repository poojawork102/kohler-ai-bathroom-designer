import re

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace H1 and opening
content = re.sub(
    r'# KOHLER AI Bathroom Designer & Planner\n+.*?\n+',
    '# Plumbline\n\n**Conversational bathroom design with verified spatial compliance**\n\n',
    content
)

# Git clone paths
content = content.replace('kohler-ai-bathroom-designer', 'plumbline')

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)

notice_content = """# Notice
This repository is an independent student case-study prototype, is not affiliated with or endorsed by any manufacturer, and product data is a representative sample compiled from public specifications for demonstration purposes.
"""
with open('NOTICE.md', 'w', encoding='utf-8') as f:
    f.write(notice_content)

print("Updated README.md and created NOTICE.md")
