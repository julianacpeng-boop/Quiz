#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JUH QUIZ — execução no GitHub Actions.
Base visual: V5_LAYOUT_IGUAL_HTML.

Fluxo:
1. autentica no Google;
2. lê a planilha;
3. baixa imagens privadas do Drive quando necessário;
4. gera os vídeos localmente;
5. envia os MP4 para uma nova pasta no Google Drive.
"""

import os
import io
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def carregar_credenciais():
    """
    Aceita um dos dois Secrets:
      GOOGLE_AUTHORIZED_USER_JSON  -> melhor para My Drive pessoal
      GOOGLE_SERVICE_ACCOUNT_JSON  -> simples; compartilhe planilha/pastas com o e-mail da conta
    """
    user_json = os.getenv("GOOGLE_AUTHORIZED_USER_JSON", "").strip()
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

    if user_json:
        info = json.loads(user_json)
        return UserCredentials.from_authorized_user_info(info, scopes=SCOPES)

    if sa_json:
        info = json.loads(sa_json)
        return ServiceAccountCredentials.from_service_account_info(info, scopes=SCOPES)

    raise RuntimeError(
        "Configure GOOGLE_AUTHORIZED_USER_JSON ou GOOGLE_SERVICE_ACCOUNT_JSON "
        "nos GitHub Actions Secrets."
    )

creds = carregar_credenciais()
gc = gspread.authorize(creds)
drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

SHEET_ID = os.getenv(
    "SHEET_ID",
    "1QDBF8XJfHbPqEXJjB_buIIOBr5PlbpXGQZC4He4OXho"
).strip()

OUTPUT_PARENT_ID = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", "").strip()
VIDEOS_FILTRO = os.getenv("VIDEOS", "ALL").strip()

VOZ = os.getenv("VOZ", "pt-BR-AntonioNeural")
VELOCIDADE_VOZ = os.getenv("VELOCIDADE_VOZ", "+10%")

W = 1080
H = 1920
FPS = 30
TEMPO_ESCOLHA = int(os.getenv("TEMPO_ESCOLHA", "5"))
TEMPO_RESPOSTA = float(os.getenv("TEMPO_RESPOSTA", "1.8"))

CARIMBO = datetime.now().strftime("%Y%m%d_%H%M")
PASTA_DRIVE = str(Path("output") / f"VIDEOS_{CARIMBO}")  # pasta local
PASTA_TMP = str(Path("tmp") / "juh_quiz_tmp")

Path(PASTA_DRIVE).mkdir(parents=True, exist_ok=True)
Path(PASTA_TMP).mkdir(parents=True, exist_ok=True)

print("✅ Google autenticado.")
print("✅ Planilha:", SHEET_ID)
print("🎯 Filtro de vídeos:", VIDEOS_FILTRO)
print("📁 Saída local:", PASTA_DRIVE)

def parse_videos(spec):
    spec = (spec or "ALL").strip().upper()
    if spec in ("ALL", "TODOS", "*"):
        return None
    ids = set()
    for parte in spec.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            a, b = parte.split("-", 1)
            a, b = int(a), int(b)
            inicio, fim = sorted((a, b))
            ids.update(range(inicio, fim + 1))
        else:
            ids.add(int(parte))
    return ids

def criar_pasta_drive(nome, parent_id):
    body = {
        "name": nome,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]
    return drive_service.files().create(
        body=body, fields="id,name", supportsAllDrives=True
    ).execute()

def enviar_arquivo_drive(caminho, parent_id):
    caminho = str(caminho)
    media = MediaFileUpload(caminho, mimetype="video/mp4", resumable=True)
    body = {"name": Path(caminho).name}
    if parent_id:
        body["parents"] = [parent_id]
    return drive_service.files().create(
        body=body,
        media_body=media,
        fields="id,name,webViewLink",
        supportsAllDrives=True,
    ).execute()



# ============================================================
# LER PLANILHA
# ============================================================

arquivo = gc.open_by_key(SHEET_ID)
print("✅ Planilha aberta:", arquivo.title)

def aba_para_df(nome):
    ws = arquivo.worksheet(nome)
    return pd.DataFrame(ws.get_all_records())

df = aba_para_df("Perguntas")
cfg = aba_para_df("Config")

for col in [
    "tema", "pergunta", "opcao_a", "opcao_b", "opcao_c",
    "resposta", "usar_imagem", "imagem_url", "ativo", "tipo_quiz"
]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

cfg["gerar_video"] = cfg["gerar_video"].astype(str).str.strip().str.upper()
df["ativo"] = df["ativo"].astype(str).str.strip().str.upper()
df["usar_imagem"] = df["usar_imagem"].astype(str).str.strip().str.upper()
df["resposta"] = df["resposta"].astype(str).str.strip().str.upper()

if "tipo_quiz" not in df.columns:
    df["tipo_quiz"] = "RESPOSTA"

df["tipo_quiz"] = df["tipo_quiz"].astype(str).str.strip().str.upper()
df.loc[df["tipo_quiz"] == "", "tipo_quiz"] = "RESPOSTA"

df["video_id"] = pd.to_numeric(df["video_id"], errors="raise").astype(int)
df["pergunta_num"] = pd.to_numeric(df["pergunta_num"], errors="raise").astype(int)
cfg["video_id"] = pd.to_numeric(cfg["video_id"], errors="raise").astype(int)
cfg["ordem"] = pd.to_numeric(cfg["ordem"], errors="raise").astype(int)

cfg_ativos = cfg[cfg["gerar_video"] == "SIM"].copy()
df = df[df["ativo"] == "SIM"].copy()

selecionados = parse_videos(VIDEOS_FILTRO)
if selecionados is not None:
    cfg_ativos = cfg_ativos[cfg_ativos["video_id"].isin(selecionados)].copy()
    df = df[df["video_id"].isin(selecionados)].copy()

cfg_ativos = cfg_ativos.sort_values("ordem")
df = df.sort_values(["video_id", "pergunta_num"])

print(f"✅ {len(cfg_ativos)} vídeos selecionados.")
print(f"✅ {len(df)} perguntas ativas.")
if len(cfg_ativos):
    print(cfg_ativos[["video_id", "tema", "cor_hex"]].to_string(index=False))

# ============================================================
# 4) FUNÇÕES VISUAIS — JUH QUIZ V13 / OPÇÃO 2
# PRETO + VERMELHO + BRANCO, ESTILO URBANO SIMPLES
# ============================================================

import math
import re
import io
import glob
import random
import requests
import regex as regex_u
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from pilmoji import Pilmoji

# ---------- fontes robustas ----------
def _achar_fonte(*candidatos):
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    for caminho in candidatos:
        if not caminho:
            continue
        nome = os.path.basename(caminho)
        achados = glob.glob(f"/usr/share/fonts/**/*{nome}", recursive=True)
        if achados:
            return achados[0]
    return None

FONT_BOLD = _achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
)
FONT_ITALIC = _achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf",
    FONT_BOLD,
)
FONT_REG = _achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    FONT_BOLD,
)

print("✅ Fontes:", FONT_BOLD, FONT_ITALIC, FONT_REG)

# ---------- paleta ----------
BLACK = (5,5,7)
BLACK_2 = (14,14,17)
BLACK_3 = (27,27,31)
RED = (238,20,35)
RED_DARK = (145,5,16)
RED_LIGHT = (255,68,76)
WHITE = (248,248,246)
OFFWHITE = (238,237,232)
GRAY = (92,92,96)
LIGHT_GRAY = (205,205,205)


def fonte(tamanho, bold=True, italic=False):
    if italic:
        caminho = FONT_ITALIC or FONT_BOLD or FONT_REG
    elif bold:
        caminho = FONT_BOLD or FONT_REG
    else:
        caminho = FONT_REG or FONT_BOLD
    if caminho:
        try:
            return ImageFont.truetype(caminho, int(tamanho))
        except Exception:
            pass
    try:
        return ImageFont.truetype("DejaVuSans.ttf", int(tamanho))
    except Exception:
        return ImageFont.load_default()


def wrap(draw, texto, fnt, max_width):
    palavras = str(texto).split()
    linhas, atual = [], ""
    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        bb = draw.textbbox((0,0), teste, font=fnt)
        if bb[2]-bb[0] <= max_width:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas



# ---------- emojis coloridos estilo WhatsApp/Android ----------
# Usa Noto Color Emoji (visual arredondado e próximo do WhatsApp/Android)
# e mantém a fonte normal para as palavras.
EMOJI_FONT_PATH = _achar_fonte(
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
)

def _eh_emoji_cluster(cluster):
    return bool(regex_u.search(r"\p{Extended_Pictographic}|\p{Regional_Indicator}", cluster))

def _render_emoji_cluster(cluster, alvo_px):
    # Noto Color Emoji costuma ter um strike fixo; renderiza grande e redimensiona.
    if not EMOJI_FONT_PATH:
        return None
    try:
        ef = ImageFont.truetype(EMOJI_FONT_PATH, 109)
        tmp = Image.new("RGBA", (180, 180), (0,0,0,0))
        td = ImageDraw.Draw(tmp)
        td.text((10, 2), cluster, font=ef, embedded_color=True)
        bbox = tmp.getbbox()
        if not bbox:
            return None
        crop = tmp.crop(bbox)
        ratio = alvo_px / max(1, crop.height)
        return crop.resize((max(1,int(crop.width*ratio)), alvo_px), Image.LANCZOS)
    except Exception:
        return None

def desenhar_texto_com_emoji(img, xy, texto, fnt, fill):
    texto = str(texto)
    d = ImageDraw.Draw(img)
    x, y = int(xy[0]), int(xy[1])
    clusters = regex_u.findall(r"\X", texto)
    normal = ""

    def flush_normal(txt, x0):
        if not txt:
            return x0
        d.text((x0,y), txt, font=fnt, fill=fill)
        bb = d.textbbox((0,0), txt, font=fnt)
        return x0 + (bb[2]-bb[0])

    # altura aproximada do texto para o emoji acompanhar a linha.
    bb_ref = d.textbbox((0,0), "Ag", font=fnt)
    emoji_h = max(24, int((bb_ref[3]-bb_ref[1]) * 1.15))

    for cl in clusters:
        if _eh_emoji_cluster(cl):
            x = flush_normal(normal, x)
            normal = ""
            emo = _render_emoji_cluster(cl, emoji_h)
            if emo is not None:
                yy = y + max(0, int((bb_ref[3]-bb_ref[1]-emoji_h)/2))
                img.alpha_composite(emo, (x, yy)) if img.mode == "RGBA" else img.paste(emo, (x, yy), emo)
                x += emo.width + 3
            else:
                d.text((x,y), cl, font=fnt, fill=fill)
                bb = d.textbbox((0,0), cl, font=fnt)
                x += bb[2]-bb[0]
        else:
            normal += cl
    flush_normal(normal, x)

def desenhar_texto_opcao(img, xy, texto, fnt, fill):
    desenhar_texto_com_emoji(img, xy, texto, fnt, fill)


def texto_centro(draw, texto, fnt, y, fill, stroke_width=0, stroke_fill=None):
    bb = draw.textbbox((0,0), str(texto), font=fnt, stroke_width=stroke_width)
    tw = bb[2]-bb[0]
    draw.text(
        ((W-tw)//2,y), str(texto), font=fnt, fill=fill,
        stroke_width=stroke_width, stroke_fill=stroke_fill
    )


def baixar_imagem(url):
    if not url or str(url).lower() in ("nan","none"):
        return None
    url = str(url).strip()
    try:
        m = re.search(r"/d/([A-Za-z0-9_-]+)", url) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
        if "drive.google.com" in url and m:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseDownload
            file_id = m.group(1)
            request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _,done = downloader.next_chunk()
            fh.seek(0)
            return Image.open(fh).convert("RGB")
        r = requests.get(url,timeout=20)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print("  ⚠ imagem não carregada:", e)
        return None


def cover(img,size):
    img = img.copy()
    ratio = max(size[0]/img.width,size[1]/img.height)
    novo = (int(img.width*ratio),int(img.height*ratio))
    img = img.resize(novo,Image.LANCZOS)
    x=(img.width-size[0])//2
    y=(img.height-size[1])//2
    return img.crop((x,y,x+size[0],y+size[1]))

def encaixar_sem_corte(img, size):
    """
    Mostra a imagem inteira dentro do quadro, sem recortar nenhuma parte.
    O espaço restante é preenchido com a própria imagem desfocada,
    preservando o tamanho e todo o restante do layout do quiz.
    """
    img = img.copy().convert("RGB")
    alvo_w, alvo_h = size

    # Fundo: mantém o quadro totalmente preenchido, mas não é a imagem principal.
    fundo = cover(img, size).filter(ImageFilter.GaussianBlur(radius=18))

    # Imagem principal: CONTAIN, nunca corta.
    ratio = min(alvo_w / img.width, alvo_h / img.height)
    novo_w = max(1, int(round(img.width * ratio)))
    novo_h = max(1, int(round(img.height * ratio)))
    frente = img.resize((novo_w, novo_h), Image.LANCZOS)

    x = (alvo_w - novo_w) // 2
    y = (alvo_h - novo_h) // 2
    fundo.paste(frente, (x, y))
    return fundo


def fundo_urbano():
    img = Image.new("RGB",(W,H),BLACK)
    d = ImageDraw.Draw(img)

    # textura geométrica discreta
    for y in range(0,H,72):
        for x in range(0,W,72):
            if ((x//72)+(y//72))%5==0:
                d.ellipse((x+10,y+10,x+15,y+15),fill=(55,8,12))

    # pinceladas/vermelho nos cantos
    d.polygon([(0,0),(210,0),(0,245)],fill=(70,4,8))
    d.polygon([(W,H-285),(W,H),(805,H)],fill=(68,4,8))

    # diagonais
    for off in (0,28,56):
        d.line((0,260+off,120,140+off),fill=RED_DARK,width=5)
        d.line((W,360+off,W-100,460+off),fill=RED_DARK,width=5)

    # halftone lateral
    for yy in range(470,750,24):
        for xx in range(18,120,24):
            if (xx+yy)%48==0:
                d.ellipse((xx,yy,xx+6,yy+6),fill=(105,8,14))
    for yy in range(1220,1550,24):
        for xx in range(W-120,W-18,24):
            if (xx+yy)%48==0:
                d.ellipse((xx,yy,xx+6,yy+6),fill=(105,8,14))

    return img


def desenhar_logo(img):
    d = ImageDraw.Draw(img)
    f1=fonte(132,italic=True)
    f2=fonte(146,italic=True)

    # JUH branco com sombra preta/vermelha
    bb=d.textbbox((0,0),"JUH",font=f1,stroke_width=5)
    x=(W-(bb[2]-bb[0]))//2
    d.text((x+8,44+10),"JUH",font=f1,fill=(50,0,0),stroke_width=7,stroke_fill=(0,0,0))
    d.text((x,44),"JUH",font=f1,fill=WHITE,stroke_width=5,stroke_fill=(20,20,20))

    # QUIZ vermelho
    bb=d.textbbox((0,0),"QUIZ",font=f2,stroke_width=5)
    x=(W-(bb[2]-bb[0]))//2
    d.text((x+8,165+10),"QUIZ",font=f2,fill=(65,0,0),stroke_width=7,stroke_fill=(0,0,0))
    d.text((x,165),"QUIZ",font=f2,fill=RED,stroke_width=5,stroke_fill=(20,20,20))

    # bolha com ?
    d.ellipse((790,72,884,166),fill=WHITE,outline=RED,width=6)
    qf=fonte(57)
    bb=d.textbbox((0,0),"?",font=qf)
    d.text((837-(bb[2]-bb[0])//2,87),"?",font=qf,fill=RED)


def categoria_label(img,tema):
    d=ImageDraw.Draw(img)
    box=(235,385,845,470)
    d.rounded_rectangle(box,radius=38,fill=RED,outline=WHITE,width=3)

    tema_u=str(tema).upper()
    if "RELACION" in tema_u:
        simbolo="♥"
    elif "PORTUG" in tema_u:
        simbolo="A"
    elif "MATEM" in tema_u:
        simbolo="∑"
    elif "TREND" in tema_u or "MOMENTO" in tema_u:
        simbolo="↑"
    else:
        simbolo="?"

    sf=fonte(34)
    d.ellipse((250,398,315,463),fill=WHITE)
    bb=d.textbbox((0,0),simbolo,font=sf)
    d.text((282-(bb[2]-bb[0])//2,408),simbolo,font=sf,fill=RED)

    tf=fonte(36)
    bb=d.textbbox((0,0),tema_u,font=tf)
    tw=bb[2]-bb[0]
    # reduz se categoria longa
    if tw>470:
        tf=fonte(29)
        bb=d.textbbox((0,0),tema_u,font=tf)
        tw=bb[2]-bb[0]
    d.text((580-tw//2,408),tema_u,font=tf,fill=WHITE)


def papel_polygon(box):
    x1,y1,x2,y2=box
    # borda levemente irregular, mas estável
    return [
        (x1+12,y1),(x1+90,y1+5),(x1+165,y1-3),(x1+250,y1+4),
        (x1+350,y1-2),(x1+455,y1+3),(x1+560,y1-4),(x2-15,y1+5),
        (x2,y1+20),(x2-5,y2-18),(x2-80,y2-3),(x2-170,y2+2),
        (x2-275,y2-3),(x2-390,y2+3),(x1+110,y2-2),(x1,y2-18)
    ]


def criar_card(pergunta,tema,cor_hex,numero,total,revelar=False,timer_texto="ESCOLHA"):
    """
    PADRÃO V5 — CÓPIA VISUAL DO HTML/PRINT APROVADO:
      • fundo preto e moldura externa vermelha com brilho;
      • JUH QUIZ no topo à esquerda;
      • "Pergunta X de Y" no topo à direita;
      • categoria branca dentro de faixa vermelha;
      • pergunta em caixa preta com borda vermelha;
      • com imagem: imagem 16:9 grande logo abaixo, inteira e sem corte;
      • alternativas A/B/C em caixas pretas com borda vermelha;
      • sem imagem: o mesmo padrão visual, com a pergunta ocupando a área da imagem;
      • leitura: "ESCOLHA A OPÇÃO" no rodapé;
      • contagem: a frase some e entram barra regressiva + cronômetro embaixo;
      • resposta: alternativa correta destacada + "COMENTE SUA PONTUAÇÃO!";
      • opinião: após a contagem, "E VOCÊ? A, B OU C? FALA NOS COMENTÁRIOS."
    """
    tipo = str(pergunta.get("tipo_quiz", "RESPOSTA")).strip().upper()
    eh_opiniao = tipo in ("OPINIÃO", "OPINIAO")

    # ==========================================================
    # FUNDO / MOLDURA — igual ao HTML preto + vermelho
    # ==========================================================
    img = Image.new("RGB", (W, H), (4, 4, 5))

    # brilho vermelho atrás da moldura
    glow = Image.new("RGBA", (W, H), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle((43, 55, W-43, H-45), radius=62,
                         outline=(238,20,35,215), width=16)
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    d = ImageDraw.Draw(img)
    outer = (50, 65, W-50, H-55)
    d.rounded_rectangle(outer, radius=58, fill=(9,9,10), outline=RED, width=6)

    # leve vinheta vermelha superior, como no HTML
    overlay = Image.new("RGBA", (W,H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((-120,-220,1200,610), fill=(125,0,10,42))
    overlay = overlay.filter(ImageFilter.GaussianBlur(95))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(outer, radius=58, outline=RED, width=6)

    # ==========================================================
    # TOPO — JUH QUIZ À ESQUERDA / PERGUNTA À DIREITA
    # ==========================================================
    brand_y = 118
    brand_x = 102
    bf = fonte(56)
    d.text((brand_x, brand_y), "JUH", font=bf, fill=WHITE)
    juh_w = d.textbbox((0,0), "JUH", font=bf)[2]
    d.text((brand_x + juh_w + 13, brand_y), "QUIZ", font=bf, fill=RED)

    contador = f"Pergunta {numero} de {total}"
    cf = fonte(30)
    cbb = d.textbbox((0,0), contador, font=cf)
    ctw = cbb[2]-cbb[0]
    cth = 76
    cx2 = W-100
    cx1 = max(620, cx2-ctw-62)
    cy1 = 108
    cy2 = cy1+cth
    d.rounded_rectangle((cx1,cy1,cx2,cy2), radius=38,
                        fill=(15,15,16), outline=RED, width=4)
    d.text((cx1+(cx2-cx1-ctw)//2, cy1+20), contador, font=cf, fill=WHITE)

    # ==========================================================
    # CATEGORIA — TEXTO BRANCO DENTRO DA FAIXA VERMELHA
    # ==========================================================
    tema_txt = str(tema).upper().strip()
    cat_font_size = 29
    catf = fonte(cat_font_size)
    max_cat_w = 790
    tbb = d.textbbox((0,0), tema_txt, font=catf)
    tw = tbb[2]-tbb[0]
    while tw > max_cat_w-54 and cat_font_size > 21:
        cat_font_size -= 1
        catf = fonte(cat_font_size)
        tbb = d.textbbox((0,0), tema_txt, font=catf)
        tw = tbb[2]-tbb[0]

    cat_x1 = 100
    cat_y1 = 215
    cat_h = 62
    cat_x2 = min(W-100, cat_x1 + tw + 48)
    d.rounded_rectangle((cat_x1,cat_y1,cat_x2,cat_y1+cat_h),
                        radius=31, fill=RED)
    d.text((cat_x1+24, cat_y1+(cat_h-(tbb[3]-tbb[1]))//2-3),
           tema_txt, font=catf, fill=WHITE)

    # ==========================================================
    # IMAGEM (SE HOUVER)
    # ==========================================================
    usar_img = str(pergunta.get("usar_imagem", "NÃO")).strip().upper() == "SIM"
    url = str(pergunta.get("imagem_url", "")).strip()
    im = None
    if usar_img and url and url.lower() not in ("nan", "none"):
        im = baixar_imagem(url)

    # ==========================================================
    # PERGUNTA — MESMA CAIXA DO HTML
    # ==========================================================
    if im is not None:
        q_box = (100, 310, W-100, 565)
        q_font_size = 38
        q_max_lines = 5
    else:
        # Sem imagem: mantém o mesmo desenho e usa o espaço central
        q_box = (100, 310, W-100, 755)
        q_font_size = 43
        q_max_lines = 7

    d.rounded_rectangle(q_box, radius=42, fill=(18,18,19), outline=RED, width=6)

    qtxt = str(pergunta["pergunta"]).strip()
    qf = fonte(q_font_size)
    q_width = q_box[2]-q_box[0]-82
    linhas = wrap(d, qtxt, qf, q_width)
    while len(linhas) > q_max_lines and q_font_size > 27:
        q_font_size -= 2
        qf = fonte(q_font_size)
        linhas = wrap(d, qtxt, qf, q_width)

    linhas = linhas[:q_max_lines]
    line_h = q_font_size + 11
    total_h = len(linhas)*line_h
    qy = q_box[1] + max(18, (q_box[3]-q_box[1]-total_h)//2)
    for linha in linhas:
        bb = d.textbbox((0,0), linha, font=qf)
        linha_w = bb[2]-bb[0]
        desenhar_texto_com_emoji(
            img, ((W-linha_w)//2, qy), linha, qf, WHITE
        )
        qy += line_h

    # ==========================================================
    # IMAGEM 16:9 — GRANDE, INTEIRA, MESMAS BORDAS VERMELHAS
    # ==========================================================
    if im is not None:
        image_area = (100, 595, W-100, 1090)  # 880 x 495 = 16:9 exato
        alvo_w = image_area[2]-image_area[0]
        alvo_h = image_area[3]-image_area[1]

        original = im.copy().convert("RGB")
        ratio = min(alvo_w/original.width, alvo_h/original.height)
        novo_w = max(1, int(round(original.width*ratio)))
        novo_h = max(1, int(round(original.height*ratio)))
        frente = original.resize((novo_w, novo_h), Image.LANCZOS)

        fundo_img = Image.new("RGB", (alvo_w, alvo_h), (0,0,0))
        px = (alvo_w-novo_w)//2
        py = (alvo_h-novo_h)//2
        fundo_img.paste(frente, (px,py))

        mask = Image.new("L", (alvo_w,alvo_h), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle((0,0,alvo_w-1,alvo_h-1), radius=38, fill=255)
        img.paste(fundo_img, (image_area[0],image_area[1]), mask)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(image_area, radius=38, outline=RED, width=6)

    # ==========================================================
    # ALTERNATIVAS — IGUAIS AO HTML
    # ==========================================================
    opts = [
        ("A", str(pergunta["opcao_a"])),
        ("B", str(pergunta["opcao_b"])),
        ("C", str(pergunta["opcao_c"])),
    ]
    correta = str(pergunta.get("resposta", "")).strip().upper()

    if im is not None:
        opt_y = 1125
        opt_h = 137
        gap = 18
        opt_font_size = 31
        circle_d = 88
    else:
        opt_y = 805
        opt_h = 185
        gap = 24
        opt_font_size = 36
        circle_d = 96

    for letra, txt in opts:
        correta_agora = revelar and (not eh_opiniao) and correta == letra
        box = (100, opt_y, W-100, opt_y+opt_h)

        if correta_agora:
            fill = RED
            outline = WHITE
            txt_color = WHITE
            circle_fill = WHITE
            circle_text = RED
        else:
            fill = (18,18,19)
            outline = RED
            txt_color = WHITE
            circle_fill = RED
            circle_text = WHITE

        d.rounded_rectangle(box, radius=34, fill=fill, outline=outline, width=5)

        circle_x1 = 126
        circle_y1 = opt_y + (opt_h-circle_d)//2
        circle_x2 = circle_x1 + circle_d
        circle_y2 = circle_y1 + circle_d
        d.ellipse((circle_x1,circle_y1,circle_x2,circle_y2),
                  fill=circle_fill, outline=RED_LIGHT, width=3)

        lf = fonte(44 if im is None else 40)
        lbb = d.textbbox((0,0), letra, font=lf)
        lw = lbb[2]-lbb[0]
        lh = lbb[3]-lbb[1]
        d.text(((circle_x1+circle_x2-lw)//2,
                circle_y1+(circle_d-lh)//2-5),
               letra, font=lf, fill=circle_text)

        text_x = circle_x2 + 35
        max_text_w = box[2]-text_x-35
        if correta_agora:
            max_text_w -= 72

        fs = opt_font_size
        of = fonte(fs)
        linhas_opt = wrap(d, txt, of, max_text_w)
        while len(linhas_opt) > 2 and fs > 24:
            fs -= 2
            of = fonte(fs)
            linhas_opt = wrap(d, txt, of, max_text_w)
        linhas_opt = linhas_opt[:2]

        line_step = fs + 8
        total_opt_h = len(linhas_opt)*line_step
        ty = opt_y + (opt_h-total_opt_h)//2 - 2
        for linha in linhas_opt:
            desenhar_texto_opcao(img, (text_x, ty), linha, of, txt_color)
            ty += line_step

        if correta_agora:
            cx = box[2]-58
            cy = opt_y+opt_h//2
            d.ellipse((cx-30,cy-30,cx+30,cy+30), outline=WHITE, width=4)
            d.line((cx-15,cy, cx-4,cy+12), fill=WHITE, width=5)
            d.line((cx-4,cy+12, cx+18,cy-15), fill=WHITE, width=5)

        opt_y += opt_h + gap

    # ==========================================================
    # RODAPÉ — ESCOLHA -> CONTAGEM EMBAIXO -> CTA
    # ==========================================================
    estado = str(timer_texto).strip().upper()
    footer_top = 1650 if im is not None else 1515
    progress_y = 1771
    timer_cx, timer_cy = 909, 1782

    # leitura
    if not revelar and not estado.startswith("00:"):
        label = "ESCOLHA A OPÇÃO"
        lf2 = fonte(31)
        lbb = d.textbbox((0,0), label, font=lf2)
        ltw = lbb[2]-lbb[0]
        pill = (100, footer_top+30, W-100, footer_top+118)
        d.rounded_rectangle(pill, radius=42, fill=RED)
        d.text(((W-ltw)//2, pill[1]+24), label, font=lf2, fill=WHITE)

    # contagem regressiva — frase desaparece, entra barra + círculo
    elif estado.startswith("00:"):
        try:
            segundos = int(estado.split(":")[-1])
        except Exception:
            segundos = 5
        segundos = max(1, min(int(TEMPO_ESCOLHA), segundos))
        frac = segundos / max(1, int(TEMPO_ESCOLHA))

        bar_x1, bar_x2 = 100, 815
        bar_h = 22
        d.rounded_rectangle((bar_x1,progress_y,bar_x2,progress_y+bar_h),
                            radius=11, fill=(48,48,50))
        fill_x2 = bar_x1 + int((bar_x2-bar_x1)*frac)
        if fill_x2 > bar_x1:
            d.rounded_rectangle((bar_x1,progress_y,fill_x2,progress_y+bar_h),
                                radius=11, fill=RED)

        d.ellipse((timer_cx-53,timer_cy-53,timer_cx+53,timer_cy+53),
                  fill=(14,14,15), outline=RED, width=6)
        tf = fonte(36)
        num = f"{segundos:02d}"
        tbb = d.textbbox((0,0), num, font=tf)
        d.text((timer_cx-(tbb[2]-tbb[0])//2,
                timer_cy-(tbb[3]-tbb[1])//2-6),
               num, font=tf, fill=WHITE)

    # tela final
    else:
        if eh_opiniao:
            cta = "E VOCÊ? A, B OU C? FALA NOS COMENTÁRIOS."
            cta_size = 27
        else:
            cta = "COMENTE SUA PONTUAÇÃO!"
            cta_size = 31

        pill = (100, footer_top+30, W-100, footer_top+126)
        d.rounded_rectangle(pill, radius=45, fill=RED, outline=WHITE, width=3)
        cf2 = fonte(cta_size)
        cbb = d.textbbox((0,0), cta, font=cf2)
        ctw = cbb[2]-cbb[0]
        while ctw > (pill[2]-pill[0]-46) and cta_size > 20:
            cta_size -= 1
            cf2 = fonte(cta_size)
            cbb = d.textbbox((0,0), cta, font=cf2)
            ctw = cbb[2]-cbb[0]
        d.text(((W-ctw)//2, pill[1]+28), cta, font=cf2, fill=WHITE)

    return img


# ============================================================
# 5) VOZ + FFMPEG — SINCRONIZAÇÃO ROBUSTA
# ============================================================

import subprocess
import json as jsonlib
import os
import regex as regex_u

AUDIO_HZ = 48000
AUDIO_CHANNELS = 2

def limpar_emojis_tts(texto):
    """Remove emojis apenas do texto enviado à voz; na imagem eles continuam aparecendo."""
    texto = str(texto)
    texto = regex_u.sub(r"\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?)*", "", texto)
    texto = regex_u.sub(r"\p{Regional_Indicator}{2}", "", texto)
    texto = regex_u.sub(r"[\uFE0F\uFE0E\u200D]", "", texto)
    texto = regex_u.sub(r"\s+", " ", texto).strip()
    return texto

def executar(cmd):
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if p.returncode != 0:
        print(p.stderr[-3500:])
        raise RuntimeError("FFmpeg retornou erro.")
    return p

def tts_salvar(texto, caminho):
    """
    Edge TTS via linha de comando.
    Cada arquivo tem nome exclusivo da pergunta para não reaproveitar áudio.
    """
    if os.path.exists(caminho):
        os.remove(caminho)

    cmd = [
        "edge-tts",
        "--voice", VOZ,
        "--rate", VELOCIDADE_VOZ,
        "--text", limpar_emojis_tts(texto),
        "--write-media", caminho
    ]
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if p.returncode != 0:
        print(p.stderr)
        raise RuntimeError("Falha ao gerar voz.")

    if not os.path.exists(caminho) or os.path.getsize(caminho) < 500:
        raise RuntimeError(f"Áudio não foi criado corretamente: {caminho}")

def duracao_audio(caminho):
    cmd = [
        "ffprobe","-v","error",
        "-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",
        caminho
    ]
    out = subprocess.check_output(cmd,text=True).strip()
    return float(out)

def criar_clipe_imagem(img_path, duracao, saida, audio=None):
    """
    Todo segmento sai exatamente com:
    - 1080x1920
    - 30 fps
    - H264/yuv420p
    - AAC 48 kHz estéreo
    Isso elimina a deriva de áudio entre as perguntas.
    """
    if os.path.exists(saida):
        os.remove(saida)

    duracao = float(duracao)

    if audio:
        cmd = [
            "ffmpeg","-y",
            "-loop","1","-i",img_path,
            "-i",audio,
            "-t",f"{duracao:.3f}",
            "-vf",f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-af",f"aresample={AUDIO_HZ}:async=1:first_pts=0,apad",
            "-c:v","libx264","-preset","veryfast","-crf","20",
            "-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","160k",
            "-ar",str(AUDIO_HZ),"-ac",str(AUDIO_CHANNELS),
            "-video_track_timescale","90000",
            "-avoid_negative_ts","make_zero",
            "-movflags","+faststart",
            saida
        ]
    else:
        cmd = [
            "ffmpeg","-y",
            "-loop","1","-i",img_path,
            "-f","lavfi","-i",
            f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_HZ}",
            "-t",f"{duracao:.3f}",
            "-vf",f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-c:v","libx264","-preset","veryfast","-crf","20",
            "-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","160k",
            "-ar",str(AUDIO_HZ),"-ac",str(AUDIO_CHANNELS),
            "-video_track_timescale","90000",
            "-avoid_negative_ts","make_zero",
            "-shortest",
            "-movflags","+faststart",
            saida
        ]

    executar(cmd)


def criar_beep(caminho, frequencia=950):
    """
    Cria um bip curto de 1 segundo.
    O som toca no início de cada segundo da contagem.
    """
    if os.path.exists(caminho):
        os.remove(caminho)

    cmd = [
        "ffmpeg","-y",
        "-f","lavfi","-i",
        f"sine=frequency={frequencia}:duration=0.14",
        "-af","volume=0.55,apad=pad_dur=1",
        "-t","1.0",
        "-c:a","aac","-b:a","160k",
        "-ar",str(AUDIO_HZ),
        "-ac",str(AUDIO_CHANNELS),
        caminho
    ]
    executar(cmd)

def juntar_clipes(lista, saida, concat_path):
    """
    Junta SOMENTE segmentos já normalizados.
    Cada pergunta é fechada em um arquivo próprio antes de entrar no vídeo final.
    """
    with open(concat_path,"w",encoding="utf-8") as f:
        for p in lista:
            f.write("file '" + p.replace("'", "'\\''") + "'\n")

    cmd = [
        "ffmpeg","-y",
        "-fflags","+genpts",
        "-f","concat","-safe","0","-i",concat_path,
        "-c:v","libx264","-preset","veryfast","-crf","20",
        "-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k",
        "-ar",str(AUDIO_HZ),"-ac",str(AUDIO_CHANNELS),
        "-af",f"aresample={AUDIO_HZ}:async=1:first_pts=0",
        "-avoid_negative_ts","make_zero",
        "-movflags","+faststart",
        saida
    ]
    executar(cmd)

# ============================================================
# 6) GERAR OS VÍDEOS — JUH QUIZ V13
# LEITURA -> CONTAGEM DE 5s COM BIP -> RESPOSTA/OPINIÃO
# QUANTIDADE DE PERGUNTAS É FLEXÍVEL
# ============================================================

import shutil
import re

if os.path.exists(PASTA_TMP):
    shutil.rmtree(PASTA_TMP)
os.makedirs(PASTA_TMP, exist_ok=True)

# Bips da contagem
BEEP_NORMAL = os.path.join(PASTA_TMP, "beep_contagem.m4a")
BEEP_FINAL = os.path.join(PASTA_TMP, "beep_final.m4a")
criar_beep(BEEP_NORMAL, 950)
criar_beep(BEEP_FINAL, 1250)

videos_gerados = []

for _, conf in cfg_ativos.iterrows():
    video_id = int(conf["video_id"])
    tema = str(conf["tema"])
    cor = str(conf["cor_hex"])

    perguntas = (
        df[df["video_id"] == video_id]
        .copy()
        .sort_values("pergunta_num")
        .reset_index(drop=True)
    )

    total = len(perguntas)

    if total == 0:
        print(f"⚠ Vídeo {video_id}: sem perguntas. Pulando.")
        continue

    # pergunta_num serve apenas para ordenar as linhas.
    # A numeração mostrada/falada será sempre 1..total.
    if perguntas["pergunta_num"].duplicated().any():
        repetidos = perguntas.loc[
            perguntas["pergunta_num"].duplicated(),
            "pergunta_num"
        ].tolist()
        raise ValueError(
            f"Vídeo {video_id} ({tema}) tem pergunta_num repetido: "
            f"{repetidos}"
        )

    print("")
    print("="*74)
    print(f"🎬 VÍDEO {video_id:02d} — {tema}")
    print(f"Total de perguntas ativas: {total}")
    print("="*74)

    pasta_video = os.path.join(
        PASTA_TMP,
        f"video_{video_id:02d}"
    )
    os.makedirs(pasta_video, exist_ok=True)

    clips_perguntas = []

    for indice, (_, p) in enumerate(
        perguntas.iterrows(),
        start=1
    ):
        dados = p.to_dict()

        # Número visual e falado SEMPRE vem da posição atual.
        # Assim, mesmo que você desative perguntas na planilha,
        # o vídeo continua 1/7, 2/7, 3/7...
        numero = indice

        tipo_quiz = (
            str(dados.get("tipo_quiz","RESPOSTA"))
            .strip().upper()
        )
        eh_opiniao = tipo_quiz in ("OPINIÃO","OPINIAO")

        pasta_q = os.path.join(
            pasta_video,
            f"q{numero:02d}"
        )
        os.makedirs(pasta_q, exist_ok=True)

        print(f" • PERGUNTA {numero}/{total}")
        print(f"   Texto: {dados['pergunta']}")

        segmentos_q = []

        # ====================================================
        # A) LEITURA COMPLETA
        # ====================================================
        texto_leitura = (
            f"Pergunta {numero} de {total}. "
            f"{dados['pergunta']} "
            f"Alternativa A. {dados['opcao_a']}. "
            f"Alternativa B. {dados['opcao_b']}. "
            f"Alternativa C. {dados['opcao_c']}."
        )

        audio_leitura = os.path.join(
            pasta_q,
            f"Q{numero:02d}_LEITURA.mp3"
        )
        tts_salvar(texto_leitura, audio_leitura)
        dur_leitura = duracao_audio(audio_leitura) + 0.20

        frame_leitura = os.path.join(
            pasta_q,
            "01_leitura.png"
        )
        criar_card(
            dados, tema, cor,
            numero=numero,
            total=total,
            revelar=False,
            timer_texto="ESCOLHA"
        ).save(frame_leitura)

        clip_leitura = os.path.join(
            pasta_q,
            "01_leitura.mp4"
        )
        criar_clipe_imagem(
            frame_leitura,
            dur_leitura,
            clip_leitura,
            audio=audio_leitura
        )
        segmentos_q.append(clip_leitura)

        # ====================================================
        # B) CONTAGEM 5 -> 1 COM BIP EM CADA SEGUNDO
        # ====================================================
        for ordem_timer, segundos in enumerate(
            range(int(TEMPO_ESCOLHA), 0, -1),
            start=2
        ):
            frame_timer = os.path.join(
                pasta_q,
                f"{ordem_timer:02d}_timer_{segundos}.png"
            )

            criar_card(
                dados, tema, cor,
                numero=numero,
                total=total,
                revelar=False,
                timer_texto=f"00:0{segundos}"
            ).save(frame_timer)

            clip_timer = os.path.join(
                pasta_q,
                f"{ordem_timer:02d}_timer_{segundos}.mp4"
            )

            som_timer = (
                BEEP_FINAL if segundos == 1
                else BEEP_NORMAL
            )

            criar_clipe_imagem(
                frame_timer,
                1.0,
                clip_timer,
                audio=som_timer
            )
            segmentos_q.append(clip_timer)

        # ====================================================
        # C) RESPOSTA / OPINIÃO
        # ====================================================
        if eh_opiniao:
            texto_final = (
                "E você? A, B ou C? "
                "Fala nos comentários."
            )
            timer_final = "OPINE"
        else:
            correta = str(
                dados.get("resposta","")
            ).strip().upper()

            if correta not in ("A","B","C"):
                raise ValueError(
                    f"Pergunta {numero} de {tema}: "
                    f"resposta inválida '{correta}'"
                )

            mapa = {
                "A": dados["opcao_a"],
                "B": dados["opcao_b"],
                "C": dados["opcao_c"],
            }

            texto_final = (
                f"A resposta correta é a alternativa {correta}. "
                f"{mapa[correta]}. "
                "Comente sua pontuação."
            )
            timer_final = "RESPOSTA"

        audio_final = os.path.join(
            pasta_q,
            f"Q{numero:02d}_RESPOSTA.mp3"
        )
        tts_salvar(texto_final, audio_final)

        dur_final = max(
            float(TEMPO_RESPOSTA),
            duracao_audio(audio_final) + 0.25
        )

        frame_final = os.path.join(
            pasta_q,
            "08_resposta.png"
        )
        criar_card(
            dados, tema, cor,
            numero=numero,
            total=total,
            revelar=True,
            timer_texto=timer_final
        ).save(frame_final)

        clip_final = os.path.join(
            pasta_q,
            "08_resposta.mp4"
        )
        criar_clipe_imagem(
            frame_final,
            dur_final,
            clip_final,
            audio=audio_final
        )
        segmentos_q.append(clip_final)

        # ====================================================
        # D) FECHA A PERGUNTA ANTES DA PRÓXIMA
        # ====================================================
        clip_q_final = os.path.join(
            pasta_video,
            f"PERGUNTA_{numero:02d}.mp4"
        )
        concat_q = os.path.join(
            pasta_q,
            "concat_pergunta.txt"
        )

        juntar_clipes(
            segmentos_q,
            clip_q_final,
            concat_q
        )

        if (
            not os.path.exists(clip_q_final)
            or os.path.getsize(clip_q_final) < 10000
        ):
            raise RuntimeError(
                f"Falha ao fechar a pergunta {numero}"
            )

        clips_perguntas.append(
            (numero, clip_q_final)
        )

        print(
            f"   ✅ pergunta {numero}/{total} "
            "fechada e sincronizada"
        )

    # Ordem final sempre 1..total
    clips_perguntas = sorted(
        clips_perguntas,
        key=lambda x: x[0]
    )

    ordem_final = [
        n for n, _ in clips_perguntas
    ]
    esperado = list(range(1,total+1))

    if ordem_final != esperado:
        raise RuntimeError(
            f"Ordem final incorreta. "
            f"Esperado {esperado}; obtido {ordem_final}"
        )

    lista_final = [
        p for _, p in clips_perguntas
    ]

    nome_limpo = re.sub(
        r"[^a-zA-Z0-9À-ÿ _-]",
        "",
        tema
    ).strip().replace(" ","_")

    saida = os.path.join(
        PASTA_DRIVE,
        f"{video_id:02d}_{nome_limpo}.mp4"
    )

    concat_final = os.path.join(
        pasta_video,
        "concat_video.txt"
    )

    juntar_clipes(
        lista_final,
        saida,
        concat_final
    )

    videos_gerados.append(saida)
    print("✅ VÍDEO SALVO:", saida)

print("")
print("🎉 PRODUÇÃO FINALIZADA")
print(
    f"{len(videos_gerados)} vídeos gerados em:"
)
print(PASTA_DRIVE)

for p in videos_gerados:
    print(" -", os.path.basename(p))


# ============================================================
# ENVIAR RESULTADOS PARA O GOOGLE DRIVE
# ============================================================

if not videos_gerados:
    print("⚠ Nenhum vídeo para enviar.")
elif not OUTPUT_PARENT_ID:
    print(
        "⚠ GOOGLE_DRIVE_OUTPUT_FOLDER_ID não configurado. "
        "Os vídeos ficaram apenas como Artifact do GitHub."
    )
else:
    pasta_remota = criar_pasta_drive(
        f"VIDEOS_GITHUB_{CARIMBO}",
        OUTPUT_PARENT_ID
    )
    pasta_remota_id = pasta_remota["id"]
    print("📤 Enviando para o Drive:", pasta_remota["name"])

    for video in videos_gerados:
        arq = enviar_arquivo_drive(video, pasta_remota_id)
        print("✅ DRIVE:", arq.get("name"), arq.get("webViewLink", arq.get("id")))

    print("🎉 Upload para o Google Drive concluído.")
