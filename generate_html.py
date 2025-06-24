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

def is_video_file(filename):
    video_exts = {'.mp4', '.webm', '.ogg', '.mov'}
    return os.path.splitext(filename)[1].lower() in video_exts

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
            media = [m.strip() for m in parts[1].split(',') if m.strip()]
            html += f'  <div class="{div_class}">\n'
            for m in media:
                media_info = parse_image(m)
                filename = media_info['filename']
                width = media_info['width']
                alt = os.path.splitext(os.path.basename(filename))[0].replace('_', ' ')
                style = f' style="width:{width}px"' if width else ''
                if is_video_file(filename):
                    html += f'    <video src="images/{filename}" controls loop{style} preload="metadata">Your browser does not support the video tag.</video>\n'
                else:
                    html += f'    <img src="images/{filename}" alt="{alt}"{style}>\n'
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

def write_page(html_blocks, page_num, total_pages):
    """Write a single HTML page with navigation links and 'The end.' on the last page."""
    filename = 'index.html' if page_num == 1 else f'page{page_num}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html>\n')
        f.write('<html lang="en">\n')
        f.write('<head>\n')
        f.write('  <meta charset="UTF-8">\n')
        f.write('  <title>Everyday Majestic Musings</title>\n')
        f.write('  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">\n')
        f.write('  <meta http-equiv="Pragma" content="no-cache">\n')
        f.write('  <meta http-equiv="Expires" content="0">\n')
        f.write('  <link rel="stylesheet" href="style.css">\n')
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('  <header class="banner">\n')
        f.write('    <h1>Everyday Majestic Musings</h1>\n')
        f.write('  </header>\n')
        f.write('  <main>\n')
        for html_block in html_blocks:
            f.write(html_block + '\n    <hr>\n')
        # Add 'The end.' only on the last page
        if page_num == total_pages:
            f.write('The end.\n')
        # Navigation
        f.write('<div class="pagination" style="text-align:center;margin:2em 0 1em 0;font-size:1.2em;">\n')
        if page_num > 1:
            prev_file = 'index.html' if page_num == 2 else f'page{page_num-1}.html'
            f.write(f'<a href="{prev_file}">&laquo; Prev</a> ')
        f.write(f' Page {page_num} of {total_pages} ')
        if page_num < total_pages:
            next_file = f'page{page_num+1}.html'
            f.write(f'<a href="{next_file}">Next &raquo;</a>')
        f.write('</div>\n')
        f.write('  </main>\n')
        f.write('  <script>\n')
        f.write("""
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
        f.write('  </script>\n')
        f.write('</body>\n')
        f.write('</html>\n')

def main():
    """Main entry point: read poems.txt, parse, and output paginated HTML pages."""
    if len(sys.argv) < 2:
        print('Usage: python generate_html.py poems.txt')
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    html_blocks = parse_poems_to_html_blocks(content)
    poems_per_page = 5
    total_pages = (len(html_blocks) + poems_per_page - 1) // poems_per_page
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * poems_per_page
        end = start + poems_per_page
        write_page(html_blocks[start:end], page_num, total_pages)

if __name__ == '__main__':
    main()
