# 📁 Data Directory - Organized by File Format

This directory is organized by **file format** for easy file management.

## 📂 Folder Structure

```
data/raw/
├── PDF/          ← 📄 Paste all PDF files here (resumes, documents, etc.)
├── TXT/          ← 📝 Paste all .txt text files here
├── MD/           ← 📝 Paste all .md markdown files here
├── DOCX/         ← 📄 Paste all .docx Word documents here
├── CSV/          ← 📊 Paste all .csv files here
└── JSON/         ← 📋 Paste all .json files here
```

## 🎯 Quick Start

### For Your 4 Resume PDFs:
1. **Go to `PDF/` folder**
2. **Paste your 4 resume PDFs** there
3. **That's it!** The ingestion script will find them automatically

### For Other Files:
- **PDF files** → `PDF/` folder
- **Text files** → `TXT/` folder
- **Markdown files** → `MD/` folder
- **Word documents** → `DOCX/` folder
- **CSV files** → `CSV/` folder
- **JSON files** → `JSON/` folder

## 📋 Supported Formats

| Format | Extension | Folder | Status |
|--------|-----------|--------|--------|
| PDF | `.pdf` | `PDF/` | ✅ Fully Supported |
| Text | `.txt` | `TXT/` | ✅ Fully Supported |
| Markdown | `.md` | `MD/` | ✅ Fully Supported |
| Word | `.docx` | `DOCX/` | ✅ Supported |
| CSV | `.csv` | `CSV/` | ✅ Supported |
| JSON | `.json` | `JSON/` | ✅ Supported |

## 🚀 After Adding Documents

Run the ingestion script:

```bash
cd ../../backend
source venv/bin/activate
python scripts/ingest.py
```

The script will:
- ✅ Find all documents in all format folders
- ✅ Process them intelligently
- ✅ Upload to Pinecone

## 💡 Tips

- **Organize by format**: Just paste files into the matching folder
- **Use descriptive filenames**: `resume-software-engineer-2024.pdf`
- **Start with PDFs**: Add your 4 resume PDFs to `PDF/` folder first
- **Add more later**: You can always add more documents

## 📍 Example Structure

After adding files:

```
PDF/
├── resume-1.pdf
├── resume-2.pdf
├── resume-3.pdf
└── resume-4.pdf

TXT/
├── company-policy.txt
└── faq.txt

MD/
└── documentation.md
```

---

**Just paste your files into the matching format folder and run ingestion!** 🚀
