# drive-site

Sincroniza una carpeta de Google Drive a GitHub Pages cada 24 horas.  
El script lee la carpeta recursivamente, descarga los archivos HTML y genera una navegación en grid de cards.

---

## Estructura del repositorio

```
drive-site/
├── .github/
│   └── workflows/
│       └── sync.yml          # Cron diario + trigger manual
├── scripts/
│   └── sync.py               # Lógica de sincronización
├── site-template/
│   └── assets/
│       └── style.css         # CSS del sitio generado
└── README.md
```

---

## Setup paso a paso

### 1. Google Cloud — Service Account

1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un proyecto nuevo (ej. `drive-site-sync`)
3. Activa la **Google Drive API**:  
   APIs & Services → Library → busca "Google Drive API" → Enable
4. Crea una Service Account:  
   APIs & Services → Credentials → Create Credentials → Service Account  
   - Nombre: `drive-sync`  
   - Role: no es necesario asignar uno a nivel de proyecto
5. En la Service Account creada, ve a **Keys** → Add Key → JSON  
   Descarga el archivo `.json` — lo necesitarás en el paso 3

6. **Comparte la carpeta de Drive** con el email de la Service Account  
   (algo como `drive-sync@tu-proyecto.iam.gserviceaccount.com`)  
   → Solo lectura es suficiente

---

### 2. Repositorio de GH Pages

Crea un repo en GitHub donde vivirá el sitio publicado.  
Puede ser `usuario.github.io` (sitio raíz) o cualquier repo con GH Pages habilitado.

En Settings → Pages:
- Source: **Deploy from a branch**
- Branch: `main` / `master`, carpeta: `/ (root)`

El script escribirá todo dentro de `/cursos/` para no pisar otros archivos.

---

### 3. Repositorio drive-site — Secrets y Variables

En este repo, ve a **Settings → Secrets and variables → Actions**:

#### Secrets (valores sensibles)
| Secret | Valor |
|--------|-------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Contenido completo del archivo `.json` descargado en el paso 1 |
| `PAGES_DEPLOY_TOKEN` | Personal Access Token con permisos `repo` (Settings → Developer Settings → PAT) |

#### Variables (configuración pública)
| Variable | Ejemplo |
|----------|---------|
| `DRIVE_FOLDER_ID` | ID de la carpeta raíz en Drive (ver abajo) |
| `PAGES_REPO` | `usuario/usuario.github.io` |
| `SITE_TITLE` | `Mis Cursos` |

#### Cómo obtener el DRIVE_FOLDER_ID
Abre la carpeta en Drive → la URL será:  
`https://drive.google.com/drive/folders/1ABC123xyz...`  
El ID es todo lo que va después de `/folders/`.

---

### 4. Ajustar la ruta de destino (opcional)

Por defecto el sitio se publica en `/cursos/` dentro del repo de Pages.  
Para cambiarlo, edita en `sync.yml`:

```yaml
- name: Copy generated site into Pages repo
  run: |
    rm -rf pages-repo/cursos        # ← cambia "cursos" aquí
    cp -r dist/ pages-repo/cursos   # ← y aquí
```

Y en `sync.py`, actualiza las rutas del CSS si cambias el segmento:

```python
def css_link() -> str:
    return '<link rel="stylesheet" href="/cursos/assets/style.css">'
    #                                      ^^^^^^^ cambia esto
```

---

### 5. Trigger manual

Una vez configurado, puedes disparar la sincronización manualmente desde:  
GitHub → Actions → "Sync Drive → GH Pages" → **Run workflow**

El cron corre automáticamente todos los días a las **5:00 AM UTC**.  
Para cambiarlo, edita la línea en `sync.yml`:

```yaml
- cron: "0 5 * * *"   # min hora día mes día-semana
```

---

## Estructura esperada en Drive

```
📁 Carpeta raíz (DRIVE_FOLDER_ID)
├── 📁 Módulo 1
│   ├── introduccion.html
│   ├── conceptos-basicos.html
│   └── 📁 Ejercicios
│       └── ejercicio-1.html
└── 📁 Módulo 2
    └── avanzado.html
```

Resultado en el sitio:

```
/cursos/                         → Grid con "Módulo 1" y "Módulo 2"
/cursos/modulo-1/                → Grid con páginas + carpeta "Ejercicios"
/cursos/modulo-1/introduccion.html
/cursos/modulo-1/ejercicios/     → Grid con "ejercicio-1"
```

---

## Personalización del CSS

El archivo `site-template/assets/style.css` controla el look del navegador  
(headers, cards, grid). Puedes editarlo libremente; se copia al `dist/`  
en cada sincronización.

Los archivos HTML descargados de Drive se sirven tal como están —  
el script no los modifica.
