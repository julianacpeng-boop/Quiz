import math
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from dados_quiz import QUIZZES

# ============================================================
# CONFIGURAÇÃO
# ============================================================

W = 1080
H = 1920
FPS = 30
ANIM_FPS = 20

VOZ = "pt-BR-AntonioNeural"
VELOCIDADE_VOZ = "+10%"

AUDIO_HZ = 48000
AUDIO_CHANNELS = 2

TEMPO_CONTAGEM = 3
PAUSA_DEPOIS_PERGUNTA = 0.10
PAUSA_DEPOIS_RESPOSTA = 0.50

FUNDO = Path("assets/fundo_folha_juh_quiz.png")
MAO = Path("assets/mao_marca_texto_suave.png")

FUSO = ZoneInfo("America/Fortaleza")
DATA_DO_DIA = datetime.now(FUSO).strftime("%Y-%m-%d")

PASTA_RAIZ = Path("output_folha_juh")
PASTA_TMP = Path("_tmp_folha_juh")
PASTA_SAIDA = PASTA_RAIZ / DATA_DO_DIA

AZUL = (13, 88, 187)
AZUL_ESCURO = (12, 39, 94)
PRETO = (20, 20, 24)
VERDE_MARCA = (166, 244, 79, 115)
VERDE_RESPOSTA = (76, 180, 61, 150)
CINZA = (88, 94, 108)
BRANCO = (255, 255, 255)

# ============================================================
# UTILIDADES
# ============================================================

def slug(texto):
    txt = unicodedata.normalize("NFKD", str(texto))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return txt or "quiz"


def executar(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        print(p.stdout)
        print(p.stderr)
        raise RuntimeError("Falha ao executar comando.")
    return p


def fonte(tamanho, bold=False):
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",

        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]

    for caminho in candidatos:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except Exception:
            pass

    return ImageFont.load_default()


def wrap_text(draw, texto, fnt, largura):
    palavras = str(texto).split()

    if not palavras:
        return [""]

    linhas = []
    linha = palavras[0]

    for palavra in palavras[1:]:
        teste = linha + " " + palavra
        bb = draw.textbbox((0, 0), teste, font=fnt)

        if bb[2] - bb[0] <= largura:
            linha = teste
        else:
            linhas.append(linha)
            linha = palavra

    linhas.append(linha)
    return linhas


def fit_lines(draw, texto, largura, altura, max_size, min_size, max_lines, bold=True):
    for tamanho in range(max_size, min_size - 1, -2):
        fnt = fonte(tamanho, bold=bold)
        linhas = wrap_text(draw, texto, fnt, largura)

        if len(linhas) > max_lines:
            continue

        bb = draw.textbbox((0, 0), "Ag", font=fnt)
        line_h = bb[3] - bb[1]
        total_h = len(linhas) * line_h + (len(linhas) - 1) * 5

        if total_h <= altura:
            return fnt, linhas, line_h

    fnt = fonte(min_size, bold=bold)
    linhas = wrap_text(draw, texto, fnt, largura)[:max_lines]
    bb = draw.textbbox((0, 0), "Ag", font=fnt)
    return fnt, linhas, bb[3] - bb[1]


def fundo_base():
    if not FUNDO.exists():
        raise FileNotFoundError(
            f"Fundo não encontrado: {FUNDO}. "
            "Envie assets/fundo_folha_juh_quiz.png ao GitHub."
        )

    img = Image.open(FUNDO).convert("RGB")
    resampling = getattr(Image, "Resampling", Image)

    return ImageOps.fit(
        img,
        (W, H),
        method=resampling.LANCZOS,
        centering=(0.5, 0.5)
    )


