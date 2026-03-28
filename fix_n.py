import glob
for f in glob.glob("*.py"):
    with open(f, "r", encoding="utf-8") as file:
        text = file.read()
    if "\
" in text:
        text = text.replace("\
", "
")
        with open(f, "w", encoding="utf-8") as file:
            file.write(text.strip() + "
")
