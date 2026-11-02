"""Reviewed scope; discovery never enables an unreviewed data source."""

COUNTRIES = {
    "BEN": "Bénin",
    "BFA": "Burkina Faso",
    "CPV": "Cabo Verde",
    "CIV": "Côte d’Ivoire",
    "GMB": "Gambie",
    "GHA": "Ghana",
    "GIN": "Guinée",
    "GNB": "Guinée-Bissau",
    "LBR": "Liberia",
    "MLI": "Mali",
    "MRT": "Mauritanie",
    "NER": "Niger",
    "NGA": "Nigeria",
    "SEN": "Sénégal",
    "SLE": "Sierra Leone",
    "TGO": "Togo",
    "KEN": "Kenya",
}
# code: (French title, canonical unit, known source methodology)
INDICATORS = {
    "NY.GDP.MKTP.CD": ("PIB nominal", "USD courants", "unspecified"),
    "NY.GDP.MKTP.KD.ZG": ("Croissance réelle du PIB", "% annuel", "unspecified"),
    "FP.CPI.TOTL.ZG": (
        "Inflation des prix à la consommation",
        "% annuel",
        "unspecified",
    ),
    "SL.UEM.TOTL.ZS": (
        "Chômage — estimation modélisée OIT",
        "% population active",
        "estimated",
    ),
    "SL.EMP.TOTL.SP.ZS": (
        "Emploi — estimation modélisée OIT",
        "% population âgée de 15 ans et plus",
        "estimated",
    ),
    "NE.EXP.GNFS.ZS": ("Exportations de biens et services", "% PIB", "unspecified"),
    "NE.IMP.GNFS.ZS": ("Importations de biens et services", "% PIB", "unspecified"),
    "BX.KLT.DINV.WD.GD.ZS": ("IDE, entrées nettes", "% PIB", "unspecified"),
    "NV.AGR.TOTL.ZS": ("Valeur ajoutée agricole", "% PIB", "unspecified"),
    "NV.IND.TOTL.ZS": ("Valeur ajoutée industrielle", "% PIB", "unspecified"),
    "NV.SRV.TOTL.ZS": ("Valeur ajoutée des services", "% PIB", "unspecified"),
}
TERMS = "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets"
API_DOC = "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392"
