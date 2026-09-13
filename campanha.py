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
CAMPANHA = {
    "modo": "tarefa",

    "titulo": "BORA DE CABELO CURTO?",
    "hashtag": "#DesafioDoCorte",

    "gancho": "VOCÊ ENTENDE DE CABELO?",
    "tarefa_chamada": "SERÁ QUE EU FICARIA BEM DE CABELO CURTO?",

    "intro_tipo": "antes_depois",

    "intro_imagem_1": "assets/antes.png",
    "intro_imagem_2": "assets/depois.png",

    "fechamento": "E AÍ: EU CORTO OU NÃO?",
    "cta": "COMENTE SE VOCÊ CORTARIA",
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
