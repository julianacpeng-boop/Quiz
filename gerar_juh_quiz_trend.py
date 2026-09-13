import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from campanha import PADRAO, CAMPANHA, QUIZZES

W = 1080
H = 1920
FPS = 30
TEMPO_ESCOLHA = 3
PAUSA_RESPOSTA = 0.55
AUDIO_HZ = 48000
AUDIO_CHANNELS = 2
VOZ = "pt-BR-AntonioNeural"
VELOCIDADE_VOZ = "+10%"

PASTA_SAIDA = Path("output")
PASTA_TMP = Path("_tmp_juh_quiz_trend")


def hex_rgb(cor):
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i+2], 16) for i in (0, 2, 4))


NAVY = hex_rgb(PADRAO["azul_escuro"])
BLUE = hex_rgb(PADRAO["azul_neon"])
CYAN = hex_rgb(PADRAO["ciano"])
WHITE = hex_rgb(PADRAO["branco"])
YELLOW = hex_rgb(PADRAO["amarelo"])
ORANGE = hex_rgb(PADRAO["laranja"])
PINK = hex_rgb(PADRAO["rosa"])
PURPLE = hex_rgb(PADRAO["roxo"])
GREEN = hex_rgb(PADRAO["verde"])


def slug(texto):
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower() or "quiz"


def achar_fonte(*candidatos):
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return None


FONT_BOLD = achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
)
FONT_REG = achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
)


def fonte(tamanho, bold=True):
    path = FONT_BOLD if bold else FONT_REG
    if path:
        return ImageFont.truetype(path, int(tamanho))
    return ImageFont.load_default()


def lerp(a, b, t):
    return int(a + (b - a) * t)


def fundo_neon():
    img = Image.new("RGB", (W, H), NAVY)
    px = img.load()
    topo = (2, 11, 48)
    meio = NAVY
    baixo = (7, 19, 78)
    for y in range(H):
        if y < H // 2:
            t = y / (H / 2)
            cor = tuple(lerp(topo[i], meio[i], t) for i in range(3))
        else:
            t = (y - H / 2) / (H / 2)
            cor = tuple(lerp(meio[i], baixo[i], t) for i in range(3))
        for x in range(W):
            px[x, y] = cor

    # Halo neon suave.
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(halo)
    d.ellipse([50, -180, W - 50, 630], outline=CYAN + (150,), width=28)
    d.ellipse([85, -145, W - 85, 595], outline=PURPLE + (110,), width=18)
    halo = halo.filter(ImageFilter.GaussianBlur(18))
    img = Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB")
    return img


def texto_central(draw, y, texto, fnt, fill, x0=0, x1=W):
    bb = draw.textbbox((0, 0), str(texto), font=fnt)
    tw = bb[2] - bb[0]
    x = x0 + ((x1 - x0) - tw) / 2
    draw.text((x, y), str(texto), font=fnt, fill=fill)


def wrap(draw, texto, fnt, max_width):
    palavras = str(texto).split()
    linhas, atual = [], ""
    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        bb = draw.textbbox((0, 0), teste, font=fnt)
        if bb[2] - bb[0] <= max_width:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def fonte_ajustada(draw, texto, max_width, max_linhas, inicio=54, minimo=28):
    for tamanho in range(inicio, minimo - 1, -2):
        f = fonte(tamanho, True)
        linhas = wrap(draw, texto, f, max_width)
        if len(linhas) <= max_linhas:
            return f, linhas
    f = fonte(minimo, True)
    return f, wrap(draw, texto, f, max_width)


def multiline_central(draw, texto, y, max_width, fill, inicio=54, max_linhas=4, line_gap=10):
    fnt, linhas = fonte_ajustada(draw, texto, max_width, max_linhas, inicio=inicio)
    bb = draw.textbbox((0, 0), "Ag", font=fnt)
    lh = bb[3] - bb[1]
    yy = y
    for linha in linhas:
        texto_central(draw, yy, linha, fnt, fill, 100, W - 100)
        yy += lh + line_gap
    return yy