def carregar_mao():
    if not MAO.exists():
        raise FileNotFoundError(
            f"Mão não encontrada: {MAO}. "
            "Envie assets/mao_marca_texto_suave.png ao GitHub."
        )

    mao = Image.open(MAO).convert("RGBA")

    # Aumenta e alonga o braço para a extremidade ficar fora do quadro.
    largura = 620
    altura = 1500

    resampling = getattr(Image, "Resampling", Image)
    mao = mao.resize((largura, altura), resampling.LANCZOS)

    # Suaviza apenas o final do braço.
    alpha = mao.getchannel("A")
    w, h = mao.size
    px = alpha.load()
    fade_start = int(h * 0.86)

    for y in range(fade_start, h):
        t = (y - fade_start) / max(1, h - fade_start)
        fator = max(0.0, 1.0 - t)
        for x in range(w):
            px[x, y] = int(px[x, y] * fator)

    alpha = alpha.filter(ImageFilter.GaussianBlur(1.5))
    mao.putalpha(alpha)
    return mao


def validar_tema(tema, perguntas):
    if not perguntas:
        raise ValueError(f'O tema "{tema}" está sem perguntas.')

    if len(perguntas) > 6:
        raise ValueError(
            f'O tema "{tema}" tem {len(perguntas)} perguntas. '
            "Este modelo suporta até 6 perguntas por vídeo."
        )

    for pergunta in perguntas:
        if "pergunta" not in pergunta:
            raise ValueError(f'Pergunta sem texto no tema "{tema}".')

        if len(pergunta.get("alternativas", [])) != 3:
            raise ValueError(
                f'A pergunta "{pergunta["pergunta"]}" precisa ter 3 alternativas.'
            )

        correta = int(pergunta.get("correta", -1))

        if correta not in (0, 1, 2):
            raise ValueError(
                f'A pergunta "{pergunta["pergunta"]}" precisa de correta 0, 1 ou 2.'
            )


# ============================================================
# LAYOUT DA FOLHA
# ============================================================

def parametros_layout(total):
    if total <= 3:
        return {
            "start_y": 535,
            "block_h": 350,
            "q_max": 46,
            "q_min": 34,
            "a_max": 37,
            "a_min": 29,
        }

    if total == 4:
        return {
            "start_y": 520,
            "block_h": 280,
            "q_max": 39,
            "q_min": 30,
            "a_max": 32,
            "a_min": 25,
        }

    if total == 5:
        return {
            "start_y": 505,
            "block_h": 230,
            "q_max": 34,
            "q_min": 27,
            "a_max": 28,
            "a_min": 23,
        }

    return {
        "start_y": 500,
        "block_h": 195,
        "q_max": 31,
        "q_min": 24,
        "a_max": 25,
        "a_min": 20,
    }


