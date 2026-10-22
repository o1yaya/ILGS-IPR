from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt


DOCX_PATH = Path(r"D:\wlxy\ILGS-IPR.docx")


def el(tag):
    return OxmlElement(tag)


def mr(text):
    r = el("m:r")
    t = el("m:t")
    t.text = text
    r.append(t)
    return r


def wr_text(text):
    r = el("w:r")
    rpr = el("w:rPr")
    rfonts = el("w:rFonts")
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")
    rfonts.set(qn("w:eastAsia"), "宋体")
    rpr.append(rfonts)
    sz = el("w:sz")
    sz.set(qn("w:val"), "21")
    rpr.append(sz)
    r.append(rpr)
    t = el("w:t")
    t.text = text
    r.append(t)
    return r


def wr_tab():
    r = el("w:r")
    r.append(el("w:tab"))
    return r


def add_seq(parent, items):
    for item in items:
        if isinstance(item, str):
            parent.append(mr(item))
        else:
            parent.append(item)


def container(tag, items):
    node = el(tag)
    add_seq(node, items)
    return node


def sub(base, subscript):
    node = el("m:sSub")
    node.append(container("m:e", [base]))
    node.append(container("m:sub", [subscript]))
    return node


def sup(base_items, superscript):
    node = el("m:sSup")
    node.append(container("m:e", base_items if isinstance(base_items, list) else [base_items]))
    node.append(container("m:sup", [superscript]))
    return node


def subsup(base, subscript, superscript):
    node = el("m:sSubSup")
    node.append(container("m:e", [base]))
    node.append(container("m:sub", [subscript]))
    node.append(container("m:sup", [superscript]))
    return node


def frac(num_items, den_items):
    node = el("m:f")
    node.append(container("m:num", num_items))
    node.append(container("m:den", den_items))
    return node


def clear_paragraph(paragraph):
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)


def set_formula(paragraph, formula_items, number):
    clear_paragraph(paragraph)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = None
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(3)

    ppr = paragraph._p.get_or_add_pPr()
    tabs = ppr.find(qn("w:tabs"))
    if tabs is not None:
        ppr.remove(tabs)
    tabs = el("w:tabs")
    tab = el("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:pos"), str(int(6.25 * 1440)))
    tabs.append(tab)
    ppr.append(tabs)

    math = el("m:oMath")
    add_seq(math, formula_items)
    paragraph._p.append(math)
    paragraph._p.append(wr_tab())
    paragraph._p.append(wr_text(f"({number})"))


FORMULAS = {
    33: ([sub("Y", "t"), "(x)=i,    ", sub("w", "t"), "(x)∈[0,1]"], 1),
    37: ([sub("S", "i,c"), "=", sub("∑", "k"), sub("α", "i,k"), sub("p", "i,k,c")], 2),
    38: (
        [
            sub("q", "i"),
            "=",
            frac([sub("max", "c"), sub("S", "i,c")], [sub("∑", "c"), sub("S", "i,c"), "+ε"]),
        ],
        3,
    ),
    39: (
        [
            sub("m", "i"),
            "=",
            frac([sub("S", "i,c₁"), "−", sub("S", "i,c₂")], [sub("∑", "c"), sub("S", "i,c"), "+ε"]),
        ],
        4,
    ),
    44: (
        [
            subsup("v", "i", "t"),
            "=",
            subsup("A", "i", "t"),
            "·exp(",
            frac(
                ["−", sup(["(", subsup("A", "i", "t"), "−", sub("A", "i,med"), ")"], "2")],
                ["2", sup("σ", "2")],
            ),
            ")",
        ],
        5,
    ),
    51: (
        [
            sub("L′", "id"),
            "=",
            frac(
                [
                    sub("∑", "x"),
                    sub("w", "t"),
                    "(x)CE(",
                    sub("p", "t"),
                    "(x),",
                    sub("Y", "t"),
                    "(x))",
                ],
                [sub("∑", "x"), sub("w", "t"), "(x)+ε"],
            ),
        ],
        6,
    ),
}


def main():
    doc = Document(str(DOCX_PATH))
    for idx, (items, number) in FORMULAS.items():
        set_formula(doc.paragraphs[idx], items, number)
    doc.save(str(DOCX_PATH))
    print(f"saved {DOCX_PATH}")


if __name__ == "__main__":
    main()
