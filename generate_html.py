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

def get_video_mime_type(filename):
    """Get the MIME type for a video file based on its extension."""
    ext = os.path.splitext(filename)[1].lower()
    video_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.ogg': 'video/ogg',
        '.mov': 'video/quicktime'
    }
    return video_types.get(ext, 'video/mp4')

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
    total_poems = len(content_blocks)
    
    for i, block in enumerate(content_blocks):
        units = [u.strip() for u in block.split('---') if u.strip()]
        parsed_units = []
        for u in units:
            unit_data = parse_poem_unit(u)
            parsed_units.append(unit_data)

        # Add poem number to the block
        block_data = {
            'units': parsed_units,
            'poem_number': total_poems - i
        }
        structured_blocks.append(block_data)

    return structured_blocks

def generate_media_html(media_info):
    """Generate HTML for a single media item."""
    filename = media_info['filename']
    width = media_info['width']
    alt = os.path.splitext(os.path.basename(filename))[0].replace('_', ' ')
    style = f' style="width:{width}px"' if width else ''
    if is_video_file(filename):
        mime_type = get_video_mime_type(filename)
        return f'<video src="images/{filename}" type="{mime_type}" controls loop{style} preload="metadata">Your browser does not support the video tag.</video>'
    else:
        return f'<img src="images/{filename}" alt="{alt}"{style}>'

def generate_unit_html(unit_data):
    """Generate HTML for a single poem unit from structured data."""
    html = ''
    
    # Add links
    for url in unit_data['links']:
        html += f'  <a href="{url}" target="_blank">{url}</a>\n'
    
    # Group left images with poem content (only these go in the flex container)
    has_left = any(media_group['placement'] == 'left' for media_group in unit_data['media'])
    
    if has_left:
        # Left images in column
        for media_group in unit_data['media']:
            if media_group['placement'] == 'left':
                html += f'  <div class="image-column">\n'
                for media_info in media_group['items']:
                    html += f'    {generate_media_html(media_info)}\n'
                html += '  </div>\n'
    
    # Add poem text (will be positioned next to left images by .left-image class)
    if unit_data['poem_lines']:
        html += '  <pre>' + html_escape('\n'.join(unit_data['poem_lines'])) + '</pre>\n'
    
    return html

def has_left_placement(unit_data):
    """Check if unit has any media with left placement."""
    return any(media_group['placement'] == 'left' for media_group in unit_data['media'])

def get_first_poem_line(block_data):
    """Extract the first line of text from a poem block for use in table of contents."""
    for unit_data in block_data['units']:
        if unit_data['poem_lines']:
            # Look through all poem lines to find the first non-empty one
            for line in unit_data['poem_lines']:
                first_line = line.strip()
                if first_line:
                    # Remove existing punctuation at the end and add ellipsis
                    first_line = re.sub(r'[.!?,:;]$', '', first_line) + '...'
                    return first_line
    return "Untitled..."

def get_first_image(block_data):
    """Extract the first image filename from a poem block for thumbnails."""
    for unit_data in block_data['units']:
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

def generate_block_html(block_data):
    """Generate HTML for a block of poem units from structured data."""
    unit_htmls = []
    for unit_data in block_data['units']:
        unit_html = generate_unit_html(unit_data)
        unit_class = 'poem-unit left-image' if has_left_placement(unit_data) else 'poem-unit'
        
        # Add top images before the unit container
        top_html = ''
        for media_group in unit_data['media']:
            if media_group['placement'] == 'top':
                top_html += f'  <div class="image-row">\n'
                for media_info in media_group['items']:
                    top_html += f'    {generate_media_html(media_info)}\n'
                top_html += '  </div>\n'
        
        # Add audio players after the unit content, outside the left-image container
        audio_html = ''
        for audio_file in unit_data['audio']:
            mime_type = get_audio_mime_type(audio_file)
            audio_html += f'  <audio controls preload="metadata" style="width: 100%; max-width: 400px; margin: 10px 0;">\n'
            audio_html += f'    <source src="audio/{audio_file}" type="{mime_type}">\n'
            audio_html += f'    Your browser does not support the audio element.\n'
            audio_html += f'  </audio>\n'
        
        full_unit_html = ''
        if top_html:
            full_unit_html += top_html
        full_unit_html += f'<div class="{unit_class}">\n{unit_html}</div>'
        if audio_html:
            full_unit_html += f'\n{audio_html}'
        
        unit_htmls.append(full_unit_html)
    
    poem_number = block_data['poem_number']
    poem_id_attr = f' id="poem-{poem_number}"'
    poem_number_html = f'<div class="poem-number">{poem_number}</div>\n'
    html = f'<div class="poem-block"{poem_id_attr}>\n{poem_number_html}'
    html += '\n<br>\n'.join(unit_htmls)
    html += '\n</div>'
    return html

