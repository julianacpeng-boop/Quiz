# ============================================================
# JUH QUIZ TREND - CONFIGURACAO RAPIDA
# Edite principalmente este arquivo quando surgir uma nova
# tarefa de criador, trend ou hashtag.
# ============================================================

PADRAO = {
    "marca": "JUH QUIZ",

    # Paleta inspirada na identidade visual enviada:
    "azul_escuro": "#06185B",
    "azul_neon": "#1377FF",
    "ciano": "#18E7FF",
    "branco": "#F7F9FF",
    "amarelo": "#FFC51B",
    "laranja": "#FF9C00",
    "rosa": "#F51BCB",
    "roxo": "#7A2CFF",
    "verde": "#19C96B",
}

CAMPANHA = {
    # "normal" = quiz comum
    # "hashtag" = destaca titulo + hashtag
    # "tarefa" = cria abertura especial antes do quiz
    "modo": "tarefa",

    "titulo": "DE VOLTA AOS ANOS 80",
    "hashtag": "#Anos80",
    "gancho": "VOCE MANJA DOS ANOS 80?",

    # Aparece na abertura quando modo = "tarefa"
    "tarefa_chamada": "EU HOJE X EU NOS ANOS 80",

    # "texto" = abertura apenas com texto
    # "antes_depois" = usa duas imagens, se existirem
    # "nenhuma" = pula a abertura especial
    "intro_tipo": "texto",

    # Para usar antes/depois, crie uma pasta assets e informe:
    # "assets/antes.png" e "assets/depois.png"
    "intro_imagem_1": "",
    "intro_imagem_2": "",

    "fechamento": "5/5? VOCE PERTENCE AOS ANOS 80!",
    "cta": "COMENTE SUA PONTUACAO",
}

# ============================================================
# PERGUNTAS
# correta: 0=A, 1=B, 2=C
# Cada tema precisa ter exatamente 5 perguntas.
# Pode acrescentar varios temas: cada tema gera um MP4.
# ============================================================

QUIZZES = {
    "Anos 80": [
        {
            "pergunta": "Qual aparelho portatil ficou famoso por permitir ouvir fitas cassete?",
            "alternativas": ["Walkman", "Discman", "MP3 player"],
            "correta": 0,
        },
        {
            "pergunta": "Qual formato era muito usado para assistir filmes em casa nos anos 80?",
            "alternativas": ["Blu-ray", "VHS", "Streaming"],
            "correta": 1,
        },
        {
            "pergunta": "Qual acessorio combinava com o visual fitness colorido dos anos 80?",
            "alternativas": ["Cartola", "Gravata borboleta", "Polaina"],
            "correta": 2,
        },
        {
            "pergunta": "Qual videogame da Nintendo foi lancado no Japao em 1983?",
            "alternativas": ["Famicom", "Nintendo 64", "GameCube"],
            "correta": 0,
        },
        {
            "pergunta": "Qual genero musical ganhou enorme espaco na MTV durante os anos 80?",
            "alternativas": ["Opera barroca", "Pop", "Samba-enredo apenas"],
            "correta": 1,
        },
    ],
}
