"""Plain-language glossary shared by tooltips (help=) and the glossary expanders. Edit terms here."""
from __future__ import annotations

# term -> (full name, plain explanation)
GLOSSARY: dict[str, tuple[str, str]] = {
    "MAE": ("Error absoluto medio",
            "Cuántos kWh se equivoca el modelo, en promedio, en cada intervalo de 15 min. Menor es mejor."),
    "RMSE": ("Raíz del error cuadrático medio",
             "Parecido al MAE, pero castiga más los errores grandes. Se expresa en kWh; menor es mejor."),
    "MAPE": ("Error porcentual absoluto medio",
             "El error como porcentaje del consumo real. Aquí solo se calcula con consumos de 1 kWh o más, "
             "porque los valores cercanos a cero lo inflan."),
    "R²": ("Coeficiente de determinación",
           "Parte de la variación del consumo que el modelo logra explicar. 1 es perfecto; 0 equivale a "
           "predecir siempre el promedio."),
    "Valor p": ("Valor p",
                "Qué tan raro sería ver una diferencia así si en realidad no existiera. Un valor menor a 0.05 "
                "suele llamarse diferencia significativa."),
    "KPSS": ("Prueba de estacionariedad KPSS",
             "Revisa si el nivel de la serie se mantiene estable en el tiempo. Si se rechaza, el nivel cambia y "
             "conviene validar hacia adelante en el tiempo."),
    "VIF": ("Factor de inflación de la varianza",
            "Mide cuánto se repite una variable en las demás. Por encima de 10 se considera redundante."),
    "Spearman": ("Correlación de Spearman",
                 "Valor entre -1 y 1 que indica si dos variables suben o bajan juntas, sin exigir una relación "
                 "en línea recta."),
    "Kruskal-Wallis": ("Prueba de Kruskal-Wallis",
                       "Compara tres o más grupos (por ejemplo, los tres tipos de carga) y dice si al menos uno "
                       "tiene un consumo distinto."),
    "Dunn": ("Prueba de Dunn",
             "Sigue a Kruskal-Wallis: compara los grupos de dos en dos (con corrección de Bonferroni) para saber "
             "cuáles difieren."),
    "Mann-Whitney": ("Prueba de Mann-Whitney",
                     "Compara dos grupos (por ejemplo, día laborable y fin de semana) sin suponer que los datos "
                     "siguen una curva normal."),
    "Friedman": ("Prueba de Friedman",
                 "Compara varios modelos sobre las mismas semanas del examen, usando la posición que ocupa cada "
                 "modelo en cada semana."),
    "Nemenyi": ("Prueba de Nemenyi",
                "Sigue a Friedman: indica qué pares de modelos se distinguen entre sí."),
    "Diebold-Mariano": ("Prueba de Diebold-Mariano",
                        "Compara los errores de dos modelos sobre las mismas predicciones y dice si la diferencia "
                        "es real o ruido; tolera errores correlacionados en el tiempo."),
    "SHAP": ("Valores SHAP",
             "Reparten cada predicción entre las variables: cuántos kWh suma o resta cada una respecto del "
             "promedio de la planta."),
    "TimeSeriesSplit": ("Validación temporal (TimeSeriesSplit)",
                        "Siempre entrena con el pasado y valida con el futuro, sin mezclar fechas."),
}


def help_text(term: str) -> str:
    """One-line tooltip for a term, e.g. help_text("MAE")."""
    name, text = GLOSSARY[term]
    return f"{name}. {text}"
