from docx import Document
import sys

doc = Document(sys.argv[1])
for i, p in enumerate(doc.paragraphs):
    print(f"P{i}: {p.text}")

print("================= FOOTNOTES ===================")
try:
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    # Extract footnotes
    import xml.etree.ElementTree as ET
    for rel in doc.part.rels.values():
        if "footnotes" in rel.target_ref:
            footnotes_part = rel.target_part
            root = ET.fromstring(footnotes_part.blob)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            for footnote in root.findall('w:footnote', ns):
                id = footnote.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                texts = []
                for t in footnote.findall('.//w:t', ns):
                    if t.text:
                        texts.append(t.text)
                if texts:
                    print(f"FN {id}: {''.join(texts)}")
except Exception as e:
    print(e)