def criar_pagina_base(tema, perguntas):
    total = len(perguntas)
    cfg = parametros_layout(total)

    img = fundo_base()
    draw = ImageDraw.Draw(img)

    # Tema dentro da faixa azul
    tema_font, tema_lines, tema_lh = fit_lines(
        draw,
        tema.upper(),
        largura=690,
        altura=70,
        max_size=43,
        min_size=25,
        max_lines=1,
        bold=True
    )

    tema_txt = tema_lines[0] if tema_lines else tema.upper()
    bb = draw.textbbox((0, 0), tema_txt, font=tema_font)
    tw = bb[2] - bb[0]

    draw.text(
        ((W - tw) / 2, 368),
        tema_txt,
        font=tema_font,
        fill=BRANCO
    )

    layouts = []

    x_question = 105
    x_option = 145
    right = 955

    for idx, pergunta in enumerate(perguntas, start=1):
        top = cfg["start_y"] + (idx - 1) * cfg["block_h"]

        q_box_h = 95 if total <= 3 else 78
        q_font, q_lines, q_lh = fit_lines(
            draw,
            f'{idx}) {pergunta["pergunta"]}',
            largura=right - x_question,
            altura=q_box_h,
            max_size=cfg["q_max"],
            min_size=cfg["q_min"],
            max_lines=2,
            bold=True
        )

        q_y = top

        line_boxes = []
        max_width = 0
        cur_y = q_y

        for linha in q_lines:
            draw.text(
                (x_question, cur_y),
                linha,
                font=q_font,
                fill=PRETO
            )

            bb = draw.textbbox(
                (x_question, cur_y),
                linha,
                font=q_font
            )

            line_boxes.append(
                (bb[0], bb[1], bb[2], bb[3])
            )
            max_width = max(max_width, bb[2] - bb[0])
            cur_y += q_lh + 5

        question_bottom = cur_y

        # alternativas
        a_font = fonte(cfg["a_max"], bold=False)

        # se alguma opção for longa, diminui a fonte para todas
        for size in range(cfg["a_max"], cfg["a_min"] - 1, -2):
            test_font = fonte(size, bold=False)
            ok = True
            for letra, alt in zip(("A", "B", "C"), pergunta["alternativas"]):
                texto = f"{letra}) {alt}"
                bb = draw.textbbox((0, 0), texto, font=test_font)
                if bb[2] - bb[0] > right - x_option:
                    ok = False
                    break
            if ok:
                a_font = test_font
                break

        bb_ag = draw.textbbox((0, 0), "Ag", font=a_font)
        a_lh = bb_ag[3] - bb_ag[1]

        option_start_y = question_bottom + 15
        option_boxes = []

        for j, (letra, alt) in enumerate(
            zip(("A", "B", "C"), pergunta["alternativas"])
        ):
            oy = option_start_y + j * (a_lh + 9)
            texto_alt = f"{letra}) {alt}"

            draw.text(
                (x_option, oy),
                texto_alt,
                font=a_font,
                fill=AZUL_ESCURO
            )

            bb = draw.textbbox(
                (x_option, oy),
                texto_alt,
                font=a_font
            )
            option_boxes.append(
                (bb[0], bb[1], bb[2], bb[3])
            )

        # caixa usada para o marca-texto
        min_y = min(b[1] for b in line_boxes)
        max_y = max(b[3] for b in line_boxes)

        highlight_box = (
            x_question - 5,
            min_y + 2,
            min(right, x_question + max_width + 12),
            max_y + 4
        )

        layouts.append({
            "question_box": highlight_box,
            "option_boxes": option_boxes,
            "correcta": int(pergunta["correta"]),
        })

    return img, layouts


# ============================================================
# MARCA-TEXTO + MÃO
# ============================================================

def aplicar_marca_texto(img, box, progresso=1.0):
    progresso = max(0.0, min(1.0, float(progresso)))

    x1, y1, x2, y2 = box
    largura = max(1, int((x2 - x1) * progresso))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.rounded_rectangle(
        [x1, y1, x1 + largura, y2],
        radius=max(5, int((y2 - y1) / 3)),
        fill=VERDE_MARCA
    )

    return Image.alpha_composite(
        img.convert("RGBA"),
        overlay
    ).convert("RGB")


def marcar_resposta(img, option_box):
    x1, y1, x2, y2 = option_box

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.rounded_rectangle(
        [x1 - 10, y1 - 5, x2 + 14, y2 + 7],
        radius=12,
        fill=VERDE_RESPOSTA
    )

    return Image.alpha_composite(
        img.convert("RGBA"),
        overlay
    ).convert("RGB")


def colocar_mao(img, box, progresso):
    mao = carregar_mao()

    x1, y1, x2, y2 = box

    # A ponta do marca-texto acompanha exatamente a pergunta atual.
    tip_x = x1 + int((x2 - x1) * progresso)
    tip_y = int((y1 + y2) / 2)

    tip_offset_x = 42
    tip_offset_y = 38

    hand_x = tip_x - tip_offset_x
    hand_y = tip_y - tip_offset_y

    # Sem travar no rodapé: a mão fica na altura de cada pergunta.
    # O braço alongado sai por baixo da tela, então a extremidade não aparece.
    canvas = img.convert("RGBA")
    canvas.alpha_composite(mao, (hand_x, hand_y))
    return canvas.convert("RGB")


