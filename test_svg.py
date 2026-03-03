import re
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication

app = QApplication([])

def inject(svg_name, colorHex):
    with open(f"icons/{svg_name}", 'r') as f:
        svg_data = f.read()

    print("--- BEFORE ---")
    print(svg_data)
        
    svg_data = re.sub(r'fill="[^"]+"', '', svg_data)
    for tag in ['path', 'circle', 'rect', 'polygon']:
        svg_data = svg_data.replace(f'<{tag} ', f'<{tag} fill="{colorHex}" ')

    print("--- AFTER ---")
    print(svg_data)

    r = QSvgRenderer(bytearray(svg_data, encoding='utf-8'))
    print("isValid() =", r.isValid())

inject("musical-notes.svg", "#ffffff")
