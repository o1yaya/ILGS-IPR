from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


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
    return parent


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


def make_formula_paragraph(formula_items, number):
    p = el("w:p")
    ppr = el("w:pPr")
    jc = el("w:jc")
    jc.set(qn("w:val"), "center")
    ppr.append(jc)

    tabs = el("w:tabs")
    tab = el("w:tab")
    tab.set(qn("w:val"), "right")
    # Approximate right text edge for the current Chinese A4 template.
    tab.set(qn("w:pos"), str(int(6.25 * 1440)))
    tabs.append(tab)
    ppr.append(tabs)

    spacing = el("w:spacing")
    spacing.set(qn("w:before"), "60")
    spacing.set(qn("w:after"), "60")
    ppr.append(spacing)
    p.append(ppr)

    math = el("m:oMath")
    add_seq(math, formula_items)
    p.append(math)
    p.append(wr_tab())
    p.append(wr_text(f"({number})"))
    return p


FORMULAS = [
    ([sub("Y", "t"), "(x)=i,    ", sub("w", "t"), "(x)∈[0,1]"], 1),
    ([sub("S", "i,c"), "=", sub("∑", "k"), sub("α", "i,k"), sub("p", "i,k,c")], 2),
    (
        [
            sub("q", "i"),
            "=",
            frac([sub("max", "c"), sub("S", "i,c")], [sub("∑", "c"), sub("S", "i,c"), "+ε"]),
        ],
        3,
    ),
    (
        [
            sub("m", "i"),
            "=",
            frac([sub("S", "i,c₁"), "−", sub("S", "i,c₂")], [sub("∑", "c"), sub("S", "i,c"), "+ε"]),
        ],
        4,
    ),
    (
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
    (
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
]

FORMULA_GROUPS = [
    [FORMULAS[0]],
    [FORMULAS[1], FORMULAS[2], FORMULAS[3]],
    [FORMULAS[4]],
    [FORMULAS[5]],
]


def has_math_table(tbl):
    return bool(tbl.xpath(".//m:oMath | .//m:oMathPara"))


def main():
    doc = Document(str(DOCX_PATH))
    body = doc.element.body
    formula_tables = [child for child in body if child.tag == qn("w:tbl") and has_math_table(child)]
    if len(formula_tables) != len(FORMULA_GROUPS):
        raise RuntimeError(f"Expected {len(FORMULA_GROUPS)} formula tables, found {len(formula_tables)}")

    for tbl, group in zip(formula_tables, FORMULA_GROUPS):
        for items, number in group:
            p = make_formula_paragraph(items, number)
            tbl.addprevious(p)
        body.remove(tbl)

    doc.save(str(DOCX_PATH))
    print(f"saved {DOCX_PATH}; replaced {len(formula_tables)} formula tables")


if __name__ == "__main__":
    main()