def render_estado(
    pagina_base,
    layouts,
    atual,
    progresso=1.0,
    mostrar_mao=False,
    mostrar_resposta=False
):
    img = pagina_base.copy()

    # Perguntas anteriores permanecem marcadas
    for i in range(atual):
        img = aplicar_marca_texto(
            img,
            layouts[i]["question_box"],
            1.0
        )

    # Pergunta atual vai sendo marcada conforme a mão se move
    img = aplicar_marca_texto(
        img,
        layouts[atual]["question_box"],
        progresso
    )

    # Destaca a alternativa correta após a contagem
    if mostrar_resposta:
        correta = layouts[atual]["correcta"]
        img = marcar_resposta(
            img,
            layouts[atual]["option_boxes"][correta]
        )

    # Mostra a mão durante a leitura da pergunta
    if mostrar_mao:
        img = colocar_mao(
            img,
            layouts[atual]["question_box"],
            progresso
        )

    return img


# ============================================================
# ÁUDIO
# ============================================================

def limpar_tts(texto):
    return re.sub(r"\s+", " ", str(texto)).strip()


def tts_salvar(texto, caminho):
    caminho = Path(caminho)

    if caminho.exists():
        caminho.unlink()

    executar([
        "edge-tts",
        "--voice", VOZ,
        "--rate", VELOCIDADE_VOZ,
        "--text", limpar_tts(texto),
        "--write-media", str(caminho),
    ])

    if not caminho.exists() or caminho.stat().st_size < 500:
        raise RuntimeError(
            f"Áudio não foi criado: {caminho}"
        )


def duracao_audio(caminho):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(caminho)
    ]

    return float(
        subprocess.check_output(
            cmd,
            text=True
        ).strip()
    )


def criar_beep(caminho, frequencia=950):
    executar([
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency={frequencia}:duration=0.14",
        "-af", "volume=0.5,apad=pad_dur=1",
        "-t", "1.0",
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", str(AUDIO_HZ),
        "-ac", str(AUDIO_CHANNELS),
        str(caminho)
    ])


# ============================================================
# VÍDEO
# ============================================================

def criar_clipe_imagem(img_path, duracao, saida, audio=None):
    duracao = float(duracao)

    if audio:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-i", str(audio),
            "-t", f"{duracao:.3f}",
            "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-af", f"aresample={AUDIO_HZ}:async=1:first_pts=0,apad",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "160k",
            "-ar", str(AUDIO_HZ),
            "-ac", str(AUDIO_CHANNELS),
            "-shortest",
            "-movflags", "+faststart",
            str(saida)
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_HZ}",
            "-t", f"{duracao:.3f}",
            "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "160k",
            "-ar", str(AUDIO_HZ),
            "-ac", str(AUDIO_CHANNELS),
            "-shortest",
            "-movflags", "+faststart",
            str(saida)
        ]

    executar(cmd)


def criar_clipe_animado(frame_dir, duracao, audio, saida):
    executar([
        "ffmpeg",
        "-y",
        "-framerate", str(ANIM_FPS),
        "-i", str(frame_dir / "frame_%04d.jpg"),
        "-i", str(audio),
        "-t", f"{duracao:.3f}",
        "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
        "-af", f"aresample={AUDIO_HZ}:async=1:first_pts=0,apad",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", str(AUDIO_HZ),
        "-ac", str(AUDIO_CHANNELS),
        "-shortest",
        "-movflags", "+faststart",
        str(saida)
    ])


