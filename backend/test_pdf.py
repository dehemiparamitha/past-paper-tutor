import pymupdf

document = pymupdf.open("data/past_papers/2015.pdf")

for page_number, page in enumerate(document, start=1):

    text = page.get_text().strip()
    images = page.get_images(full=True)

    print(
        f"Page {page_number}: "
        f"text={len(text)} chars, "
        f"images={len(images)}"
    )

document.close()