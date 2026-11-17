"""Manuscrito IMRaD. Las cifras salen de escenario.pkl y no se reescriben a mano."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from escenario import DISPLAY, MODELS, figures

HERE = Path(__file__).resolve().parent
PKL = HERE / "escenario.pkl"
OUT = HERE / "Tamizaje_TB_SP-02_mejorada.docx"

ORDER: list[str] = []
LIB = {
    "who2025": "World Health Organization. Global tuberculosis report 2025. Geneva: World Health Organization; 2025. ISBN 978-92-4-011692-4.",
    "who2021": "World Health Organization. WHO consolidated guidelines on tuberculosis. Module 2: screening – systematic screening for tuberculosis disease. Geneva: World Health Organization; 2021.",
    "tpp2014": "World Health Organization. High-priority target product profiles for new tuberculosis diagnostics: report of a consensus meeting. Geneva: World Health Organization; 2014.",
    "qin2021": "Qin ZZ, Ahmed S, Sarker MS, Paul K, Adel ASS, Naheyan T, et al. Tuberculosis detection from chest x-rays for triaging in a high tuberculosis-burden setting: an evaluation of five artificial intelligence algorithms. Lancet Digit Health. 2021;3(9):e543-e554. doi:10.1016/S2589-7500(21)00116-3.",
    "codlin2021": "Codlin AJ, Dao TP, Vo LNQ, Forse RJ, Truong VV, Dang HM, et al. Independent evaluation of 12 artificial intelligence solutions for the detection of tuberculosis. Sci Rep. 2021;11:23895. doi:10.1038/s41598-021-03265-0.",
    "harris2019": "Harris M, Qi A, Jeagal L, et al. A systematic review of the diagnostic accuracy of artificial intelligence-based computer programs to analyze chest x-rays for pulmonary tuberculosis. PLoS One. 2019;14(9):e0221339. doi:10.1371/journal.pone.0221339.",
    "lakhani2017": "Lakhani P, Sundaram B. Deep learning at chest radiography: automated classification of pulmonary tuberculosis by using convolutional neural networks. Radiology. 2017;284(2):574-582. doi:10.1148/radiol.2017162326.",
    "murphy2020": "Murphy K, Habib SS, Zaidi SMA, et al. Computer aided detection of tuberculosis on chest radiographs: an evaluation of the CAD4TB v6 system. Sci Rep. 2020;10:5492.",
    "pasa2019": "Pasa F, Golkov V, Pfeiffer F, Cremers D, Pfeiffer D. Efficient deep network architectures for fast chest X-ray tuberculosis screening and visualization. Sci Rep. 2019;9:6268.",
    "jaeger2014": "Jaeger S, Candemir S, Antani S, Wáng YXJ, Lu PX, Thoma G. Two public chest X-ray datasets for computer-aided screening of pulmonary tuberculosis. Quant Imaging Med Surg. 2014;4(6):475-477.",
    "roberts2021": "Roberts M, Driggs D, Thorpe M, Gilbey J, Yeung M, Ursprung S, et al. Common pitfalls and recommendations for using machine learning to detect and prognosticate for COVID-19 using chest radiographs and CT scans. Nat Mach Intell. 2021;3:199-217. doi:10.1038/s42256-021-00307-0.",
    "handbook2021": "World Health Organization. WHO operational handbook on tuberculosis. Module 2: screening – systematic screening for tuberculosis disease. Geneva: World Health Organization; 2021.",
    "stard2015": "Bossuyt PM, Reitsma JB, Bruns DE, Gatsonis CA, Glasziou PP, Irwig L, et al. STARD 2015: an updated list of essential items for reporting diagnostic accuracy studies. BMJ. 2015;351:h5527. doi:10.1136/bmj.h5527.",
    "tripod2024": "Collins GS, Moons KGM, Dhiman P, Riley RD, Beam AL, Van Calster B, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. BMJ. 2024;385:e078378. doi:10.1136/bmj-2023-078378.",
    "claim2020": "Mongan J, Moy L, Kahn CE Jr. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): a guide for authors and reviewers. Radiol Artif Intell. 2020;2(2):e200029. doi:10.1148/ryai.2020200029.",
    "decide2022": "Vasey B, Nagendran M, Campbell B, Clifton DA, Collins GS, Denaxas S, et al. Reporting guideline for the early-stage clinical evaluation of decision support systems driven by artificial intelligence: DECIDE-AI. Nat Med. 2022;28:924-933. doi:10.1038/s41591-022-01772-9.",
    "huang2017": "Huang G, Liu Z, Van Der Maaten L, Weinberger KQ. Densely connected convolutional networks. In: Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition; 2017; Honolulu, HI. p. 4700-4708. doi:10.1109/CVPR.2017.243.",
    "chexnext2018": "Rajpurkar P, Irvin J, Ball RL, Zhu K, Yang B, Mehta H, et al. Deep learning for chest radiograph diagnosis: a retrospective comparison of the CheXNeXt algorithm to practicing radiologists. PLoS Med. 2018;15(11):e1002686. doi:10.1371/journal.pmed.1002686.",
    "imagenet2015": "Russakovsky O, Deng J, Su H, Krause J, Satheesh S, Ma S, et al. ImageNet large scale visual recognition challenge. Int J Comput Vis. 2015;115(3):211-252. doi:10.1007/s11263-015-0816-y.",
    "tan2019": "Tan M, Le QV. EfficientNet: rethinking model scaling for convolutional neural networks. In: Proceedings of the 36th International Conference on Machine Learning; 2019. Proc Mach Learn Res. 97:6105-6114.",
    "dosovitskiy2021": "Dosovitskiy A, Beyer L, Kolesnikov A, Weissenborn D, Zhai X, Unterthiner T, et al. An image is worth 16x16 words: transformers for image recognition at scale. In: International Conference on Learning Representations; 2021.",
    "vaswani2017": "Vaswani A, Shazeer N, Parmar N, Uszkoreit J, Jones L, Gomez AN, et al. Attention is all you need. In: Advances in Neural Information Processing Systems 30; 2017. p. 5998-6008.",
    "hochreiter1997": "Hochreiter S, Schmidhuber J. Long short-term memory. Neural Comput. 1997;9(8):1735-1780. doi:10.1162/neco.1997.9.8.1735.",
    "akiba2019": "Akiba T, Sano S, Yanase T, Ohta T, Koyama M. Optuna: a next-generation hyperparameter optimization framework. In: Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining; 2019; Anchorage, AK. p. 2623-2631. doi:10.1145/3292500.3330701.",
    "loshchilov2019": "Loshchilov I, Hutter F. Decoupled weight decay regularization. In: International Conference on Learning Representations; 2019.",
    "youden1950": "Youden WJ. Index for rating diagnostic tests. Cancer. 1950;3(1):32-35.",
    "platt1999": "Platt JC. Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In: Smola AJ, Bartlett P, Schölkopf B, Schuurmans D, editors. Advances in large margin classifiers. Cambridge (MA): MIT Press; 1999. p. 61-74.",
    "guo2017": "Guo C, Pleiss G, Sun Y, Weinberger KQ. On calibration of modern neural networks. In: Proceedings of the 34th International Conference on Machine Learning; 2017. Proc Mach Learn Res. 70:1321-1330.",
    "vancalster2019": "Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW. Calibration: the Achilles heel of predictive analytics. BMC Med. 2019;17:230. doi:10.1186/s12916-019-1466-7.",
    "delong1988": "DeLong ER, DeLong DM, Clarke-Pearson DL. Comparing the areas under two or more correlated receiver operating characteristic curves: a nonparametric approach. Biometrics. 1988;44(3):837-845.",
    "sun2014": "Sun X, Xu W. Fast implementation of DeLong’s algorithm for comparing the areas under correlated receiver operating characteristic curves. IEEE Signal Process Lett. 2014;21(11):1389-1393.",
    "mcnemar1947": "McNemar Q. Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika. 1947;12(2):153-157.",
    "holm1979": "Holm S. A simple sequentially rejective multiple test procedure. Scand J Stat. 1979;6(2):65-70.",
    "friedman1937": "Friedman M. The use of ranks to avoid the assumption of normality implicit in the analysis of variance. J Am Stat Assoc. 1937;32(200):675-701.",
    "wilcoxon1945": "Wilcoxon F. Individual comparisons by ranking methods. Biometrics Bulletin. 1945;1(6):80-83.",
    "efron1993": "Efron B, Tibshirani RJ. An introduction to the bootstrap. New York: Chapman and Hall; 1993.",
    "vickers2006": "Vickers AJ, Elkin EB. Decision curve analysis: a novel method for evaluating prediction models. Med Decis Making. 2006;26(6):565-574. doi:10.1177/0272989X06295361.",
    "selvaraju2017": "Selvaraju RR, Cogswell M, Das A, Vedantam R, Parikh D, Batra D. Grad-CAM: visual explanations from deep networks via gradient-based localization. In: Proceedings of the IEEE International Conference on Computer Vision; 2017; Venice. p. 618-626. doi:10.1109/ICCV.2017.74.",
    "johnson2019": "Johnson AEW, Pollard TJ, Berkowitz SJ, et al. MIMIC-CXR, a de-identified publicly available database of chest radiographs with free-text reports. Sci Data. 2019;6:317. doi:10.1038/s41597-019-0322-0.",
    "nguyen2022": "Nguyen HQ, Lam K, Le LT, et al. VinDr-CXR: an open dataset of chest X-rays with radiologist’s annotations. Sci Data. 2022;9:429. doi:10.1038/s41597-022-01498-w.",
    "geirhos2020": "Geirhos R, Jacobsen JH, Michaelis C, Zemel R, Brendel W, Bethge M, et al. Shortcut learning in deep neural networks. Nat Mach Intell. 2020;2:665-673. doi:10.1038/s42256-020-00257-z.",
    "oakden2020": "Oakden-Rayner L, Dunnmon J, Carneiro G, Ré C. Hidden stratification causes clinically meaningful failures in machine learning for medical imaging. In: Proceedings of the ACM Conference on Health, Inference, and Learning; 2020. p. 151-159.",
    "ghassemi2021": "Ghassemi M, Oakden-Rayner L, Beam AL. The false hope of current approaches to explainable artificial intelligence in health care. Lancet Digit Health. 2021;3(11):e745-e750. doi:10.1016/S2589-7500(21)00208-9.",
    "wiens2019": "Wiens J, Saria S, Sendak M, Ghassemi M, Liu VX, Doshi-Velez F, et al. Do no harm: a roadmap for responsible machine learning for health care. Nat Med. 2019;25(9):1337-1340. doi:10.1038/s41591-019-0548-6.",
    "sendak2020": "Sendak MP, Gao M, Brajer N, Balu S. Presenting machine learning model information to clinical end users with model facts labels. NPJ Digit Med. 2020;3:41. doi:10.1038/s41746-020-0253-3.",
    "consort2020": "Liu X, Cruz Rivera S, Moher D, Calvert MJ, Denniston AK. Reporting guidelines for clinical trial reports for interventions involving artificial intelligence: the CONSORT-AI extension. Nat Med. 2020;26(9):1364-1374. doi:10.1038/s41591-020-1034-x.",
}


def cite(*keys: str) -> str:
    nums = []
    for key in keys:
        if key not in LIB:
            raise KeyError(key)
        if key not in ORDER:
            ORDER.append(key)
        nums.append(str(ORDER.index(key) + 1))
    return "[" + ", ".join(nums) + "]"


def num(x, d=3) -> str:
    return f"{float(x):.{d}f}".replace(".", ",")


def pct(x, d=1) -> str:
    return num(100 * float(x), d)


def entero(x) -> str:
    return f"{int(round(float(x))):,}".replace(",", " ")


def pv(p) -> str:
    p = float(p)
    if p < 0.001:
        return "<0,001"
    return num(p, 3)


def ic(lo, hi, d=3) -> str:
    return f"{num(lo, d)} a {num(hi, d)}"


def shade(cell, fill: str) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_run_font(run, size=12, bold=False, italic=False, color=None, font="Times New Roman") -> None:
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_p(doc, text, size=12, bold=False, italic=False, align="justify", before=0, after=8, center=False):
    p = doc.add_paragraph()
    p.alignment = {
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
    }[align if not center else "center"]
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    set_run_font(r, size=size, bold=bold, italic=italic)
    return p


def add_rich(doc, parts, align="justify", before=0, after=8, size=12):
    p = doc.add_paragraph()
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.15
    for text, bold, italic in parts:
        r = p.add_run(text)
        set_run_font(r, size=size, bold=bold, italic=italic)
    return p


def h1(doc, text):
    p = doc.add_paragraph(text, style="Heading 1")
    return p


def h2(doc, text):
    return doc.add_paragraph(text, style="Heading 2")


def caption(doc, text):
    return add_p(doc, text, size=10, italic=False, align="left", before=8, after=4)


def add_figure(doc, filename, legend, width_cm):
    doc.add_picture(str(HERE / "figuras" / filename), width=Cm(width_cm))
    return add_p(doc, legend, size=10, align="justify", before=4, after=10)


def note(doc, text):
    return add_p(doc, text, size=9, italic=True, align="left", before=0, after=10)


def cell_text(cell, text, size=8, bold=False, color=None, center=True):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    set_run_font(r, size=size, bold=bold, color=color)


def set_widths(table, widths_cm):
    table.autofit = False
    table.allow_autofit = False
    total = int(sum(widths_cm) / 2.54 * 1440)
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for child in list(grid):
            grid.remove(child)
    else:
        grid = OxmlElement("w:tblGrid")
        tbl_pr.addnext(grid)
    for w in widths_cm:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(int(w / 2.54 * 1440)))
        grid.append(gc)
    for row in table.rows:
        for i, w in enumerate(widths_cm):
            row.cells[i].width = Cm(w)
            tc = row.cells[i]._tc
            tc_pr = tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(int(w / 2.54 * 1440)))
            tc_w.set(qn("w:type"), "dxa")


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        shade(cell, "1F4E79")
        cell_text(cell, h, size=8, bold=True, color="FFFFFF")
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = table.rows[r_i + 1].cells[c_i]
            if r_i % 2 == 1:
                shade(cell, "F4F7FB")
            cell_text(cell, val, size=8, bold=(c_i == 0), center=(c_i != 0))
    set_widths(table, widths)
    hdr = table.rows[0]._tr.get_or_add_trPr()
    mark = OxmlElement("w:tblHeader")
    hdr.append(mark)
    return table


def page_field(paragraph):
    run = paragraph.add_run()
    set_run_font(run, size=9, color="444444")
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)


def operating_ci(y, p, thr, n_boot=2000, seed=20261104):
    """Intervalo percentil de sensibilidad y especificidad con el umbral ya cerrado."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=float)
    pred = (np.asarray(p) >= thr).astype(float)
    n = len(y)
    sens = np.empty(n_boot)
    spec = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        yy = y[idx]
        pr = pred[idx]
        pos = yy == 1
        neg = ~pos
        sens[i] = pr[pos].mean() if pos.any() else np.nan
        spec[i] = (1.0 - pr[neg]).mean() if neg.any() else np.nan
    return (
        float(np.nanquantile(sens, 0.025)),
        float(np.nanquantile(sens, 0.975)),
        float(np.nanquantile(spec, 0.025)),
        float(np.nanquantile(spec, 0.975)),
    )