def concatenar_clipes(clipes, saida, lista_path):
    lista_path.write_text(
        "\n".join(
            f"file '{Path(c).resolve().as_posix()}'"
            for c in clipes
        ),
        encoding="utf-8"
    )

    executar([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(lista_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(saida)
    ])


# ============================================================
# GERAÇÃO DE UM TEMA
# ============================================================

def gerar_video_tema(tema, perguntas, indice, total_temas):
    validar_tema(tema, perguntas)

    print(
        f"\n🎬 {indice:02d}/{total_temas:02d} — {tema}"
    )

    pagina_base, layouts = criar_pagina_base(
        tema,
        perguntas
    )

    pasta_tema = PASTA_TMP / slug(tema)
    pasta_tema.mkdir(parents=True, exist_ok=True)

    clipes = []

    beep = pasta_tema / "beep.m4a"
    criar_beep(beep)

    for q_idx, pergunta in enumerate(perguntas):
        numero = q_idx + 1
        base_num = numero * 10

        # ----------------------------------------
        # 1. Pergunta falada + mão riscando
        # ----------------------------------------
        audio_pergunta = (
            pasta_tema
            / f"{numero:02d}_pergunta.mp3"
        )

        # NÃO lê as alternativas
        tts_salvar(
            pergunta["pergunta"],
            audio_pergunta
        )

        dur = (
            duracao_audio(audio_pergunta)
            + PAUSA_DEPOIS_PERGUNTA
        )

        frame_dir = (
            pasta_tema
            / f"frames_{numero:02d}"
        )

        if frame_dir.exists():
            shutil.rmtree(frame_dir)

        frame_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        total_frames = max(
            12,
            int(math.ceil(dur * ANIM_FPS))
        )

        for f in range(total_frames):
            progresso = (
                f / max(1, total_frames - 1)
            )

            frame = render_estado(
                pagina_base,
                layouts,
                q_idx,
                progresso=progresso,
                mostrar_mao=True,
                mostrar_resposta=False
            )

            frame.save(
                frame_dir / f"frame_{f:04d}.jpg",
                quality=91
            )

        clip_pergunta = (
            pasta_tema
            / f"{base_num:03d}_pergunta.mp4"
        )

        criar_clipe_animado(
            frame_dir,
            dur,
            audio_pergunta,
            clip_pergunta
        )

        clipes.append(clip_pergunta)

        # ----------------------------------------
        # 2. Contagem 3, 2, 1
        # ----------------------------------------
        for n in (3, 2, 1):
            count_img = render_estado(
                pagina_base,
                layouts,
                q_idx,
                progresso=1.0,
                mostrar_mao=False,
                mostrar_resposta=False
            )

            draw = ImageDraw.Draw(count_img)

            # bolinha de contagem discreta no canto
            cx, cy, r = 940, 470, 48

            draw.ellipse(
                [cx-r, cy-r, cx+r, cy+r],
                fill=AZUL
            )

            txt = str(n)
            fnt = fonte(43, bold=True)

            bb = draw.textbbox(
                (0, 0),
                txt,
                font=fnt
            )

            draw.text(
                (
                    cx - (bb[2]-bb[0])/2,
                    cy - (bb[3]-bb[1])/2 - 3
                ),
                txt,
                font=fnt,
                fill=BRANCO
            )

            count_png = (
                pasta_tema
                / f"{numero:02d}_count_{n}.png"
            )

            count_img.save(count_png)

            count_clip = (
                pasta_tema
                / f"{base_num + (4-n):03d}_count_{n}.mp4"
            )

            criar_clipe_imagem(
                count_png,
                1.0,
                count_clip,
                beep
            )

            clipes.append(count_clip)

        # ----------------------------------------
        # 3. Resposta correta
        # ----------------------------------------
        resposta = pergunta["alternativas"][
            int(pergunta["correta"])
        ]

        answer_img = render_estado(
            pagina_base,
            layouts,
            q_idx,
            progresso=1.0,
            mostrar_mao=False,
            mostrar_resposta=True
        )

        answer_png = (
            pasta_tema
            / f"{numero:02d}_resposta.png"
        )
        answer_img.save(answer_png)

        audio_resposta = (
            pasta_tema
            / f"{numero:02d}_resposta.mp3"
        )

        # fala SOMENTE a correta
        tts_salvar(
            f"A resposta correta é: {resposta}.",
            audio_resposta
        )

        answer_dur = (
            duracao_audio(audio_resposta)
            + PAUSA_DEPOIS_RESPOSTA
        )

        answer_clip = (
            pasta_tema
            / f"{base_num + 4:03d}_resposta.mp4"
        )

        criar_clipe_imagem(
            answer_png,
            answer_dur,
            answer_clip,
            audio_resposta
        )

        clipes.append(answer_clip)

    # --------------------------------------------
    # FINAL CURTO
    # --------------------------------------------
    final_img = pagina_base.copy()

    for i in range(len(perguntas)):
        final_img = aplicar_marca_texto(
            final_img,
            layouts[i]["question_box"],
            1.0
        )

    draw = ImageDraw.Draw(final_img)

    final_text = "QUANTAS VOCÊ ACERTOU?"
    fnt = fonte(35, bold=True)

    bb = draw.textbbox(
        (0, 0),
        final_text,
        font=fnt
    )

    tx = (W - (bb[2]-bb[0])) / 2
    ty = 1765

    draw.rounded_rectangle(
        [tx - 25, ty - 12, tx + (bb[2]-bb[0]) + 25, ty + 52],
        radius=25,
        fill=(255, 255, 255)
    )

    draw.text(
        (tx, ty),
        final_text,
        font=fnt,
        fill=AZUL_ESCURO
    )

    final_png = (
        pasta_tema
        / "final.png"
    )
    final_img.save(final_png)

    final_audio = (
        pasta_tema
        / "final.mp3"
    )

    tts_salvar(
        "Quantas você acertou?",
        final_audio
    )

    final_dur = (
        duracao_audio(final_audio)
        + 0.7
    )

    final_clip = (
        pasta_tema
        / "999_final.mp4"
    )

    criar_clipe_imagem(
        final_png,
        final_dur,
        final_clip,
        final_audio
    )

    clipes.append(final_clip)

    # --------------------------------------------
    # JUNTA TUDO
    # --------------------------------------------
    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    saida = (
        PASTA_SAIDA
        / f"{indice:02d}_{slug(tema)}.mp4"
    )

    concatenar_clipes(
        clipes,
        saida,
        pasta_tema / "concat.txt"
    )

    print(f"✅ {saida}")
    return saida


# ============================================================
# PREVIEW
# ============================================================

def preview():
    if not QUIZZES:
        raise ValueError("QUIZZES está vazio.")

    tema, perguntas = next(
        iter(QUIZZES.items())
    )

    validar_tema(tema, perguntas)

    pagina, layouts = criar_pagina_base(
        tema,
        perguntas
    )

    pagina.save(
        "preview_folha_limpa.png"
    )

    animado = render_estado(
        pagina,
        layouts,
        atual=0,
        progresso=0.65,
        mostrar_mao=True,
        mostrar_resposta=False
    )

    animado.save(
        "preview_mao_riscando.png"
    )

    resposta = render_estado(
        pagina,
        layouts,
        atual=0,
        progresso=1.0,
        mostrar_mao=False,
        mostrar_resposta=True
    )

    resposta.save(
        "preview_resposta.png"
    )

    print("Previews criados:")
    print(" - preview_folha_limpa.png")
    print(" - preview_mao_riscando.png")
    print(" - preview_resposta.png")


# ============================================================
# MAIN
# ============================================================

def main():
    if "--preview" in sys.argv:
        preview()
        return

    if not QUIZZES:
        raise ValueError("QUIZZES está vazio.")

    if PASTA_TMP.exists():
        shutil.rmtree(PASTA_TMP)

    PASTA_TMP.mkdir(
        parents=True,
        exist_ok=True
    )

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    temas = list(
        QUIZZES.items()
    )

    gerados = []

    for indice, (tema, perguntas) in enumerate(
        temas,
        start=1
    ):
        video = gerar_video_tema(
            tema,
            perguntas,
            indice,
            len(temas)
        )

        gerados.append(video)

    print(
        f"\n✅ Finalizado. "
        f"{len(gerados)} vídeo(s) gerado(s)."
    )

    for video in gerados:
        print(" -", video)


if __name__ == "__main__":
    main()
