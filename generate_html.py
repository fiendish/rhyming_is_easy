import os
import sys
import re

def html_escape(text):
    """Escape HTML special characters in text."""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))

def parse_image(img_str):
    """Parse an image string of the form 'filename.jpg[width]' or 'filename.jpg'. Raises ValueError on invalid input."""
    match = re.match(r"([^[\]]+)(?:\[(\d+)\])?", img_str.strip())
    if not match:
        raise ValueError(f"Invalid image string: {img_str}")
    filename = match.group(1).strip()
    width = match.group(2)
    return {'filename': filename, 'width': width}

def parse_poem_unit(poem_unit):
    """Parse a single poem unit and return its HTML representation and whether it uses left layout."""
    lines = poem_unit.strip().split('\n')
    if not lines:
        return '', False
    html = ''
    uses_left = False
    poem_lines = []
    for line in lines:
        parts = line.split(':', 1)
        prefix = parts[0].strip()
        if prefix == 'link' and len(parts) == 2:
            url = parts[1].strip()
            html += f'  <a href="{url}" target="_blank">{url}</a>\n'
        elif prefix in ('top', 'left') and len(parts) == 2:
            div_class = 'image-row' if prefix == 'top' else 'image-column'
            if prefix == 'left':
                uses_left = True
            images = [img.strip() for img in parts[1].split(',') if img.strip()]
            html += f'  <div class="{div_class}">\n'
            for img in images:
                img_info = parse_image(img)
                alt = os.path.splitext(os.path.basename(img_info['filename']))[0].replace('_', ' ')
                style = f' style="width:{img_info["width"]}px"' if img_info['width'] else ''
                html += f'    <img src="images/{img_info["filename"]}" alt="{alt}"{style}>\n'
            html += '  </div>\n'
        else:
            poem_lines.append(line)
    if poem_lines:
        html += '  <pre>' + html_escape('\n'.join(poem_lines)) + '</pre>\n'
    return html, uses_left

def parse_poems_to_html_blocks(content):
    """Parse the full poems.txt content and return a list of HTML blocks, adding 'left-image' class to units as needed."""
    content_blocks = [b.strip() for b in content.split('===') if b.strip()]
    html_blocks = []
    for block in content_blocks:
        units = [u.strip() for u in block.split('---') if u.strip()]
        unit_htmls = []
        for u in units:
            unit_html, uses_left = parse_poem_unit(u)
            unit_class = 'poem-unit left-image' if uses_left else 'poem-unit'
            unit_htmls.append(f'<div class="{unit_class}">\n{unit_html}</div>')
        html = '<div class="poem-block">\n'
        html += '\n<br>\n'.join(unit_htmls)
        html += '\n</div>'
        html_blocks.append(html)
    return html_blocks

def main():
    """Main entry point: read poems.txt, parse, and output a complete HTML page with click-to-enlarge images."""
    if len(sys.argv) < 2:
        print('Usage: python generate_html.py poems.txt > index.html')
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    html_blocks = parse_poems_to_html_blocks(content)
    # HTML template from index.html with click-to-enlarge images
    print('<!DOCTYPE html>')
    print('<html lang="en">')
    print('<head>')
    print('  <meta charset="UTF-8">')
    print('  <title>Everyday Majestic Musings</title>')
    print('  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">')
    print('  <meta http-equiv="Pragma" content="no-cache">')
    print('  <meta http-equiv="Expires" content="0">')
    print('  <link rel="stylesheet" href="style.css">')
    print('</head>')
    print('<body>')
    print('  <h1>Everyday Majestic Musings</h1>')
    print('  <main>')
    for html_block in html_blocks:
        print(html_block)
        print('    <hr>')
    print('The end.')
    print('  </main>')
    print('  <script>')
    print("""
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('img').forEach(function(img) {
      img.addEventListener('click', function(e) {
        if (img.classList.contains('enlarged-image')) {
          img.classList.remove('enlarged-image');
          const backdrop = document.querySelector('.enlarged-image-backdrop');
          if (backdrop) backdrop.remove();
        } else {
          const backdrop = document.createElement('div');
          backdrop.className = 'enlarged-image-backdrop';
          backdrop.onclick = function() {
            img.classList.remove('enlarged-image');
            backdrop.remove();
          };
          document.body.appendChild(backdrop);
          img.classList.add('enlarged-image');
        }
        e.stopPropagation();
      });
    });
  });
    """)
    print('  </script>')
    print('</body>')
    print('</html>')

if __name__ == '__main__':
    main()