def cabecalho(img, draw, tema, numero=None):
    # Marca
    logo = [85, 72, 470, 185]
    draw.rounded_rectangle([logo[0] + 8, logo[1] + 10, logo[2] + 8, logo[3] + 10],
                           radius=34, fill=(0, 0, 0, 90))
    draw.rounded_rectangle(logo, radius=34, fill=(8, 31, 112), outline=CYAN, width=5)

    draw.text((118, 92), "Juh", font=fonte(50, True), fill=WHITE)
    draw.text((270, 92), "Quiz", font=fonte(50, True), fill=YELLOW)

    # ponto neon
    draw.ellipse([430, 105, 448, 123], fill=PINK)

    # hashtag
    hashtag = CAMPANHA.get("hashtag", "").strip()
    if hashtag:
        f = fonte(28, True)
        bb = draw.textbbox((0, 0), hashtag, font=f)
        w = bb[2] - bb[0]
        x1 = W - 70
        x0 = max(500, x1 - w - 44)
        draw.rounded_rectangle([x0, 84, x1, 145], radius=25, fill=(255, 255, 255), outline=PURPLE, width=3)
        texto_central(draw, 99, hashtag, f, NAVY, x0, x1)

    # Tema
    tema_txt = str(tema).upper()
    f_tema, linhas = fonte_ajustada(draw, tema_txt, 760, 1, inicio=34, minimo=24)
    bb = draw.textbbox((0, 0), linhas[0], font=f_tema)
    tw = bb[2] - bb[0]
    x0 = (W - tw) / 2 - 32
    x1 = (W + tw) / 2 + 32
    draw.rounded_rectangle([x0, 225, x1, 296], radius=30, fill=(12, 38, 120), outline=BLUE, width=4)
    texto_central(draw, 243, linhas[0], f_tema, WHITE, x0, x1)

    if numero is not None:
        draw.rounded_rectangle([860, 225, 1002, 296], radius=28, fill=YELLOW)
        texto_central(draw, 242, f"{numero}/5", fonte(32, True), NAVY, 860, 1002)


