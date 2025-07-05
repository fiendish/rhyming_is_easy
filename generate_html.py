import os
import sys
import re
import time

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

def get_audio_mime_type(filename):
    """Get the MIME type for an audio file based on its extension."""
    ext = os.path.splitext(filename)[1].lower()
    audio_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.webm': 'audio/webm',
        '.flac': 'audio/flac'
    }
    return audio_types.get(ext, 'audio/mpeg')

def parse_poem_unit(poem_unit):
    """Parse a single poem unit and return its structured data representation."""
    lines = poem_unit.strip().split('\n')
    if not lines:
        return {'links': [], 'media': [], 'audio': [], 'poem_lines': [], 'uses_left': False}
    
    links = []
    media = []
    audio = []
    poem_lines = []
    
    for line in lines:
        parts = line.split(':', 1)
        prefix = parts[0].strip()
        if prefix == 'link' and len(parts) == 2:
            url = parts[1].strip()
            links.append(url)
        elif prefix == 'audio' and len(parts) == 2:
            audio_file = parts[1].strip()
            audio.append(audio_file)
        elif prefix in ('top', 'left') and len(parts) == 2:
            placement = prefix
            media_items = [m.strip() for m in parts[1].split(',') if m.strip()]
            parsed_media = []
            for m in media_items:
                media_info = parse_image(m)
                parsed_media.append(media_info)

            media.append({'placement': placement, 'items': parsed_media})
        else:
            poem_lines.append(line)
    
    return {
        'links': links,
        'media': media,
        'audio': audio,
        'poem_lines': poem_lines
    }

def parse_poems_to_structured_data(content):
    """Parse the full poems.txt content and return structured data."""
    content_blocks = [b.strip() for b in content.split('===') if b.strip()]
    structured_blocks = []
    for block in content_blocks:
        units = [u.strip() for u in block.split('---') if u.strip()]
        parsed_units = []
        for u in units:
            unit_data = parse_poem_unit(u)
            parsed_units.append(unit_data)

        structured_blocks.append(parsed_units)

    return structured_blocks

def generate_unit_html(unit_data):
    """Generate HTML for a single poem unit from structured data."""
    html = ''
    
    # Add links
    for url in unit_data['links']:
        html += f'  <a href="{url}" target="_blank">{url}</a>\n'
    
    # Add media
    for media_group in unit_data['media']:
        placement = media_group['placement']
        div_class = 'image-row' if placement == 'top' else 'image-column'
        html += f'  <div class="{div_class}">\n'
        for media_info in media_group['items']:
            filename = media_info['filename']
            width = media_info['width']
            alt = os.path.splitext(os.path.basename(filename))[0].replace('_', ' ')
            style = f' style="width:{width}px"' if width else ''
            if is_video_file(filename):
                html += f'    <video src="images/{filename}" controls loop{style} preload="metadata">Your browser does not support the video tag.</video>\n'
            else:
                html += f'    <img src="images/{filename}" alt="{alt}"{style}>\n'

        html += '  </div>\n'
    
    # Add poem text
    if unit_data['poem_lines']:
        html += '  <pre>' + html_escape('\n'.join(unit_data['poem_lines'])) + '</pre>\n'
    
    # Add audio players
    for audio_file in unit_data['audio']:
        mime_type = get_audio_mime_type(audio_file)
        html += f'  <audio controls preload="metadata" style="width: 100%; max-width: 400px; margin: 10px 0;">\n'
        html += f'    <source src="audio/{audio_file}" type="{mime_type}">\n'
        html += f'    Your browser does not support the audio element.\n'
        html += f'  </audio>\n'
    
    return html

def has_left_placement(unit_data):
    """Check if unit has any media with left placement."""
    return any(media_group['placement'] == 'left' for media_group in unit_data['media'])

def get_first_poem_line(block_units):
    """Extract the first line of text from a poem block for use in table of contents."""
    for unit_data in block_units:
        if unit_data['poem_lines']:
            # Look through all poem lines to find the first non-empty one
            for line in unit_data['poem_lines']:
                first_line = line.strip()
                if first_line:
                    # Remove existing punctuation at the end and add ellipsis
                    first_line = re.sub(r'[.!?,:;]$', '', first_line) + '...'
                    return first_line
    return "Untitled..."

def get_first_image(block_units):
    """Extract the first image filename from a poem block for thumbnails."""
    for unit_data in block_units:
        if unit_data['media']:
            for media_group in unit_data['media']:
                if media_group['items']:
                    first_media = media_group['items'][0]
                    filename = first_media['filename']
                    # If it's an image, return it directly
                    if not is_video_file(filename):
                        return filename
                    # If it's a video, check for image with same base name
                    else:
                        base_name = os.path.splitext(filename)[0]
                        # Check for common image extensions
                        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            image_filename = base_name + ext
                            if os.path.exists(f'images/{image_filename}'):
                                return image_filename
    return None

