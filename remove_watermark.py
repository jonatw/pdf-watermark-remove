import fitz
import asyncio
import re
from collections import Counter

def most_frequent_text_tj_substring(doc, window=300, min_length=30):
    counter = Counter()
    for page in doc:
        for xref in page.get_contents():
            content = doc.xref_stream(xref)
            i = 0
            while i < len(content):
                if content[i:i+1] == b'(':
                    end = content.find(b') Tj', i)
                    if end != -1 and end - i < window:
                        substring = content[i:end+4]
                        if len(substring) >= min_length:
                            counter[substring] += 1
                        i = end + 4
                        continue
                if content[i:i+1] == b'<':
                    end = content.find(b'> Tj', i)
                    if end != -1 and end - i < window:
                        substring = content[i:end+4]
                        if len(substring) >= min_length:
                            counter[substring] += 1
                        i = end + 4
                        continue
                if content[i:i+1] == b'[':
                    end = content.find(b'] TJ', i)
                    if end != -1 and end - i < window:
                        substring = content[i:end+5]
                        if len(substring) >= min_length:
                            counter[substring] += 1
                        i = end + 5
                        continue
                i += 1
    if not counter:
        return None, 0

    print("Top 5 candidates (min length applied):")
    for s, c in counter.most_common(5):
        try:
            print(f"  {s.decode('utf-8', errors='replace')} x {c}")
        except:
            print(f"  {s[:60]}... x {c}")

    return counter.most_common(1)[0]

async def remove_watermark_from_page(doc, page_number, target_str):
    page = doc[page_number]
    replaced = 0
    for xref in page.get_contents():
        raw = doc.xref_stream(xref)
        raw_str = raw.decode("latin1")

        blocks = re.findall(r"q\s+.*?Q", raw_str, flags=re.DOTALL)
        for block in blocks:
            if target_str in block:
                raw_str = raw_str.replace(block, "")
                replaced += 1
        if replaced:
            # print(f"Page {page_number}: removed {replaced} block(s)")
            doc.update_stream(xref, raw_str.encode("latin1"))

async def remove_watermark_by_common_str(input_file, output_file):
    doc = fitz.open(input_file)
    most_common, freq = most_frequent_text_tj_substring(doc, min_length=30)

    if not most_common or freq < 1:
        print("No watermark pattern detected.")
        return

    try:
        target_str = most_common.decode('latin1').strip()
    except:
        target_str = most_common.hex()

    print(f"\nDetected watermark (freq={freq}):")
    print(target_str)

    # 平行處理每頁
    tasks = [remove_watermark_from_page(doc, page.number, target_str) for page in doc]
    await asyncio.gather(*tasks)

    doc.save(output_file, garbage=4, deflate=True, clean=True)

async def remove_watermark_by_xref(input_file, output_file):
    doc = fitz.open(input_file)
    def get_target_xref_at_first_page(doc):
        xref_patterns = [
            {'height': 2360, 'width': 1640},
            {'height': 1640, 'width': 2360}
        ]
        image_list = doc[0].get_image_info(xrefs=True)
        for image_info in image_list:
            for pattern in xref_patterns:
                if image_info['width'] == pattern['width'] and image_info['height'] == pattern['height']:
                    return image_info['xref']
        return None

    target_xref = get_target_xref_at_first_page(doc)
    if target_xref:
        doc[0].delete_image(target_xref)
        doc.ez_save(output_file)

async def remove_watermark(input_file, output_file):
    doc = fitz.open(input_file)
    if 'Version' in doc.metadata.get('producer', ''):
        await remove_watermark_by_xref(input_file, output_file)
    else:
        await remove_watermark_by_common_str(input_file, output_file)