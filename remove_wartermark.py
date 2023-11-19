import fitz, re

def remove_watermark(input_file, output_file):
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
    for page in doc:
        page.clean_contents()
        xref = page.get_contents()[0]
        cont = bytearray(page.read_contents())
        while True:
            i1 = cont.find(most_frequent)
            if i1 < 0: break
            cont[i1 : i1+len(most_frequent)] = b""
        doc.update_stream(xref, cont)
    doc.ez_save(output_file)