def generate_block_html(block_units, poem_id=None):
    """Generate HTML for a block of poem units from structured data."""
    unit_htmls = []
    for unit_data in block_units:
        unit_html = generate_unit_html(unit_data)
        unit_class = 'poem-unit left-image' if has_left_placement(unit_data) else 'poem-unit'
        unit_htmls.append(f'<div class="{unit_class}">\n{unit_html}</div>')
    
    poem_id_attr = f' id="poem-{poem_id}"' if poem_id is not None else ''
    html = f'<div class="poem-block"{poem_id_attr}>\n'
    html += '\n<br>\n'.join(unit_htmls)
    html += '\n</div>'
    return html

def write_page(structured_blocks, page_num, total_pages):
    """Write a single HTML page with navigation links and 'The end.' on the last page."""
    filename = 'index.html' if page_num == 1 else f'page{page_num}.html'
    css_version = int(time.time())
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html>\n')
        f.write('<html lang="en">\n')
        f.write('<head>\n')
        f.write('  <meta charset="UTF-8">\n')
        f.write('  <title>Everyday Majestic Musings</title>\n')
        f.write('  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">\n')
        f.write('  <meta http-equiv="Pragma" content="no-cache">\n')
        f.write('  <meta http-equiv="Expires" content="0">\n')
        f.write(f'  <link rel="stylesheet" href="style.css?v={css_version}">\n')
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('  <header class="banner">\n')
        f.write('    <h1><a href="poems.html" style="color: inherit; text-decoration: none;">Everyday Majestic Musings</a></h1>\n')
        f.write('  </header>\n')
        f.write('  <main>\n')
        for i, block_units in enumerate(structured_blocks):
            poem_id = (page_num - 1) * 5 + i
            html_block = generate_block_html(block_units, poem_id)
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

def write_table_of_contents(structured_blocks):
    """Write a table of contents page with links to each poem."""
    css_version = int(time.time())
    with open('poems.html', 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html>\n')
        f.write('<html lang="en">\n')
        f.write('<head>\n')
        f.write('  <meta charset="UTF-8">\n')
        f.write('  <title>Table of Contents - Everyday Majestic Musings</title>\n')
        f.write('  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">\n')
        f.write('  <meta http-equiv="Pragma" content="no-cache">\n')
        f.write('  <meta http-equiv="Expires" content="0">\n')
        f.write(f'  <link rel="stylesheet" href="style.css?v={css_version}">\n')
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('  <header class="banner">\n')
        f.write('    <h1><a href="/" style="color: inherit; text-decoration: none;">Everyday Majestic Musings</a></h1>\n')
        f.write('  </header>\n')
        f.write('  <main>\n')
        f.write('    <h2>Table of Contents</h2>\n')
        f.write('    <ul style="line-height: 1.8; margin-bottom: 2em; list-style: none; padding-left: 0;">\n')
        
        poems_per_page = 5
        total_poems = len(structured_blocks)
        for i, block_units in enumerate(structured_blocks):
            page_num = (i // poems_per_page) + 1
            page_file = 'index.html' if page_num == 1 else f'page{page_num}.html'
            first_line = get_first_poem_line(block_units)
            first_image = get_first_image(block_units)
            poem_number = total_poems - i  # Reverse numbering so newest (first) has highest number
            
            if first_image:
                thumbnail_html = f'<img src="images/{first_image}" alt="" style="max-width: 96px; max-height: 96px; margin-right: 0.5em; vertical-align: middle; border-radius: 3px; cursor: default;">'
                f.write(f'      <li style="display: flex; align-items: center; margin-bottom: 0.5em;"><span style="font-weight: bold; min-width: 2.5em; margin-right: 0.5em;">{poem_number}.</span>{thumbnail_html}<a href="{page_file}#poem-{i}">{html_escape(first_line)}</a></li>\n')
            else:
                f.write(f'      <li style="display: flex; align-items: center; margin-bottom: 0.5em;"><span style="font-weight: bold; min-width: 2.5em; margin-right: 0.5em;">{poem_number}.</span><a href="{page_file}#poem-{i}">{html_escape(first_line)}</a></li>\n')
        
        f.write('    </ul>\n')
        f.write('  </main>\n')
        f.write('</body>\n')
        f.write('</html>\n')

def main():
    """Main entry point: read poems.txt, parse, and output paginated HTML pages."""
    if len(sys.argv) < 2:
        print('Usage: python generate_html.py poems.txt')
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()

    structured_blocks = parse_poems_to_structured_data(content)
    poems_per_page = 5
    total_pages = (len(structured_blocks) + poems_per_page - 1) // poems_per_page
    
    # Write the main pages
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * poems_per_page
        end = start + poems_per_page
        write_page(structured_blocks[start:end], page_num, total_pages)
    
    # Write the table of contents
    write_table_of_contents(structured_blocks)

if __name__ == '__main__':
    main()
