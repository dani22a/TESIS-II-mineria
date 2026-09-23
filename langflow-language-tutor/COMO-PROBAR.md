# Cómo probar el tutor de idiomas (Langflow)

Réplica de la guía de Langflow: un agente que genera historias de lectura con el vocabulario que ya conoces y permite agregar palabras nuevas. Funciona en **inglés**, **español** y **chino**.

Abre Langflow en [http://127.0.0.1:7860](http://127.0.0.1:7860) y entra al flujo **Language Tutor**.

---

## 1. Arrancar con Podman

En PowerShell, desde esta carpeta:

```powershell
podman machine start
copy .env.example .env
```

En `.env` pega tu clave de Gemini (la misma de Google AI Studio):

```env
GOOGLE_API_KEY=tu_clave_aqui
GEMINI_API_KEY=tu_clave_aqui
```

El flujo **Language Tutor** usa esa clave: los agentes están en **Gemini 2.5 Flash** y leen `GOOGLE_API_KEY`. No hace falta pegar OpenAI.

Luego:

```powershell
podman compose up -d
```

Espera unos segundos (Langflow tarda en levantar) y entra a `http://127.0.0.1:7860`.

El usuario por defecto es `langflow` y la contraseña está en `.env` (`LANGFLOW_SUPERUSER_PASSWORD`). Con auto-login suele entrar solo.

Para parar:

```powershell
podman compose down
```

---

## 2. Antes del Playground (solo la primera vez)

1. Abre el flujo **Language Tutor**.
2. Confirma que **Language Agent** y **Create Story Tool** muestran **Gemini 2.5 Flash**. La API key ya entra por `.env`.
3. En **Word Loader** pulsa el botón de ejecutar (flecha), sobre todo si acabamos de ampliar el vocabulario.
4. Arriba a la derecha, pulsa **Playground**.

Sin ejecutar **Word Loader** al menos una vez, la herramienta de historias no tiene lista de palabras.

---

## 3. Qué hace el flujo

| Nodo | Para qué |
|---|---|
| **Upload Word File** | Carga un CSV a la base (opcional; ya hay vocabulario inicial). |
| **Word Loader** | Lee las palabras conocidas de Postgres. |
| **Prompt** | Arma la consigna: “crea una historia en {idioma} solo con estas palabras”. |
| **Create Story Tool** | Agente que escribe la historia (modo herramienta). |
| **Add word tool** | Agrega una palabra nueva al vocabulario. |
| **Language Agent** | Agente principal del chat: decide si crear historia o agregar palabra. |

Hay dos acciones, igual que en la guía original:

- Pedir una **historia** → usa Create Story Tool.
- Pedir **agregar una palabra** → usa Add word tool.

---

## 4. Pruebas por idioma

Usa un chat nuevo en el Playground para cada idioma si quieres ver el resultado más limpio.

### Inglés

```text
Create a story in English.
```

Resultado esperado: una historia corta (8–12 oraciones) con palabras tipo `school`, `friend`, `cat`, `apple`, `mother`.

Luego:

```text
Add the word library in English
```

Resultado esperado: `Added word: library (English)`.

Pide otra historia en inglés: debería poder usar `library`.

### Español

```text
Crea una historia en español.
```

Resultado esperado: una historia corta con título y 2-3 párrafos, gramática natural (no frases telegráficas). No debe repetir el mismo texto dos veces.

Luego:

```text
Agrega la palabra bosque en español
```

Resultado esperado: `Added word: bosque (Spanish)`.

### Chino

```text
Create a story in Chinese.
```

o:

```text
用中文写一个故事。
```

Resultado esperado: historia corta en chino simplificado, estilo similar al ejemplo de la guía (学校、朋友、猫、苹果、妈妈).

Luego:

```text
Add the word 台湾 in Chinese
```

Resultado esperado: `Added word: 台湾 (Chinese)`.

---

## 5. Cargar más vocabulario (opcional)

Los CSV están en `data/`:

| Archivo | Idioma |
|---|---|
| `data/words_en.csv` | Inglés (`word`) |
| `data/words_es.csv` | Español (`word`) |
| `data/words_zh.csv` | Chino (`word`) |
| `data/words_all.csv` | Los tres (`word,language`) |

En el nodo **Upload Word File**:

1. **Column Name:** `word`
2. Si usas `words_all.csv`, **Language Column:** `language`
3. Si usas un CSV de un solo idioma, elige **Default Language:** `en`, `es` o `zh`
4. Sube el archivo y ejecuta el nodo
5. Vuelve a ejecutar **Word Loader**

---

## 6. Si algo falla

| Qué ves | Qué hacer |
|---|---|
| Langflow no abre en `:7860` | `podman machine start` y luego `podman compose up -d`. Espera a que el health esté ok. |
| Language Model required | Elige Gemini en **Language Agent** y **Create Story Tool**. Revisa la API key. |
| Historia vacía o error de tools | Ejecuta **Word Loader** y confirma que **Add word tool** y **Create Story Tool** estén en modo herramienta (conectados a Tools del agente). |
| Palabra no aparece en la siguiente historia | Vuelve a ejecutar **Word Loader** después de agregar palabras. |
| Postgres vacío | El seed solo corre la primera vez que se crea el volumen. Si borraste el volumen, `podman compose down -v` y vuelve a levantar. |

---

## 7. Comandos útiles

```powershell
podman compose ps
podman compose logs -f langflow
podman compose down
```

Postgres queda mapeado en el host al puerto **5434** (dentro de la red de Podman sigue siendo `5432`).