def write_html_header(f, title, show_toc_link=True):
    """Write the HTML header with common meta tags, CSS, and banner."""
    css_version = int(time.time())
    f.write('<!DOCTYPE html>\n')
    f.write('<html lang="en">\n')
    f.write('<head>\n')
    f.write('  <meta charset="UTF-8">\n')
    f.write(f'  <title>{title}</title>\n')
    f.write('  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">\n')
    f.write('  <meta http-equiv="Pragma" content="no-cache">\n')
    f.write('  <meta http-equiv="Expires" content="0">\n')
    f.write(f'  <link rel="stylesheet" href="style.css?v={css_version}">\n')
    f.write('</head>\n')
    f.write('<body>\n')
    f.write('  <header class="banner">\n')
    f.write('    <h1><a href="index.html" style="color: inherit; text-decoration: none;">Everyday Majestic Musings</a></h1>\n')
    visibility_style = '' if show_toc_link else ' style="visibility: hidden;"'
    element_tag = 'a href="poems.html"' if show_toc_link else 'div'
    f.write(f'    <{element_tag} class="table-of-contents-link"{visibility_style}>Go to Table of Contents</{"a" if show_toc_link else "div"}>\n')
    f.write('  </header>\n')

def write_image_enlargement_script(f):
    """Write the JavaScript for image enlargement functionality."""
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

def write_page(structured_blocks, page_num, total_pages):
    """Write a single HTML page with navigation links and 'The end.' on the last page."""
    filename = 'index.html' if page_num == 1 else f'page{page_num}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        write_html_header(f, 'Everyday Majestic Musings')
        f.write('  <main>\n')
        for i, block_data in enumerate(structured_blocks):
            html_block = generate_block_html(block_data)
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
        write_image_enlargement_script(f)
        f.write('</body>\n')
        f.write('</html>\n')

def write_table_of_contents(structured_blocks):
    """Write a table of contents page with links to each poem."""
    with open('poems.html', 'w', encoding='utf-8') as f:
        write_html_header(f, 'Table of Contents - Everyday Majestic Musings', show_toc_link=False)
        f.write('  <main>\n')
        f.write('    <h2>Table of Contents</h2>\n')
        f.write('    <ul style="line-height: 1.8; margin-bottom: 2em; list-style: none; padding-left: 0;">\n')
        
        poems_per_page = 5
        total_poems = len(structured_blocks)
        for i, block_data in enumerate(structured_blocks):
            page_num = (i // poems_per_page) + 1
            page_file = 'index.html' if page_num == 1 else f'page{page_num}.html'
            first_line = get_first_poem_line(block_data)
            first_image = get_first_image(block_data)
            poem_number = block_data['poem_number']
            
            if first_image:
                thumbnail_html = f'<img src="images/{first_image}" alt="" style="max-width: 96px; max-height: 96px; margin-right: 0.5em; vertical-align: middle; border-radius: 3px; cursor: default;">'
                f.write(f'      <li style="display: flex; align-items: center; margin-bottom: 0.5em;"><span style="font-weight: bold; min-width: 2.5em; margin-right: 0.5em;">{poem_number}.</span>{thumbnail_html}<a href="{page_file}#poem-{poem_number}">{html_escape(first_line)}</a></li>\n')
            else:
                f.write(f'      <li style="display: flex; align-items: center; margin-bottom: 0.5em;"><span style="font-weight: bold; min-width: 2.5em; margin-right: 0.5em;">{poem_number}.</span><a href="{page_file}#poem-{poem_number}">{html_escape(first_line)}</a></li>\n')
        
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
