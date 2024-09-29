import fitz, asyncio

async def remove_watermark_from_page(page, most_frequent):
    page.clean_contents()
    xref = page.get_contents()[0]
    cont = bytearray(page.read_contents())
    while True:
        i1 = cont.find(most_frequent)
        if i1 < 0: break
        cont[i1 : i1+len(most_frequent)] = b""
    page.parent.update_stream(xref, cont)

async def remove_watermark_by_common_str(input_file, output_file):
    doc = fitz.open(input_file)

    def most_frequent_substring_with_pattern(byte_array, pattern, length):
        count = {}
        pattern_length = len(pattern)
        i = 0

        while i < len(byte_array) - pattern_length:
            # Find the occurrence of the pattern
            if byte_array[i:i + pattern_length] == pattern:
                # Extract the substring of the desired length after the pattern
                substring = bytes(byte_array[i:i + pattern_length + length])
                # Count the frequency
                count[substring] = count.get(substring, 0) + 1
                # Move past this occurrence
                i += pattern_length
            else:
                i += 1
        # Find the most frequent substring
        most_frequent = max(count, key=count.get)
        return most_frequent, count[most_frequent]
    page = doc[0]
    page.clean_contents()
    xref = page.get_contents()[0]
    cont = bytearray(page.read_contents())
    pattern = b" Td\n<"
    length = 100    
    most_frequent, frequency = most_frequent_substring_with_pattern(cont, pattern, length)

    tasks = [remove_watermark_from_page(page, most_frequent) for page in doc]
    await asyncio.gather(*tasks)

    doc.ez_save(output_file)

async def remove_watermark_by_xref(input_file, output_file):
    doc = fitz.open(input_file)
    def get_target_xref_at_first_page(doc):
        xref_width_pattern = 2360
        xref_height_pattern = 1640
        target_xref = None
        image_list = doc[0].get_image_info(xrefs=True)
        for image_info in image_list:
            if image_info['width'] == xref_width_pattern and image_info['height'] == xref_height_pattern:
                target_xref =image_info['xref']
        return target_xref

    target_xref = get_target_xref_at_first_page(doc)
    if not target_xref:
        return
    else:
        doc[0].delete_image(target_xref)
        doc.ez_save(output_file)

async def remove_watermark(input_file, output_file):
    doc = fitz.open(input_file)
    if 'Version' in doc.metadata['producer']:
        await remove_watermark_by_xref(input_file, output_file)
    else:
        await remove_watermark_by_common_str(input_file, output_file)