def render_intro():
    img = fundo_neon()
    draw = ImageDraw.Draw(img)

    cabecalho(img, draw, CAMPANHA.get("titulo", "DESAFIO"))

    # Card central
    card = [75, 390, W - 75, 1500]
    draw.rounded_rectangle([card[0] + 15, card[1] + 18, card[2] + 15, card[3] + 18],
                           radius=52, fill=(0, 0, 0))
    draw.rounded_rectangle(card, radius=52, fill=(8, 29, 100), outline=CYAN, width=7)

    titulo = CAMPANHA.get("tarefa_chamada") or CAMPANHA.get("gancho") or CAMPANHA.get("titulo")
    multiline_central(draw, titulo, 470, 780, WHITE, inicio=65, max_linhas=4, line_gap=16)

    intro_tipo = CAMPANHA.get("intro_tipo", "texto")
    p1 = Path(CAMPANHA.get("intro_imagem_1", "") or "")
    p2 = Path(CAMPANHA.get("intro_imagem_2", "") or "")

    if intro_tipo == "antes_depois" and p1.is_file() and p2.is_file():
        def colar(path, caixa):
            im = Image.open(path).convert("RGB")
            x0, y0, x1, y1 = caixa
            bw, bh = x1 - x0, y1 - y0
            escala = max(bw / im.width, bh / im.height)
            novo = im.resize((int(im.width * escala), int(im.height * escala)))
            left = max(0, (novo.width - bw) // 2)
            top = max(0, (novo.height - bh) // 2)
            crop = novo.crop((left, top, left + bw, top + bh))
            img.paste(crop, (x0, y0))
            draw.rounded_rectangle(caixa, radius=32, outline=WHITE, width=5)

        colar(p1, [130, 720, 505, 1270])
        colar(p2, [575, 720, 950, 1270])
        texto_central(draw, 1300, "ANTES", fonte(30, True), CYAN, 130, 505)
        texto_central(draw, 1300, "DEPOIS", fonte(30, True), YELLOW, 575, 950)
    else:
        # Elementos graficos da marca
        draw.ellipse([185, 760, 405, 980], outline=CYAN, width=14)
        texto_central(draw, 798, "?", fonte(110, True), CYAN, 185, 405)
        draw.polygon([(700, 770), (885, 870), (700, 970)], fill=WHITE)
        draw.ellipse([635, 735, 935, 1035], outline=PURPLE, width=12)

    gancho = CAMPANHA.get("gancho", "")
    if gancho:
        multiline_central(draw, gancho, 1370, 780, YELLOW, inicio=43, max_linhas=2, line_gap=10)

    texto_central(draw, 1665, "DESAFIO EM 5 PERGUNTAS", fonte(34, True), WHITE)
    return img


def render_frame(tema, pergunta, numero, estado, timer=None):
    img = fundo_neon()
    draw = ImageDraw.Draw(img)
    cabecalho(img, draw, tema, numero)

    # card principal branco com borda neon
    card = [55, 350, W - 55, 1640]
    draw.rounded_rectangle([card[0] + 14, card[1] + 18, card[2] + 14, card[3] + 18],
                           radius=50, fill=(1, 7, 35))
    draw.rounded_rectangle(card, radius=50, fill=WHITE, outline=CYAN, width=7)

    # Gancho
    gancho = CAMPANHA.get("gancho", "VOCE ACERTA?")
    draw.rounded_rectangle([165, 392, W - 165, 468], radius=30, fill=NAVY, outline=PURPLE, width=4)
    texto_central(draw, 412, gancho, fonte(29, True), YELLOW, 165, W - 165)

    # pergunta
    y_after = multiline_central(draw, pergunta["pergunta"], 525, 800, NAVY, inicio=52, max_linhas=4, line_gap=12)

    timer_y = max(790, y_after + 30)
    if estado == "reading":
        timer_txt = "..."
        legenda = "OUCA A PERGUNTA"
    elif estado == "countdown":
        timer_txt = str(timer)
        legenda = "RESPONDA AGORA"
    else:
        timer_txt = "OK"
        legenda = "RESPOSTA"

    draw.ellipse([W/2 - 72, timer_y, W/2 + 72, timer_y + 144], fill=NAVY, outline=CYAN, width=7)
    texto_central(draw, timer_y + 39, timer_txt, fonte(45, True), WHITE, W/2 - 72, W/2 + 72)
    texto_central(draw, timer_y + 155, legenda, fonte(25, True), PURPLE)

    # alternativas
    alt_top = timer_y + 220
    letras = ["A", "B", "C"]
    cores = [CYAN, PURPLE, YELLOW]

    for i, alt in enumerate(pergunta["alternativas"]):
        yy = alt_top + i * 145
        correta = i == int(pergunta["correta"])

        if estado == "answer" and correta:
            bg = (221, 255, 235)
            outline = GREEN
            label_bg = GREEN
            txt = NAVY
        elif estado == "answer" and not correta:
            bg = (235, 239, 249)
            outline = (182, 191, 215)
            label_bg = (160, 169, 194)
            txt = (105, 111, 135)
        else:
            bg = (255, 255, 255)
            outline = cores[i]
            label_bg = cores[i]
            txt = NAVY

        box = [130, yy, W - 130, yy + 112]
        draw.rounded_rectangle(box, radius=28, fill=bg, outline=outline, width=6)
        draw.rounded_rectangle([155, yy + 20, 245, yy + 92], radius=20, fill=label_bg)

        letra = "OK" if estado == "answer" and correta else letras[i]
        texto_central(draw, yy + 38, letra, fonte(28, True), NAVY if label_bg == YELLOW else WHITE, 155, 245)

        f_alt, linhas = fonte_ajustada(draw, alt, 610, 2, inicio=35, minimo=25)
        bb = draw.textbbox((0, 0), "Ag", font=f_alt)
        lh = bb[3] - bb[1]
        ytxt = yy + (112 - (len(linhas) * lh + (len(linhas)-1)*4)) / 2 - 3
        for linha in linhas:
            draw.text((280, ytxt), linha, font=f_alt, fill=txt)
            ytxt += lh + 4

    # progresso
    x0, x1 = 130, W - 130
    y = 1572
    draw.rounded_rectangle([x0, y, x1, y + 16], radius=8, fill=(213, 219, 236))
    progresso = numero / 5
    draw.rounded_rectangle([x0, y, x0 + int((x1-x0)*progresso), y + 16], radius=8, fill=BLUE)

    return img


def render_final(tema):
    img = fundo_neon()
    draw = ImageDraw.Draw(img)
    cabecalho(img, draw, tema)

    card = [80, 420, W - 80, 1510]
    draw.rounded_rectangle([card[0] + 15, card[1] + 18, card[2] + 15, card[3] + 18],
                           radius=50, fill=(0, 0, 0))
    draw.rounded_rectangle(card, radius=50, fill=(8, 29, 100), outline=CYAN, width=7)

    texto_central(draw, 535, "FIM DO DESAFIO", fonte(56, True), YELLOW)
    multiline_central(draw, CAMPANHA.get("fechamento", "5/5?"), 690, 760, WHITE, inicio=48, max_linhas=3, line_gap=14)

    for idx, txt in enumerate(["5/5 = INCRIVEL", "4/5 = MANDOU BEM", "3/5 = QUASE LA"]):
        yy = 930 + idx * 135
        draw.rounded_rectangle([230, yy, W - 230, yy + 95], radius=28, fill=WHITE, outline=PURPLE, width=4)
        texto_central(draw, yy + 27, txt, fonte(30, True), NAVY, 230, W - 230)

    texto_central(draw, 1370, CAMPANHA.get("cta", "COMENTE SUA PONTUACAO"), fonte(34, True), CYAN)
    hashtag = CAMPANHA.get("hashtag", "")
    if hashtag:
        texto_central(draw, 1600, hashtag, fonte(36, True), YELLOW)

    texto_central(draw, 1730, "@juhquiz", fonte(30, True), WHITE)
    return img


def executar(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        print(p.stderr[-6000:])
        raise RuntimeError("Comando retornou erro.")
    return p


def tts_salvar(texto, caminho):
    p = subprocess.run(
        [
            "edge-tts",
            "--voice", VOZ,
            "--rate", VELOCIDADE_VOZ,
            "--text", re.sub(r"\s+", " ", str(texto)).strip(),
            "--write-media", str(caminho),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if p.returncode != 0:
        print(p.stderr)
        raise RuntimeError("Falha no Edge TTS.")


def duracao_audio(caminho):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(caminho),
    ]
    return float(subprocess.check_output(cmd, text=True).strip())


def criar_beep(caminho, frequencia):
    executar([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={frequencia}:duration=0.14",
        "-af", "volume=0.50,apad=pad_dur=1",
        "-t", "1.0",
        "-c:a", "aac", "-b:a", "160k",
        "-ar", str(AUDIO_HZ), "-ac", str(AUDIO_CHANNELS),
        str(caminho),
    ])


def criar_clipe(img_path, duracao, saida, audio=None):
    if audio:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img_path),
            "-i", str(audio),
            "-t", f"{float(duracao):.3f}",
            "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-af", f"aresample={AUDIO_HZ}:async=1:first_pts=0,apad",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-ar", str(AUDIO_HZ), "-ac", str(AUDIO_CHANNELS),
            "-shortest",
            "-movflags", "+faststart",
            str(saida),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img_path),
            "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_HZ}",
            "-t", f"{float(duracao):.3f}",
            "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-ar", str(AUDIO_HZ), "-ac", str(AUDIO_CHANNELS),
            "-shortest",
            "-movflags", "+faststart",
            str(saida),
        ]
    executar(cmd)


def juntar_clipes(lista, saida, concat_path):
    with open(concat_path, "w", encoding="utf-8") as f:
        for p in lista:
            caminho = str(Path(p).resolve()).replace("'", "'\\''")
            f.write(f"file '{caminho}'\n")

    executar([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(Path(concat_path).resolve()),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-ar", str(AUDIO_HZ), "-ac", str(AUDIO_CHANNELS),
        "-movflags", "+faststart",
        str(saida),
    ])


def validar():
    if CAMPANHA.get("modo") not in ("normal", "hashtag", "tarefa"):
        raise ValueError("CAMPANHA['modo'] deve ser normal, hashtag ou tarefa.")

    if not QUIZZES:
        raise ValueError("QUIZZES esta vazio.")

    vistas = set()
    for tema, perguntas in QUIZZES.items():
        if len(perguntas) != 5:
            raise ValueError(f"Tema '{tema}' precisa ter exatamente 5 perguntas.")
        for q in perguntas:
            if len(q.get("alternativas", [])) != 3:
                raise ValueError(f"Pergunta precisa de 3 alternativas: {q.get('pergunta')}")
            if int(q.get("correta", -1)) not in (0, 1, 2):
                raise ValueError(f"Resposta correta invalida: {q.get('pergunta')}")
            texto = str(q.get("pergunta", "")).strip()
            if not texto:
                raise ValueError("Existe pergunta vazia.")
            if texto in vistas:
                raise ValueError(f"Pergunta repetida: {texto}")
            vistas.add(texto)


def main():
    validar()

    if PASTA_TMP.exists():
        shutil.rmtree(PASTA_TMP)
    PASTA_TMP.mkdir(parents=True)
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    beep = PASTA_TMP / "beep.m4a"
    beep_final = PASTA_TMP / "beep_final.m4a"
    criar_beep(beep, 930)
    criar_beep(beep_final, 1250)

    for vid_num, (tema, perguntas) in enumerate(QUIZZES.items(), start=1):
        pasta = PASTA_TMP / f"{vid_num:02d}_{slug(tema)}"
        pasta.mkdir(parents=True)
        segmentos = []

        if CAMPANHA.get("modo") == "tarefa" and CAMPANHA.get("intro_tipo") != "nenhuma":
            intro_png = pasta / "intro.png"
            intro_mp4 = pasta / "intro.mp4"
            render_intro().save(intro_png)
            criar_clipe(intro_png, 3.2, intro_mp4)
            segmentos.append(intro_mp4)

        for idx, q in enumerate(perguntas, start=1):
            qdir = pasta / f"q{idx}"
            qdir.mkdir()

            # pergunta
            audio_q = qdir / "pergunta.mp3"
            tts_salvar(q["pergunta"], audio_q)
            dur_q = duracao_audio(audio_q) + 0.15
            png_q = qdir / "pergunta.png"
            mp4_q = qdir / "pergunta.mp4"
            render_frame(tema, q, idx, "reading").save(png_q)
            criar_clipe(png_q, dur_q, mp4_q, audio_q)
            segmentos.append(mp4_q)

            # contagem
            for n in range(TEMPO_ESCOLHA, 0, -1):
                png_t = qdir / f"timer_{n}.png"
                mp4_t = qdir / f"timer_{n}.mp4"
                render_frame(tema, q, idx, "countdown", n).save(png_t)
                criar_clipe(png_t, 1.0, mp4_t, beep_final if n == 1 else beep)
                segmentos.append(mp4_t)

            # resposta
            correta = int(q["correta"])
            resposta = q["alternativas"][correta]
            audio_r = qdir / "resposta.mp3"
            tts_salvar(resposta, audio_r)
            dur_r = duracao_audio(audio_r) + PAUSA_RESPOSTA
            png_r = qdir / "resposta.png"
            mp4_r = qdir / "resposta.mp4"
            render_frame(tema, q, idx, "answer").save(png_r)
            criar_clipe(png_r, dur_r, mp4_r, audio_r)
            segmentos.append(mp4_r)

        final_png = pasta / "final.png"
        final_mp4 = pasta / "final.mp4"
        render_final(tema).save(final_png)
        criar_clipe(final_png, 2.5, final_mp4)
        segmentos.append(final_mp4)

        saida = PASTA_SAIDA / f"{vid_num:02d}_{slug(tema)}.mp4"
        juntar_clipes(segmentos, saida, pasta / "concat.txt")
        print(f"Gerado: {saida}", flush=True)

    print("Finalizado.", flush=True)


if __name__ == "__main__":
    main()
