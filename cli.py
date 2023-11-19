import sys
from remove_wartermark import remove_watermark

def main():
    input_file = sys.argv[1]
    output_file = input_file.replace(".pdf", "_no_watermark.pdf")
    remove_watermark(input_file, output_file)

if __name__ == "__main__":
    main()
