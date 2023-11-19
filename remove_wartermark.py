import fitz

def remove_watermark(input_file, output_file):
    doc = fitz.open(input_file)
    def most_frequent_substring(byte_array, length):
        count = {}
        for i in range(len(byte_array) - length + 1):
            substring = bytes(byte_array[i:i + length])
            if substring in count:
                count[substring] += 1
            else:
                count[substring] = 1
        most_frequent = max(count, key=count.get)
        return most_frequent, count[most_frequent]
    page = doc[0]
    page.clean_contents()
    xref = page.get_contents()[0]
    cont = bytearray(page.read_contents())
    byte_length = 100
    most_frequent, frequency = most_frequent_substring(cont, byte_length)
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