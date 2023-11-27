import sys
import asyncio
from remove_watermark import remove_watermark

async def async_main():
    input_file = sys.argv[1]
    output_file = input_file.replace(".pdf", "_no_watermark.pdf")
    await remove_watermark(input_file, output_file)

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