def net_benefit(y, p, pt):
    pred = p >= pt
    tp = np.sum(pred & (y == 1))
    fp = np.sum(pred & (y == 0))
    n = len(y)
    return float(tp / n - fp / n * (pt / (1 - pt)))


def build():
    ORDER.clear()
    with PKL.open("rb") as fh:
        R = pickle.load(fh)
    figures(R)
    prim = R["primary"]
    pname = DISPLAY[prim]
    st = R["stats"]
    pe = st[prim]["ext"]
    pi = st[prim]["test"]
    pv_ = st[prim]["val"]
    p95 = st[prim]["ext95"]
    d = st["densenet121"]
    coh = R["cohort"]
    qc = R["qc"]
    rev = R["review"]
    ver = R["versions"]
    y = R["frames"][prim]["ext"]["y"].to_numpy()
    pp = R["frames"][prim]["ext"]["p"].to_numpy()
    pdn = R["frames"]["densenet121"]["ext"]["p"].to_numpy()
    thr = R["thresholds"][prim]["t90"]
    sens_lo, sens_hi, spec_lo, spec_hi = operating_ci(y, pp, thr, seed=20261104)
    thr_d = R["thresholds"]["densenet121"]["t90"]
    yd = R["frames"]["densenet121"]["ext"]["y"].to_numpy()
    ds_lo, ds_hi, dp_lo, dp_hi = operating_ci(yd, pdn, thr_d, seed=20261105)
    nb10 = net_benefit(y, pp, 0.10)
    nb20 = net_benefit(y, pp, 0.20)
    nb_thr = net_benefit(y, pp, thr)
    nb_dn = net_benefit(y, pdn, thr)
    prev = float(y.mean())
    nb_all = prev - (1 - prev) * (thr / (1 - thr))
    comp = {c["name"]: c for c in R["comparisons"]}
    fr = R["friedman"]
    excluded = qc["technical"] + qc["format"] + qc["resolution"] + qc["blank"] + qc["duplicate"]

    doc = Document()
    for style_name, size, before, after in (
        ("Normal", 12, 0, 8),
        ("Heading 1", 14, 16, 8),
        ("Heading 2", 12, 12, 6),
    ):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        style.font.bold = style_name != "Normal"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = 1.15
        if style_name == "Normal":
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)
    section.header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = section.header.paragraphs[0].add_run("SP-02  ·  versión mejorada")
    set_run_font(hr, size=8, italic=True, color="666666")
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = fp.add_run("Página ")
    set_run_font(frun, size=9, color="444444")
    page_field(fp)
    doc.core_properties.title = (
        "Tamizaje de tuberculosis pulmonar en radiografías de tórax con un sistema de apoyo a la decisión"
    )
    doc.core_properties.subject = "Versión mejorada"
    doc.core_properties.category = "Manuscrito científico"
    doc.core_properties.language = "es-ES"

    add_p(doc, "Versión mejorada", size=11, bold=True, align="left", before=12, after=2)
    add_p(
        doc,
        "Tamizaje de tuberculosis pulmonar en radiografías de tórax con un sistema de apoyo a la decisión: comparación de cinco arquitecturas y transporte del umbral a dos instituciones",
        size=16,
        bold=True,
        align="left",
        before=2,
        after=4,
    )
    add_p(
        doc,
        "Título abreviado: Umbral transportado en el tamizaje radiográfico de tuberculosis",
        size=11,
        italic=True,
        align="left",
        after=8,
    )
    add_p(doc, "[Nombre del autor 1], [Nombre del autor 2]", size=12, align="left", after=2)
    add_p(doc, "[Unidad o facultad], [Universidad]", size=11, italic=True, align="left", after=2)
    add_p(doc, "Correspondencia: [correo institucional]", size=11, align="left", after=8)
    add_p(
        doc,
        "Tipo de artículo: investigación original. Estructura preparada para una revista de salud digital indexada en Scopus o Web of Science, con reporte orientado por STARD 2015, TRIPOD+AI, CLAIM y DECIDE-AI.",
        size=10,
        italic=True,
        align="left",
    )

    h1(doc, "Resumen")
    add_rich(doc, [
        ("Contexto. ", True, False),
        ("La radiografía de tórax sigue siendo la puerta del tamizaje de la tuberculosis donde faltan lectores. El vacío no es la ausencia de algoritmos: la evidencia compara sobre todo productos cerrados, y casi no mide si una arquitectura abierta, con el umbral congelado antes de ver otro hospital, sostiene el perfil de triaje dentro de un flujo que puede negarse a puntuar una imagen.", False, False),
    ])
    add_rich(doc, [
        ("Objetivo. ", True, False),
        ("Evaluar la discriminación, la calibración y el punto de operación de cinco arquitecturas para el tamizaje de tuberculosis pulmonar, con el umbral fijado solo en validación, y describir el despliegue del sistema SP-02.", False, False),
    ])
    add_rich(doc, [
        ("Métodos. ", True, False),
        (f"Escenario retrospectivo de tres instituciones y una imagen por persona. De {entero(qc['received'])} radiografías recibidas, {entero(qc['evaluable'])} fueron evaluables. El sitio D (n = {entero(coh['D']['n'])}) se partió por persona en entrenamiento, validación y prueba interna. E1 y E2 permanecieron fuera del ajuste. El modelo desplegable fue el de mayor AUC de validación. El umbral fue el más alto que alcanzaba una sensibilidad de al menos 90 % en validación. La calibración fue un escalado de Platt ajustado solo en esa partición. La referencia del escenario es microbiológica.", False, False),
    ])
    add_rich(doc, [
        ("Resultados. ", True, False),
        (f"El modelo seleccionado fue {pname}. En la cohorte externa (n = {entero(pe['n'])}; {entero(pe['n_pos'])} con tuberculosis) el AUC fue {num(pe['auc_roc'])} (IC 95 % {ic(pe['auc_lo'], pe['auc_hi'])}). Con el umbral transportado, la sensibilidad fue {pct(pe['sensitivity'])} % y la especificidad {pct(pe['specificity'])} %. Ninguna de las cinco redes cumplió a la vez el perfil de triaje de 90 % de sensibilidad y 70 % de especificidad. La diferencia de AUC frente a DenseNet121 no fue significativa; sí lo fue la diferencia de aciertos en el punto de operación. La especificidad cayó al {pct(next(s['specificity'] for s in R['subgroups'] if s['label'].startswith('Tuberculosis')))} % en tuberculosis previa y el AUC de las personas de 60 años o más fue {num(next(s['auc'] for s in R['subgroups'] if '60 años o más' in s['label']))}.", False, False),
    ])
    add_rich(doc, [
        ("Conclusión. ", True, False),
        ("Elegir la red por el AUC de validación no basta para sostener el perfil de triaje al cambiar de institución. El aporte trasladable, en este escenario, es el sistema que encierra el umbral, aparta la imagen no evaluable, deja la etiqueta final en un revisor y registra la decisión en una bitácora que no se puede reescribir.", False, False),
    ])
    add_p(doc, "Palabras clave: tuberculosis pulmonar; radiografía torácica; detección asistida por computadora; validación externa; calibración de probabilidades; apoyo a la decisión clínica.", size=11)

    h1(doc, "Abstract")
    add_rich(doc, [
        ("Background. ", True, False),
        ("Chest radiography remains the entry point for tuberculosis triage where readers are scarce. The gap is not a lack of algorithms. Most head-to-head evidence concerns closed commercial products, and few studies ask whether an open architecture, with its threshold frozen before any external site is seen, can hold a triage profile inside a workflow allowed to refuse an image.", False, False),
    ])
    add_rich(doc, [
        ("Objective. ", True, False),
        ("To compare discrimination, calibration and the transported operating point of five deep-learning families, and to specify the deployment of the SP-02 decision-support system.", False, False),
    ])
    add_rich(doc, [
        ("Methods. ", True, False),
        (f"Retrospective three-site study, one radiograph per person. Of {entero(qc['received'])} submissions, {entero(qc['evaluable'])} were evaluable. Site D was split by person. Two external sites never entered tuning, calibration or threshold selection. The deployable model maximised validation AUC. The threshold was the highest score reaching 90% sensitivity on validation. Probabilities were Platt-scaled on validation logits only.", False, False),
    ])
    add_rich(doc, [
        ("Results. ", True, False),
        (f"{pname} was selected. External AUC was {num(pe['auc_roc'])} (95% CI {ic(pe['auc_lo'], pe['auc_hi'])}), with sensitivity {pct(pe['sensitivity'])}% and specificity {pct(pe['specificity'])}% at the locked threshold. No model met the 90%/70% triage target. The AUC difference versus DenseNet121 was not significant; classification disagreements at the operating point were. Specificity fell to {pct(next(s['specificity'] for s in R['subgroups'] if s['label'].startswith('Tuberculosis')))}% after prior tuberculosis, and AUC was {num(next(s['auc'] for s in R['subgroups'] if '60 años o más' in s['label']))} at age 60 or older.", False, False),
    ])
    add_rich(doc, [
        ("Conclusion. ", True, False),
        ("Validation AUC did not secure a transportable triage profile. The durable piece is a workflow that freezes the threshold, withholds non-evaluable images, keeps a human final label and writes an append-only audit.", False, False),
    ])
    add_p(doc, "Keywords: pulmonary tuberculosis; chest radiography; computer-aided detection; external validation; probability calibration; clinical decision support.", size=11)
    add_p(
        doc,
        "Abreviaturas: AUC, área bajo la curva característica operativa del receptor; ECE, error de calibración esperado; IC, intervalo de confianza; RIC, recorrido intercuartílico; VPN, valor predictivo negativo; VPP, valor predictivo positivo.",
        size=10,
        italic=True,
        align="left",
    )
    h1(doc, "Puntos clave")
    add_p(
        doc,
        f"El modelo de mayor AUC en validación, {pname}, alcanzó un AUC externo de {num(pe['auc_roc'])} (IC 95 % {ic(pe['auc_lo'], pe['auc_hi'])}). Esa ventaja frente a DenseNet121 no fue significativa.",
        align="left",
    )
    add_p(
        doc,
        f"Con el umbral transportado, la sensibilidad fue {pct(pe['sensitivity'])} % y la especificidad {pct(pe['specificity'])} %. Ninguna de las cinco redes cumplió a la vez el perfil de triaje de 90 % y 70 %.",
        align="left",
    )
    add_p(
        doc,
        "En el mismo corte, el híbrido clasificó bien a más personas que DenseNet121, a costa de dejar pasar más tuberculosis. El AUC y el punto de operación no eligen el mismo motor.",
        align="left",
    )
    add_p(
        doc,
        "La discriminación cayó desde los 60 años y dejó de ser útil en tuberculosis previa. Apartar la imagen no evaluable, congelar el umbral y conservar una bitácora que no se reescribe es el aporte que no depende de ganar la curva.",
        align="left",
    )

    h1(doc, "1. Introducción")
    h2(doc, "1.1. La brecha entre la carga de enfermedad y la lectura de la radiografía")
    add_p(
        doc,
        "En 2024 enfermaron de tuberculosis unos 10,7 millones de personas (intervalo de incertidumbre 9,9 a 11,5 millones) y murieron 1,23 millones. La tasa fue de 131 por 100 000 habitantes. La reducción desde 2015 llega a 12 %, lejos del hito de 50 % fijado para 2025 por la estrategia Fin a la TB. "
        f"La Región de las Américas concentró cerca de 3,3 % de los casos incidentes {cite('who2025')}. "
        "Esas cifras no se mueven al ritmo de las metas porque el diagnóstico llega tarde: la radiografía de tórax es barata y está disponible, pero su lectura exige personal que muchos servicios no tienen en el momento en que la persona se presenta.",
    )
    add_p(
        doc,
        f"La Organización Mundial de la Salud admite el uso de detección asistida por computadora para el triaje y el tamizaje de la tuberculosis en personas de 15 años o más, como alternativa a la lectura humana, siempre que el programa elija el producto y el umbral con evidencia local {cite('who2021')}. "
        f"El perfil de producto de un test de triaje pide, como meta, al menos 90 % de sensibilidad y 70 % de especificidad frente a una referencia microbiológica {cite('tpp2014')}. "
        "Ese par de números es una restricción de programa, no un adorno del área bajo la curva. Un modelo puede ordenar bien a las personas y, aun así, en el umbral que preserva la sensibilidad, confirmar a tantas que el laboratorio no gana capacidad.",
    )
    h2(doc, "1.2. Lo que ya se comparó y lo que sigue abierto")
    add_p(
        doc,
        f"La comparación independiente de cinco productos comerciales en 23 954 radiografías de Dhaka, con Xpert MTB/RIF como referencia, situó el AUC entre 0,849 y 0,908. Solo qXR y CAD4TB cumplieron el perfil de triaje en el punto de 90 % de sensibilidad, con especificidades de 74,3 % y 72,9 %. Todos perdieron rendimiento por encima de los 60 años y en tuberculosis previa {cite('qin2021')}. "
        f"Otra evaluación, de doce productos en Vietnam, encontró que seis se acercaban a un lector experto y que el equipo de radiología modificaba el resultado de algunos {cite('codlin2021')}. "
        f"Las revisiones sistemáticas anteriores habían descrito una heterogeneidad grande y un riesgo alto de sesgo cuando el conjunto de prueba era pequeño o se parecía demasiado al de entrenamiento {cite('harris2019')}.",
    )
    add_p(
        doc,
        f"En el extremo optimista, un conjunto de redes convolucionales alcanzó un AUC de 0,99 en 150 radiografías de prueba {cite('lakhani2017')}. "
        f"Ese número no se ha reproducido en archivos grandes con referencia microbiológica. CAD4TB versión 6 y redes compactas diseñadas para tamizaje mostraron que la velocidad y la exactitud pueden convivir, pero también que el punto de corte hay que volver a situarlo {cite('murphy2020', 'pasa2019')}. "
        f"Los archivos públicos de Shenzhen y Montgomery permitieron los primeros comparadores abiertos y, a la vez, enseñaron lo frágil que es un resultado cuando la misma persona o la misma imagen cruza la partición {cite('jaeger2014', 'roberts2021')}. "
        f"MIMIC-CXR y VinDr-CXR ampliaron la escala, con etiquetas de informe o de radiólogo que no equivalen a un cultivo o a una prueba molecular {cite('johnson2019', 'nguyen2022')}.",
    )
    h2(doc, "1.3. La brecha que este estudio recorre")
    add_p(
        doc,
        f"Aunque la exactitud del software comercial se ha medido en evaluaciones ciegas, sigue sin resolverse cómo se comparan, bajo un protocolo único y sin fuga por persona, cinco familias abiertas —red densa, red eficiente, transformador visual compacto, híbrido convolucional-transformador e híbrido con memoria bidireccional— cuando dos instituciones se reservan antes de tocar el umbral. "
        f"Tampoco queda resuelto cómo se despliega el modelo elegido: quién carga la imagen, quién acepta o corrige la etiqueta, qué se hace con la radiografía ilegible y cómo se impide reescribir la bitácora. La limitación importa porque un AUC aislado no dice qué fracción de placas no debe puntuarse, ni qué probabilidad se le enseña al revisor, ni quién responde si el umbral viaja mal {cite('handbook2021')}. "
        "Este trabajo recorre esa brecha con el sistema SP-02 y con un escenario de análisis que obedece las mismas cerraduras que el código: partición por persona, institución externa fuera del ajuste, calibración y umbral solo en validación.",
    )
    h2(doc, "1.4. Objetivo, hipótesis y aportes")
    add_p(
        doc,
        "El objetivo fue estimar la discriminación y el punto de operación de las cinco arquitecturas en dos instituciones no usadas para el desarrollo, y describir si el modelo de mayor AUC de validación sostiene el perfil de triaje al transportar el umbral. "
        "La hipótesis de superioridad fue que el híbrido EfficientNet-BiLSTM con atención superaría a DenseNet121 en el AUC externo. DenseNet121 se fijó de antemano como comparador de referencia porque es la identidad que la interfaz clínica muestra mientras el motor no se reemplaza. "
        "La hipótesis de programa fue que el umbral anclado a 90 % de sensibilidad en validación mantendría sensibilidad y especificidad por encima del perfil de triaje en la cohorte externa. Ambas hipótesis se contrastan en los resultados; no se dan por cumplidas en el diseño.",
    )
    add_p(
        doc,
        "Los aportes que el lector puede verificar son cuatro. Primero, la comparación de las cinco familias con una sola regla de selección, una sola calibración y un umbral que no se reabre. Segundo, la separación explícita entre imagen no evaluable y clasificación binaria, de modo que el AUC no se infla con placas que el sistema se negó a leer. Tercero, el despliegue con cuatro roles humanos, una cuenta de servicio, seis flujos de orquestación y un canal de consulta que no recibe imágenes ni seudónimos. Cuarto, el informe conjunto de lo que no alcanzó significación: la diferencia de AUC frente a las redes convolucionales grandes y las comparaciones por pares de la validación cruzada.",
    )

    h1(doc, "2. Métodos")
    h2(doc, "2.1. Diseño y normas de reporte")
    add_p(
        doc,
        f"El diseño es un estudio retrospectivo de exactitud diagnóstica con validación externa geográfica, más una evaluación temprana del flujo de apoyo a la decisión. El reporte de exactitud sigue STARD 2015 {cite('stard2015')}. "
        f"El modelo de predicción se informa con TRIPOD+AI {cite('tripod2024')} y el componente de imagen con CLAIM {cite('claim2020')}. "
        f"La lectura humana, los tiempos y la anulación de la etiqueta se informan con el espíritu de DECIDE-AI, como evaluación temprana y no como ensayo de resultados clínicos {cite('decide2022')}. "
        "No hubo un desenlace de tratamiento iniciado ni de mortalidad. El sistema no es un dispositivo de diagnóstico y la interfaz lo dice en el pie de cada pantalla.",
    )
    add_p(
        doc,
        "El plan de análisis es el del programa SP-02: partición por persona, sitio externo cerrado al ajuste y las mismas pruebas. La arquitectura de la figura 1 describe el programa escrito.",
    )
    h2(doc, "2.2. El sistema y su despliegue")
    add_p(
        doc,
        "SP-02 es el sistema de apoyo a la decisión en el que se encaja el modelo. No sustituye al lector: separa quién carga, quién decide y quién puede revisar la huella. Cuatro roles humanos ven pantallas distintas. El operador abre el caso y la imagen. El revisor acepta o corrige la etiqueta. El auditor lee la bitácora. El administrador gestiona usuarios y exportaciones. Una cuenta de servicio solo orquesta; no revisa ni administra. Cada caso lleva un seudónimo, no el nombre de la persona. El motor en pantalla se identifica por nombre y versión. En el programa de referencia esa identidad es DenseNet121 (densenet121-tb-v1), porque el motor se puede cambiar. En este escenario la regla de selección señaló otra red; el contrato de la pantalla no cambia.",
    )
    add_p(
        doc,
        "Antes de cualquier puntaje, la imagen tiene que ser legible. Solo se aceptan PNG y JPEG cuyo tipo declarado coincida con el archivo. Se rechazan los archivos vacíos, los mayores de 15 MB, los que no se pueden abrir, los de lado menor a 256 píxeles y los de gris casi uniforme. El resumen SHA-256 marca duplicados. Esas placas quedan como no evaluables o como fallo técnico y no entran al AUC: el estado «no evaluable» no es una tercera clase de la red. Si la imagen pasa, la salida es una probabilidad, el umbral ya cerrado y una de dos etiquetas, tuberculosis probable o sin hallazgos compatibles. La etiqueta final del revisor queda atada a esa inferencia, de modo que siempre se sabe qué número estaba en pantalla.",
    )
    add_p(
        doc,
        "La bitácora solo admite altas. La base impide corregirla, borrarla o vaciarla, y cada exportación queda asentada. Seis flujos llaman a la misma API y no reescriben los permisos: importan lotes, revisan la calidad, lanzan la inferencia pendiente, avisan por conteos sin identificadores, envían el reporte semanal y resumen el día. El rendimiento del modelo solo se calcula si hay etiquetas de referencia; si no las hay, el flujo deja constancia de que no calculó nada. Un canal de preguntas ve únicamente agregados del tablero. Si interviene un modelo de lenguaje, no recibe imágenes ni seudónimos, y debe callar cuando el texto de apoyo no cubre la pregunta. La figura 1 muestra ese reparto. Las versiones de bibliotecas quedan en el apartado de reproducibilidad, no en el argumento clínico.",
    )
    add_figure(
        doc,
        "fig1_arquitectura.png",
        "Figura 1. Despliegue del sistema SP-02. Los cuatro roles humanos entran por la aplicación web. La API conserva los permisos, el estado del caso y la bitácora. El motor es intercambiable. La orquestación y el canal de consultas no ven la imagen ni el seudónimo.",
        16.2,
    )
    h2(doc, "2.3. Población, referencia y partición")
    add_p(
        doc,
        "El escenario representa un archivo retrospectivo de tres instituciones, con una proyección posteroanterior por persona adulta. La referencia es microbiológica, del tipo Xpert o cultivo, obtenida en una ventana cercana a la placa. No se usó el informe radiológico como verdad. Esa elección importa: una secuela de tuberculosis antigua puede parecer enfermedad activa y, con una referencia microbiológica negativa, cuenta como falso positivo del modelo. Es el contraste correcto para triaje, y es más duro que etiquetar «anormal» cualquier opacidad.",
    )
    add_p(
        doc,
        f"El sitio D aportó {entero(coh['D']['n'])} personas y se partió con GroupShuffleSplit por identificador de persona: 60 % entrenamiento (n = {entero(coh['train']['n'])}), 20 % validación (n = {entero(coh['val']['n'])}) y 20 % prueba interna (n = {entero(coh['test']['n'])}). "
        f"E1 (n = {entero(coh['E1']['n'])}) y E2 (n = {entero(coh['E2']['n'])}) se retiraron antes de la partición. El código comprueba que ningún identificador de persona y ningún resumen de imagen se compartan entre particiones, y aborta si una institución externa reaparece en el desarrollo. "
        "Los archivos Shenzhen y Montgomery sirvieron en el programa como contrato de formato y como prueba de esa cerradura, no como la cohorte de este escenario. MIMIC-CXR y VinDr-CXR no se mezclaron: exigen acceso credencialado y sus etiquetas no son la referencia microbiológica usada aquí.",
    )
    add_p(
        doc,
        "No se calculó un tamaño de muestra a priori. La precisión queda expresada por la amplitud del intervalo. La figura 2 muestra el flujo, incluidas las exclusiones de calidad, que no forman parte del AUC.",
    )
    add_figure(
        doc,
        "fig2_flujo.png",
        "Figura 2. Flujo del escenario. Las exclusiones de formato, resolución, imagen uniforme, duplicado y fallo técnico salen antes del modelo. El umbral y el escalado de Platt se estiman en la validación del sitio D y no se reabren con la prueba interna ni con E1 o E2.",
        14.2,
    )
    h2(doc, "2.4. Arquitecturas")
    add_p(
        doc,
        f"Las cinco redes producen un solo logit y se entrenan con pérdida logística binaria, ponderada por la razón de negativos sobre positivos. La imagen entra en gris, reescalada a 224 píxeles y llevada al intervalo [−1, 1]. DenseNet121 sustituye la capa final por una salida lineal; el mapa de activación se toma del cuarto bloque denso {cite('huang2017')}. "
        f"Se eligió como referencia por su uso extendido en radiografía de tórax {cite('chexnext2018')}. "
        f"EfficientNet-B3 usa la escala compuesta de profundidad, ancho y resolución, con abandono 0,3 en el clasificador {cite('tan2019')}. "
        f"El transformador visual de este programa no es ViT-Base: es una red compacta de parche 16, dimensión 192, seis bloques y tres cabezas, con token de clase {cite('dosovitskiy2021')}. "
        f"El CNN-Transformer aplica tres convoluciones de zancada 2 hasta 128 canales y un codificador de dos capas y cuatro cabezas, con la atención descrita para secuencias {cite('vaswani2017')}. "
        f"El híbrido toma los mapas de EfficientNet-B3 (1 536 canales), los proyecta, los recorre con una LSTM bidireccional de estado 64 y agrega las posiciones con atención aditiva {cite('hochreiter1997')}. "
        f"DenseNet121, EfficientNet-B3 y el tallo del híbrido pueden inicializarse con ImageNet {cite('imagenet2015')}. El ViT compacto y el CNN-Transformer nacen de pesos aleatorios: el código no trae un punto de control público para esas dos redes. Esa asimetría es parte de la comparación y se discute como tal.",
    )
    h2(doc, "2.5. Ajuste, calibración y umbral")
    add_p(
        doc,
        f"El protocolo de búsqueda es Optuna con el estimador de Parzen en árbol y poda por mediana, 30 ensayos y hasta 15 épocas, optimizando el AUC de validación {cite('akiba2019')}. "
        f"El optimizador es AdamW {cite('loshchilov2019')}. El espacio incluye la tasa de aprendizaje, el decaimiento de peso, el abandono y el tamaño de lote. Se conserva el punto de control de mejor AUC de validación. "
        f"El umbral prespecificado es el más alto de la curva ROC de validación que alcanza una sensibilidad de al menos 0,90. Entre los umbrales que cumplen esa sensibilidad, esa regla es la de mayor especificidad; es la variante de programa del índice de Youden cuando el costo de un falso negativo está acotado por el perfil de triaje {cite('youden1950', 'tpp2014')}. "
        f"Un análisis de sensibilidad repitió el cierre con una meta de 0,95. Las probabilidades salen de un escalado de Platt ajustado solo a los logits de validación {cite('platt1999')}. "
        "Ni el umbral ni los coeficientes de Platt se reestiman en la prueba interna ni en E1 o E2.",
    )
    h2(doc, "2.6. Explicación visual")
    add_p(
        doc,
        f"Para las redes con un mapa convolucional, incluida la raíz del híbrido, el programa calcula Grad-CAM sobre el logit de la clase positiva {cite('selvaraju2017')}. "
        "Para el ViT compacto calcula el despliegue de la atención del token de clase. El mapa se guarda junto a la inferencia y se muestra al revisor. No hubo en este escenario una verdad de terreno de localización, de modo que el mapa no entra en el desenlace de exactitud. Sirve como pieza del flujo, y el tiempo de lectura con mapa y sin mapa se midió aparte.",
    )
    h2(doc, "2.7. Análisis estadístico")
    add_p(
        doc,
        "El desenlace primario fue el AUC-ROC en la cohorte externa agrupada. El modelo desplegable se eligió antes de mirar ese desenlace: mayor AUC en la validación del sitio D y, en empate, menor error de calibración esperado. "
        f"Los intervalos de 95 % del AUC, y los de sensibilidad y especificidad en el umbral ya cerrado, son percentiles de 2 000 remuestreos de personas {cite('efron1993')}. "
        f"Como hay una imagen por persona, remuestrear personas y remuestrear filas coinciden. La comparación pareada de AUC usó la prueba de DeLong, en la forma rápida de Sun y Xu {cite('delong1988', 'sun2014')}. "
        f"La concordancia de clasificaciones en el umbral cerrado usó la prueba exacta de McNemar {cite('mcnemar1947')}. "
        f"Las cuatro comparaciones del modelo seleccionado contra el resto se ajustaron con Holm, por separado para DeLong y para McNemar {cite('holm1979')}. "
        "El nivel de significación fue 0,05, bilateral.",
    )
    add_p(
        doc,
        f"Se informaron además el AUC de precisión-recuperación, la F1, el coeficiente de Matthews, el Brier y el error de calibración esperado en diez intervalos, antes y después de Platt {cite('guo2017', 'vancalster2019')}. "
        f"La utilidad se resumió con la curva de decisión: beneficio neto frente a confirmar a todas las personas y frente a no confirmar a nadie {cite('vickers2006')}. "
        f"En el sitio D se calcularon cinco bloques GroupKFold por persona y se aplicó Friedman; los pares, Wilcoxon con Holm {cite('friedman1937', 'wilcoxon1945')}. "
        "Esos bloques miden si el orden de las redes ya puntuadas se sostiene entre grupos de personas. No son un reentrenamiento de cada pliegue: el programa todavía no automatiza ese ciclo, y se informa como análisis de estabilidad, no como varianza de reajuste.",
    )
    h2(doc, "2.8. Revisión humana y operación")
    add_p(
        doc,
        f"Sobre las {entero(rev['n'])} personas de la cohorte externa, dos revisores registraron una etiqueta a ciegas de la referencia microbiológica, con la probabilidad y la imagen a la vista. Se calculó la concordancia de cada uno con el modelo y el kappa de Cohen entre ellos. "
        f"En un cruce de {entero(rev['n_time'])} casos, el mismo revisor cronometró la lectura con mapa y sin mapa. Los tiempos se compararon con Wilcoxon pareado. "
        "La latencia del motor y el tiempo de extremo a extremo del caso se plantean como medición del API en el servidor de inferencia, no como una corrida de los flujos de n8n en producción: esos flujos están exportados, inactivos, y su estructura se validó sin una instancia en vivo.",
    )
    h2(doc, "2.9. Ética, privacidad y versiones")
    add_p(
        doc,
        "El diseño retrospectivo sobre imágenes ya obtenidas requiere dictamen de comité y, en su caso, exención de consentimiento con seudonimización. El seudónimo no viaja al canal de lenguaje. Las imágenes permanecen en el almacén de la institución, detrás de una interfaz que puede cambiarse por un depósito de objetos sin tocar la regla clínica. "
        f"El escenario se calculó con Python {ver.get('python')}, NumPy {ver.get('numpy')}, pandas {ver.get('pandas')}, scikit-learn {ver.get('sklearn')}, SciPy {ver.get('scipy')} y PyTorch {ver.get('torch')}. "
        "La API declara FastAPI 0.115 o superior, SQLAlchemy 2 y PostgreSQL 18 como objetivo de despliegue. El cliente declara React 18.3 y Vite 6.",
    )

    h1(doc, "3. Resultados")
    h2(doc, "3.1. Cohorte y calidad de la imagen")
    add_p(
        doc,
        f"Llegaron {entero(qc['received'])} radiografías. Se excluyeron {entero(excluded)} ({pct(excluded / qc['received'])} %): "
        f"{entero(qc['technical'])} por fallo técnico, {entero(qc['format'])} por formato ilegible o tipo no admitido, "
        f"{entero(qc['resolution'])} por resolución por debajo de 256 píxeles, {entero(qc['blank'])} por imagen uniforme y {entero(qc['duplicate'])} por duplicado del resumen SHA-256. "
        f"Quedaron {entero(qc['evaluable'])} personas con una imagen evaluable. La prevalencia de tuberculosis fue {pct(coh['D']['prev'])} % en el sitio D, {pct(coh['E1']['prev'])} % en E1 y {pct(coh['E2']['prev'])} % en E2. "
        "La edad mediana rondó los 55 años, con un recorrido intercuartílico ancho, propio de un archivo hospitalario y no de un tamizaje comunitario de adultos jóvenes. La proporción de mujeres fue menor en E2. VIH y tuberculosis previa se situaron cerca de una de cada diez personas, con más antecedentes en E2 (tabla 1).",
    )
    caption(doc, "Tabla 1. Características de las personas con imagen evaluable, por institución y por partición del sitio D.")
    rows1 = []
    for key in ("D", "train", "val", "test", "E1", "E2", "ext"):
        c = coh[key]
        rows1.append([
            c["label"],
            entero(c["n"]),
            f"{entero(c['n_pos'])} ({pct(c['prev'])})",
            f"{num(c['age'], 0)} ({num(c['age_q1'], 0)} a {num(c['age_q3'], 0)})",
            pct(c["female"]),
            pct(c["hiv"]),
            pct(c["prior"]),
        ])
    add_table(
        doc,
        ["Grupo", "n", "TB, n (%)", "Edad, mediana (RIC)", "Mujeres, %", "VIH, %", "TB previa, %"],
        rows1,
        [3.5, 1.5, 2.3, 3.2, 2.1, 1.8, 2.6],
    )
    note(doc, "TB: tuberculosis según la referencia microbiológica del escenario. RIC: recorrido intercuartílico. La partición de entrenamiento, validación y prueba interna suma el sitio D. E1 y E2 no entraron en esa partición. Edad en años.")

    h2(doc, "3.2. Discriminación y calibración")
    add_p(
        doc,
        f"En validación, el AUC más alto fue el de {pname} ({num(pv_['auc_roc'])}). Siguieron DenseNet121 ({num(st['densenet121']['val']['auc_roc'])}), EfficientNet-B3 ({num(st['efficientnet_b3']['val']['auc_roc'])}), el ViT compacto ({num(st['vit']['val']['auc_roc'])}) y el CNN-Transformer ({num(st['cnn_transformer']['val']['auc_roc'])}). "
        f"La regla de selección, aplicada antes de abrir la cohorte externa, dejó como modelo del escenario a {pname}.",
    )
    add_p(
        doc,
        f"En la prueba interna el AUC de ese modelo fue {num(pi['auc_roc'])} (IC 95 % {ic(pi['auc_lo'], pi['auc_hi'])}). "
        f"En la cohorte externa bajó a {num(pe['auc_roc'])} (IC 95 % {ic(pe['auc_lo'], pe['auc_hi'])}), una caída de {num(pi['auc_roc'] - pe['auc_roc'])} puntos. "
        f"El AUC de precisión-recuperación externo fue {num(pe['auc_pr'])} y el Brier {num(pe['brier'])}. "
        "La figura 3 muestra que las dos redes convolucionales grandes y el híbrido viajan juntas, y que el ViT compacto y el CNN-Transformer quedan por debajo en casi todo el recorrido. El punto marcado es el umbral cerrado en validación, no el mejor punto de la curva externa.",
    )
    add_figure(
        doc,
        "fig3_roc.png",
        "Figura 3. Curvas ROC en la cohorte externa agrupada (n = 1 360). El punto marca el umbral de EfficientNet-BiLSTM-atención fijado en la validación del sitio D para una sensibilidad de al menos 90 %. La leyenda informa el AUC.",
        14.6,
    )
    add_p(
        doc,
        f"El escalado de Platt, estimado en validación (pendiente {num(R['calibration'][prim]['a'], 2)}, intercepto {num(R['calibration'][prim]['b'], 2)}), bajó el error de calibración esperado del modelo seleccionado de {num(pe['ece_raw'])} a {num(pe['ece'])} en la cohorte externa. "
        f"El efecto fue del mismo sentido en las cinco redes (tabla 2). La figura 4 muestra la curva cruda del modelo seleccionado por debajo de la diagonal, es decir, probabilidades crudas más altas que la frecuencia observada, y las curvas ya escaladas cerca de la identidad. "
        f"Quedó calibración residual por sede: el error fue {num(st[prim]['e1']['ece'])} en E1 y {num(st[prim]['e2']['ece'])} en E2. Transportar los coeficientes no sustituye un ajuste local.",
    )
    caption(doc, "Tabla 2. Discriminación y calibración. El AUC interno es el de la prueba del sitio D. El AUC externo agrupa E1 y E2. El error de calibración esperado (ECE) compara la probabilidad media con la frecuencia observada en diez intervalos.")
    rows2 = []
    for name in MODELS:
        s_i, s_e = st[name]["test"], st[name]["ext"]
        rows2.append([
            DISPLAY[name],
            f"{num(s_i['auc_roc'])} ({ic(s_i['auc_lo'], s_i['auc_hi'])})",
            f"{num(s_e['auc_roc'])} ({ic(s_e['auc_lo'], s_e['auc_hi'])})",
            num(s_e["auc_pr"]),
            num(s_e["brier"]),
            num(s_e["ece_raw"]),
            num(s_e["ece"]),
        ])
    add_table(
        doc,
        ["Modelo", "AUC interno (IC 95 %)", "AUC externo (IC 95 %)", "AUC-PR", "Brier", "ECE crudo", "ECE Platt"],
        rows2,
        [3.6, 3.3, 3.3, 1.6, 1.5, 1.8, 1.9],
    )
    note(doc, "IC: intervalo de confianza por remuestreo de personas. AUC-PR: área bajo la curva de precisión y recuperación. ECE: error de calibración esperado. El modelo de la primera fila es el seleccionado por el AUC de validación.")
    add_figure(
        doc,
        "fig4_calibracion.png",
        "Figura 4. Calibración en la cohorte externa. La línea punteada es el modelo seleccionado antes del escalado de Platt. Las líneas continuas son las cinco redes después de aplicar, sin reajuste, los coeficientes estimados en validación.",
        14.6,
    )

    h2(doc, "3.3. Punto de operación y perfil de triaje")
    add_p(
        doc,
        f"El umbral de {pname} quedó en {num(thr)}. En validación la sensibilidad fue {pct(pv_['sensitivity'])} % y la especificidad {pct(pv_['specificity'])} %: la meta de sensibilidad se cumplió y la de especificidad del perfil de triaje, no. "
        f"Transportado a la cohorte externa, la sensibilidad bajó a {pct(pe['sensitivity'])} % (IC 95 % {pct(sens_lo)} a {pct(sens_hi)}; {entero(pe['tp'])} verdaderos positivos y {entero(pe['fn'])} falsos negativos) y la especificidad fue {pct(pe['specificity'])} % (IC 95 % {pct(spec_lo)} a {pct(spec_hi)}; {entero(pe['fp'])} falsos positivos y {entero(pe['tn'])} verdaderos negativos). "
        f"El valor predictivo positivo fue {pct(pe['ppv'])} % y el negativo {pct(pe['npv'])} %. "
        f"Ninguna de las cinco redes cumplió a la vez 90 % de sensibilidad y 70 % de especificidad (tabla 3). La hipótesis de programa no se sostiene en este escenario.",
    )
    add_p(
        doc,
        f"DenseNet121, en su propio umbral de validación ({num(thr_d)}), mantuvo en la cohorte externa una sensibilidad de {pct(d['ext']['sensitivity'])} % (IC 95 % {pct(ds_lo)} a {pct(ds_hi)}) con una especificidad de {pct(d['ext']['specificity'])} % (IC 95 % {pct(dp_lo)} a {pct(dp_hi)}). "
        f"El híbrido, elegido por AUC, perdió la meta de sensibilidad al viajar y ganó especificidad respecto de esa referencia ({pct(pe['specificity'])} % frente a {pct(d['ext']['specificity'])} %). "
        f"No hay una dominancia uniforme: depende de si el programa teme más un caso no confirmado o una prueba molecular de más. "
        f"Con la meta alternativa de 95 % de sensibilidad en validación, el umbral del híbrido bajó a {num(R['thresholds'][prim]['t95'])} y, fuera, la sensibilidad fue {pct(p95['sensitivity'])} % con especificidad de {pct(p95['specificity'])} %. El perfil tampoco se cumplió.",
    )
    add_p(
        doc,
        f"La fracción de personas a las que no se les pediría la prueba molecular, porque el modelo dijo «sin hallazgos compatibles», fue {pct(pe['xpert_avoided'])} % con el híbrido y {pct(d['ext']['xpert_avoided'])} % con DenseNet121. "
        f"Esa fracción incluye a los falsos negativos: {entero(pe['fn'])} de {entero(pe['n_pos'])} personas con tuberculosis no serían confirmadas si nadie revisara el caso. "
        f"El número de pruebas por cada tuberculosis detectada fue {num(pe['nnt'], 2)} con el híbrido, frente a {num(1 / pe['prevalence'], 2)} si se confirmara a toda la cohorte. "
        f"Por sede, la discriminación casi no cambió (AUC {num(st[prim]['e1']['auc_roc'])} en E1 y {num(st[prim]['e2']['auc_roc'])} en E2), pero el valor predictivo positivo pasó de {pct(st[prim]['e1']['ppv'])} % en E1 a {pct(st[prim]['e2']['ppv'])} % en E2, con la prevalencia. La tabla 3 desagrega el punto de operación.",
    )
    caption(doc, "Tabla 3. Punto de operación en la cohorte externa con el umbral cerrado en validación (sensibilidad objetivo de al menos 90 %). El perfil de triaje exige, a la vez, sensibilidad de al menos 90 % y especificidad de al menos 70 %.")
    rows3 = []
    for name in MODELS:
        s = st[name]["ext"]
        rows3.append([
            DISPLAY[name],
            num(R["thresholds"][name]["t90"]),
            pct(s["sensitivity"]),
            pct(s["specificity"]),
            pct(s["ppv"]),
            pct(s["npv"]),
            pct(s["xpert_avoided"]),
            "Sí" if s["tpp"] else "No",
        ])
    for site, label in (("e1", "E1, modelo seleccionado"), ("e2", "E2, modelo seleccionado")):
        s = st[prim][site]
        rows3.append([
            label,
            num(thr),
            pct(s["sensitivity"]),
            pct(s["specificity"]),
            pct(s["ppv"]),
            pct(s["npv"]),
            pct(s["xpert_avoided"]),
            "Sí" if s["tpp"] else "No",
        ])
    add_table(
        doc,
        ["Modelo o sede", "Umbral", "Sens.", "Esp.", "VPP", "VPN", "Sin prueba, %", "Perfil"],
        rows3,
        [4.2, 1.6, 1.5, 1.5, 1.5, 1.5, 2.4, 1.8],
    )
    note(doc, "Sens.: sensibilidad. Esp.: especificidad. VPP y VPN: valores predictivos positivo y negativo. «Sin prueba» es el porcentaje de personas etiquetadas como sin hallazgos compatibles. Porcentajes, salvo el umbral. El perfil se evalúa sobre la fila, no sobre el AUC.")

    h2(doc, "3.4. Comparaciones pareadas")
    add_p(
        doc,
        f"La diferencia de AUC externo entre {pname} y DenseNet121 fue {num(comp['densenet121']['delong']['auc_a'] - comp['densenet121']['delong']['auc_b'])} "
        f"(z = {num(comp['densenet121']['delong']['z'], 2)}; p = {pv(comp['densenet121']['delong']['p'])}; p de Holm = {pv(comp['densenet121']['delong_holm'])}). "
        f"Tampoco fue significativa frente a EfficientNet-B3 (p de Holm = {pv(comp['efficientnet_b3']['delong_holm'])}) ni frente al CNN-Transformer (p de Holm = {pv(comp['cnn_transformer']['delong_holm'])}). "
        f"Sí lo fue frente al ViT compacto (Δ = {num(comp['vit']['delong']['auc_a'] - comp['vit']['delong']['auc_b'])}; p de Holm = {pv(comp['vit']['delong_holm'])}). "
        "La hipótesis de superioridad en AUC frente a la referencia densa no se confirma.",
    )
    add_p(
        doc,
        f"En el punto de operación la lectura cambia. McNemar contó {entero(comp['densenet121']['mcnemar']['a_only_correct'])} personas clasificadas bien solo por el híbrido y {entero(comp['densenet121']['mcnemar']['b_only_correct'])} bien solo por DenseNet121 "
        f"(p de Holm = {pv(comp['densenet121']['mcnemar_holm'])}). "
        f"El mismo patrón, con más discordancia a favor del híbrido, apareció frente a EfficientNet-B3, el CNN-Transformer y el ViT (tabla 4). "
        "Un AUC parecido puede esconder un umbral que se equivoca en personas distintas. Aquí el híbrido acertó más a la clasificación cerrada, sobre todo porque produjo menos falsos positivos, a costa de la sensibilidad que DenseNet121 sí preservó.",
    )
    add_p(
        doc,
        f"Friedman, sobre cinco bloques de personas del sitio D, rechazó que las cinco redes tuvieran el mismo AUC (chi cuadrado = {num(fr['friedman_chi2'], 2)}; gl = 4; p = {pv(fr['friedman_p'])}). "
        "Ningún Wilcoxon por pares sobrevivió a Holm: con cinco bloques el p mínimo de un signo constante es 0,0625 y el ajuste de diez pares lo lleva a 0,625. "
        "El orden existe en conjunto y no se puede atribuir, con esta potencia, a un par concreto. No se interpreta como evidencia de reentrenamiento.",
    )
    caption(doc, "Tabla 4. Comparaciones pareadas en la cohorte externa. DeLong contrasta AUC. McNemar contrasta aciertos en el umbral de cada modelo. Holm se aplica dentro de cada familia de cuatro pruebas.")
    rows4 = []
    for name in ("densenet121", "efficientnet_b3", "cnn_transformer", "vit"):
        c = comp[name]
        rows4.append([
            DISPLAY[name],
            num(c["delong"]["auc_a"] - c["delong"]["auc_b"]),
            num(c["delong"]["z"], 2),
            pv(c["delong"]["p"]),
            pv(c["delong_holm"]),
            entero(c["mcnemar"]["a_only_correct"]),
            entero(c["mcnemar"]["b_only_correct"]),
            pv(c["mcnemar"]["p"]),
            pv(c["mcnemar_holm"]),
        ])
    add_table(
        doc,
        ["Comparador", "Δ AUC", "z", "p", "Holm", "Solo híbrido", "Solo comparador", "p McN.", "Holm"],
        rows4,
        [3.4, 1.5, 1.3, 1.5, 1.5, 1.8, 2.2, 1.6, 1.5],
    )
    note(doc, "Δ AUC: AUC del modelo seleccionado menos AUC del comparador. «Solo híbrido» y «solo comparador» son conteos de personas en las que un modelo acierta y el otro no. McN.: McNemar exacto. p de Holm en la columna contigua a cada familia.")

    h2(doc, "3.5. Subgrupos")
    add_p(
        doc,
        f"La figura 5 y la tabla 5 concentran el hallazgo de transporte que el AUC global esconde. Entre las personas de 60 años o más (n = {entero(next(s['n'] for s in R['subgroups'] if '60 años o más' in s['label']))}) el AUC fue "
        f"{num(next(s['auc'] for s in R['subgroups'] if '60 años o más' in s['label']))} "
        f"(IC 95 % {ic(next(s['lo'] for s in R['subgroups'] if '60 años o más' in s['label']), next(s['hi'] for s in R['subgroups'] if '60 años o más' in s['label']))}), "
        f"con sensibilidad {pct(next(s['sensitivity'] for s in R['subgroups'] if '60 años o más' in s['label']))} %. "
        f"Por debajo de esa edad el AUC fue {num(next(s['auc'] for s in R['subgroups'] if 'menor de 60' in s['label']))}. "
        "Mujeres y hombres no se separaron de forma material.",
    )
    prior = next(s for s in R["subgroups"] if s["label"].startswith("Tuberculosis previa"))
    sin = next(s for s in R["subgroups"] if s["label"].startswith("Sin tuberculosis"))
    hiv = next(s for s in R["subgroups"] if s["label"] == "VIH")
    add_p(
        doc,
        f"En tuberculosis previa (n = {entero(prior['n'])}, de ellas {entero(prior['n_pos'])} con enfermedad activa) el AUC fue {num(prior['auc'])} (IC 95 % {ic(prior['lo'], prior['hi'])}) y la especificidad {pct(prior['specificity'])} %. "
        f"El intervalo incluye 0,50: no se afirma que el modelo ordenara peor que el azar, sí que dejó de discriminar de forma útil y que marcó como probable a casi todas las secuelas microbiológicamente negativas. "
        f"Sin ese antecedente, el AUC fue {num(sin['auc'])} (IC 95 % {ic(sin['lo'], sin['hi'])}) y la especificidad {pct(sin['specificity'])} %. "
        f"En VIH (n = {entero(hiv['n'])}, {entero(hiv['n_pos'])} con tuberculosis) el AUC fue {num(hiv['auc'])} (IC 95 % {ic(hiv['lo'], hiv['hi'])}). El intervalo es ancho y la prevalencia del subgrupo es alta; no se lee como prueba de equidad.",
    )
    add_figure(
        doc,
        "fig5_subgrupos.png",
        "Figura 5. AUC del modelo seleccionado en la cohorte externa, por sede y por subgrupo. La línea discontinua gris es el AUC de toda la cohorte externa. La línea punteada clara marca 0,50. Las barras son intervalos de 95 % por remuestreo de personas.",
        15.2,
    )
    caption(doc, "Tabla 5. Subgrupos del modelo seleccionado con el umbral transportado. El denominador es la cohorte externa, salvo las filas de sede.")
    rows5 = []
    for s in R["subgroups"]:
        rows5.append([
            s["label"],
            entero(s["n"]),
            entero(s["n_pos"]),
            f"{num(s['auc'])} ({ic(s['lo'], s['hi'])})",
            pct(s["sensitivity"]),
            pct(s["specificity"]),
        ])
    add_table(
        doc,
        ["Subgrupo", "n", "TB", "AUC (IC 95 %)", "Sens., %", "Esp., %"],
        rows5,
        [4.4, 1.6, 1.4, 4.6, 2.5, 2.5],
    )
    note(doc, "TB: personas con referencia positiva. Sens. y Esp. usan el umbral de validación del modelo seleccionado, sin reajuste dentro del subgrupo.")

    h2(doc, "3.6. Utilidad, revisión y operación")
    add_p(
        doc,
        f"En la curva de decisión, {pname} y DenseNet121 quedaron por encima de la estrategia de confirmar a toda la cohorte desde probabilidades umbral bajas, y muy cerca uno del otro (figura 6). "
        f"En el umbral cerrado ({num(thr)}), el beneficio neto del híbrido fue {num(nb_thr)} frente a {num(nb_dn)} de DenseNet121 y {num(nb_all)} de confirmar a todas las personas. "
        f"A una probabilidad umbral de 0,10 el beneficio neto del híbrido fue {num(nb10)}; a 0,20 fue {num(nb20)}. "
        "La ganancia frente a «confirmar a todas» es real en este escenario y la ganancia frente a la red densa es pequeña. No se traduce, por sí sola, en menos muertes: ese desenlace no se midió.",
    )
    add_figure(
        doc,
        "fig6_decision.png",
        "Figura 6. Curva de decisión en la cohorte externa. La línea vertical punteada es el umbral de validación del modelo seleccionado. Confirmar a todas las personas pierde beneficio neto cuando la probabilidad umbral sube, porque cada falso positivo pesa más.",
        14.6,
    )
    add_p(
        doc,
        f"El revisor 1 coincidió con el modelo en {pct(rev['agree1'])} % de los casos y el revisor 2 en {pct(rev['agree2'])} %. El kappa entre revisores fue {num(rev['kappa'])}. "
        f"De {entero(rev['fn'])} falsos negativos del modelo, al menos un revisor rescató {entero(rev['fn_rescued'])}; {entero(rev['both_wrong_fn'])} siguieron sin marcarse. "
        f"De {entero(rev['fp'])} falsos positivos, al menos un revisor corrigió {entero(rev['fp_corrected'])}. "
        f"La sensibilidad del revisor 1 frente a la referencia, calculada después y no durante la lectura, fue {pct(rev['rev1_sens'])} % y la especificidad {pct(rev['rev1_spec'])} %. "
        f"La lectura con mapa tardó una mediana de {num(rev['med_with'], 0)} segundos (RIC {num(rev['q1_with'], 0)} a {num(rev['q3_with'], 0)}) y sin mapa {num(rev['med_without'], 0)} segundos (RIC {num(rev['q1_without'], 0)} a {num(rev['q3_without'], 0)}); p {pv(rev['time_p'])}. "
        "El ahorro de tiempo no se presenta como un efecto clínico: son 80 pares de un solo revisor.",
    )
    caption(doc, "Tabla 6. Calidad de entrada, revisión humana y operación del flujo. Los conteos de calidad usan el denominador de radiografías recibidas. La revisión usa la cohorte externa.")
    rows6 = [
        ["Calidad", "Recibidas / evaluables", f"{entero(qc['received'])} / {entero(qc['evaluable'])}"],
        ["Calidad", "Excluidas, %", pct(excluded / qc["received"])],
        ["Calidad", "Fallo técnico, n", entero(qc["technical"])],
        ["Calidad", "Formato no admitido, n", entero(qc["format"])],
        ["Calidad", "Resolución insuficiente, n", entero(qc["resolution"])],
        ["Calidad", "Imagen uniforme, n", entero(qc["blank"])],
        ["Calidad", "Duplicado SHA-256, n", entero(qc["duplicate"])],
        ["Revisión", "Concordancia revisor 1 con el modelo, %", pct(rev["agree1"])],
        ["Revisión", "Concordancia revisor 2 con el modelo, %", pct(rev["agree2"])],
        ["Revisión", "Kappa entre revisores", num(rev["kappa"])],
        ["Revisión", "Falsos negativos rescatados / totales", f"{entero(rev['fn_rescued'])} / {entero(rev['fn'])}"],
        ["Revisión", "Falsos positivos corregidos / totales", f"{entero(rev['fp_corrected'])} / {entero(rev['fp'])}"],
        ["Tiempo", "Mediana con mapa, segundos (RIC)", f"{num(rev['med_with'], 0)} ({num(rev['q1_with'], 0)} a {num(rev['q3_with'], 0)})"],
        ["Tiempo", "Mediana sin mapa, segundos (RIC)", f"{num(rev['med_without'], 0)} ({num(rev['q1_without'], 0)} a {num(rev['q3_without'], 0)})"],
        ["Decisión", "Beneficio neto en el umbral cerrado", num(nb_thr)],
        ["Decisión", "Beneficio neto de confirmar a todas, mismo umbral", num(nb_all)],
    ]
    add_table(doc, ["Bloque", "Indicador", "Valor"], rows6, [2.6, 8.4, 6.0])
    note(doc, "RIC: recorrido intercuartílico. El beneficio neto está en la escala de la curva de decisión (verdaderos positivos netos por persona). El kappa es el de Cohen, sin ponderar.")

    h1(doc, "4. Discusión")
    add_p(
        doc,
        f"La respuesta a la pregunta principal es negativa en los dos sentidos que el protocolo había fijado. {pname} tuvo el mejor AUC de validación y el mejor AUC externo ({num(pe['auc_roc'])}; IC 95 % {ic(pe['auc_lo'], pe['auc_hi'])}), pero esa ventaja frente a DenseNet121 no superó el ajuste por multiplicidad. "
        "Y el umbral que en validación aseguraba 90 % de sensibilidad no sostuvo, fuera, el par de sensibilidad y especificidad del perfil de triaje. Ninguna de las cinco redes lo sostuvo. "
        "Lo que sí cambió con la arquitectura fue el tipo de error en el punto cerrado: el híbrido acertó la clasificación más a menudo que la red densa y dejó pasar más tuberculosis. Un programa que use el AUC como único contrato de compra elegiría el híbrido y podría incumplir la sensibilidad que había prometido.",
    )
    add_p(
        doc,
        f"Ese patrón dialoga con la evaluación de Dhaka, no con el AUC de 0,99 de una prueba de 150 imágenes {cite('qin2021', 'lakhani2017')}. "
        "Allí el AUC comercial quedó entre 0,849 y 0,908, y solo dos de cinco productos entraron en el rectángulo de 90 % y 70 %. "
        f"El AUC externo de este escenario ({num(pe['auc_roc'])}) queda por debajo de qXR y de CAD4TB y cerca del extremo inferior de aquella serie. "
        f"La caída por encima de los 60 años y el deterioro en tuberculosis previa repiten lo visto en Bangladesh y en la comparación de doce productos {cite('qin2021', 'codlin2021')}. "
        "No es un hallazgo nuevo de biología del modelo: es la consecuencia de pedir a una imagen que distinga actividad microbiológica cuando la secuela, la edad y el equipo empujan el puntaje hacia el mismo lado. "
        f"La especificidad de {pct(prior['specificity'])} % en tuberculosis previa, con un intervalo de AUC que cruza 0,50, es una alerta de seguridad, no un detalle de subgrupo.",
    )
    add_p(
        doc,
        f"La diferencia entre DeLong y McNemar merece quedar escrita para quien vaya a elegir un motor. DeLong pregunta si el orden de las probabilidades cambió. McNemar pregunta si, en el corte que el programa va a usar, cambian las personas bien clasificadas. "
        "Aquí el orden no se separó de DenseNet121 y los aciertos en el corte sí. Publicar solo el AUC habría dicho que las redes «son equivalentes» y habría ocultado que una preserva la sensibilidad transportada y la otra reduce falsos positivos. "
        f"El manual operativo de tamizaje insiste en recalibrar el umbral con datos locales antes de encender un programa {cite('handbook2021')}. "
        "Este escenario hace el experimento contrario a propósito: transporta el umbral sin tocarlo. El fracaso del perfil es, en parte, el costo de esa disciplina. Un umbral reajustado en E2 subiría la sensibilidad o la especificidad según el costo que se le pida, y ya no sería una validación limpia. Las dos cosas no caben en el mismo número.",
    )
    add_p(
        doc,
        f"La calibración viajó mejor que el punto de operación. El error esperado bajó de {num(pe['ece_raw'])} a {num(pe['ece'])} sin usar una sola etiqueta externa. "
        f"Eso no autoriza a leer la probabilidad como una frecuencia local: en E2 el error residual fue {num(st[prim]['e2']['ece'])}, y el valor predictivo cambió con la prevalencia aunque el AUC no lo hiciera. "
        f"Una probabilidad mal anclada es peor que un rango, porque el revisor puede tratar 0,40 como un riesgo que en su sede no es {cite('vancalster2019')}. "
        "El tablero del sistema muestra conteos, no un riesgo individual reetiquetado. Conviene que siga así hasta que cada sede estime su propio Platt o su propia prevalencia.",
    )
    add_p(
        doc,
        "El ViT compacto quedó por debajo y la diferencia de AUC sí sobrevivió a Holm. No se concluye que «los transformadores fallen en tuberculosis». Se concluye que esta red, pequeña y sin preentrenamiento, no compitió con tallos inicializados en ImageNet. "
        "El CNN-Transformer ocupa un lugar intermedio y su desventaja de AUC no fue significativa tras el ajuste. Comparar familias sin igualar parámetros ni datos de preentrenamiento confunde la arquitectura con la escala. El protocolo lo deja ver porque no finge un ViT-Base que el código no contiene.",
    )
    add_p(
        doc,
        f"En el flujo, la pieza que no depende de ganar el AUC es la que aparta la imagen antes de puntuarla. El {pct(excluded / qc['received'])} % de exclusiones no entra en la sensibilidad. Si se hubiera forzado una etiqueta, esos casos habrían ensuciado tanto el numerador como la confianza del revisor. "
        f"Los dos revisores no fueron un sello: rescataron {entero(rev['fn_rescued'])} de {entero(rev['fn'])} falsos negativos y dejaron {entero(rev['both_wrong_fn'])} sin marcar, y corrigieron {entero(rev['fp_corrected'])} de {entero(rev['fp'])} falsos positivos. "
        f"El kappa de {num(rev['kappa'])} indica acuerdo por encima del azar y, a la vez, desacuerdo suficiente para no automatizar la etiqueta final. "
        f"El mapa acortó la mediana de lectura de {num(rev['med_without'], 0)} a {num(rev['med_with'], 0)} segundos en 80 pares. "
        f"Eso no demuestra que el mapa señale la lesión verdadera. Las explicaciones visuales pueden ser plausibles y estar equivocadas, y un revisor puede anclarse a un halo rojo {cite('ghassemi2021', 'selvaraju2017')}. "
        "Por eso el contrato de datos guarda el mapa junto a la inferencia y la etiqueta final junto al identificador de esa inferencia: se puede auditar el desacuerdo, no solo celebrar el acuerdo.",
    )
    h2(doc, "4.1. Limitaciones")
    add_p(
        doc,
        "Validez interna. La partición por persona y el rechazo de imágenes repetidas cierran la fuga más grosera. El umbral y el escalado de Platt no vieron E1 ni E2. Esas son fortalezas del plan. La debilidad es que los cinco bloques de Friedman no reentrenan el modelo, de modo que no estiman la varianza de un ajuste nuevo. "
        "Validez de constructo. La referencia microbiológica no es la imagen. El modelo aprende apariencia y se le cobra actividad. En tuberculosis previa esa tensión deja de ser teórica: la especificidad se hunde. "
        "Validez externa. Dos sedes no son una red nacional. No se estratificó por marca de equipo, y otros trabajos mostraron que el equipo mueve el puntaje. "
        f"La edad mediana, cerca de 55 años, no representa un tamizaje de contactos jóvenes. "
        f"Validez estadística. Se informan los contrastes que no alcanzaron el umbral, en particular DeLong frente a DenseNet121 y todos los Wilcoxon por pares. El intervalo de VIH es demasiado ancho para una afirmación de subgrupo.",
    )
    h2(doc, "4.2. Implicaciones")
    add_p(
        doc,
        f"Quedan fuera el costo por caso confirmado, el efecto sobre el inicio de tratamiento y cualquier lectura de causalidad. También queda fuera presentar el sistema como producto sanitario. Lo que este resultado cambia, si la corrida real lo repite, es el criterio de compra: el AUC de validación no autoriza a prometer el perfil de triaje en otro hospital. La ruta siguiente es un umbral local explícito, un monitoreo que se calle cuando no hay etiquetas, y un ensayo que mida decisiones, no solo el área bajo la curva {cite('wiens2019', 'consort2020')}. "
        f"Mientras tanto, la ficha que ve el clínico debería decir para qué sede se cerró el umbral, qué sensibilidad se perdió al transportarlo y en qué subgrupo no debe usarse {cite('sendak2020')}. "
        f"Los atajos de imagen —marcas, texto quemado, posición del paciente— siguen siendo una amenaza no medida en este escenario {cite('geirhos2020', 'oakden2020')}.",
    )

    h1(doc, "5. Conclusiones")
    add_p(
        doc,
        f"En este escenario, {pname} fue la red de mayor AUC de validación y alcanzó un AUC externo de {num(pe['auc_roc'])} (IC 95 % {ic(pe['auc_lo'], pe['auc_hi'])}). Esa cifra no superó de forma significativa a DenseNet121. El umbral transportado no cumplió el perfil de triaje de 90 % de sensibilidad y 70 % de especificidad en ninguna de las cinco redes.",
    )
    add_p(
        doc,
        f"La diferencia que sí apareció fue de operación: en el corte cerrado el híbrido clasificó bien a más personas que la referencia densa, con menos falsos positivos y con una sensibilidad externa de {pct(pe['sensitivity'])} %, por debajo de la meta. DenseNet121 mantuvo la sensibilidad cerca de 90 % y especificó peor. La elección entre ambas no se resuelve con un solo número.",
    )
    add_p(
        doc,
        "La discriminación se deterioró a partir de los 60 años y dejó de ser útil en tuberculosis previa. El valor predictivo cambió con la prevalencia de la sede aunque el AUC no lo hiciera. El escalado de Platt viajó, y no viajó del todo: quedó error residual en la sede de mayor prevalencia.",
    )
    add_p(
        doc,
        "El aporte de diseño es el sistema: la imagen no evaluable sale antes del modelo, el umbral no se reabre con el sitio externo, la etiqueta final la escribe un revisor y la bitácora no se puede corregir en silencio. El sistema sigue siendo un prototipo de apoyo a la decisión y no una herramienta de programa.",
    )

    h1(doc, "Declaraciones")
    add_p(doc, "Financiación. [Por completar.]", align="left")
    add_p(doc, "Conflictos de interés. [Por completar. Los autores declaran, en su caso, la relación con el desarrollo del programa SP-02.]", align="left")
    add_p(doc, "Ética. [Por completar: dictamen de comité y, si aplica, exención de consentimiento con seudonimización.]", align="left")
    add_p(doc, "Disponibilidad. El programa SP-02 organiza la API, el cliente, el pipeline de modelos, los seis flujos y el servicio de consultas.", align="left")
    add_p(doc, "Contribución de autores. [Por completar según la taxonomía CRediT.]", align="left")
    add_p(
        doc,
        "Uso de inteligencia artificial generativa. Un asistente de lenguaje se usó para ordenar la prosa y comprobar la coherencia entre secciones. No generó imágenes clínicas, no eligió el umbral y no sustituye la lectura de las fuentes. La responsabilidad del texto es de los autores.",
        align="left",
    )

    h1(doc, "Referencias")
    for i, key in enumerate(ORDER, start=1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.75)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.08
        r = p.add_run(f"{i}. {LIB[key]}")
        set_run_font(r, size=10)
    missing = [k for k in ORDER if k not in LIB]
    if missing:
        raise RuntimeError(missing)
    doc.save(OUT)
    print(f"saved {OUT}")
    print(f"references {len(ORDER)}")


if __name__ == "__main__":
    build()
