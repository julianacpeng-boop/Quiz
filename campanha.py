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
    "modo": "tarefa",

    "titulo": "SEMANA DO CINEMA",
    "hashtag": "#SemanaDoCinema",

    "gancho": "VOCÊ SABE TUDO SOBRE A SEMANA DO CINEMA?",

    "tarefa_chamada": "CINEMA BARATINHO EM JOÃO PESSOA!",

    "intro_tipo": "antes_depois",

    "intro_imagem_1": "assets/antes.png",
    "intro_imagem_2": "assets/depois.png",

    "fechamento": "5/5? ENTÃO VOCÊ JÁ PODE MARCAR O CINEMINHA!",
    "cta": "COMENTE QUANTAS VOCÊ ACERTOU",
}

# ============================================================
# PERGUNTAS
# correta: 0=A, 1=B, 2=C
# Cada tema precisa ter exatamente 5 perguntas.
# Pode acrescentar varios temas: cada tema gera um MP4.
# ============================================================

QUIZZES = {
    "Cabelo Curto": [
        {
            "pergunta": "Qual corte costuma ficar na altura do queixo?",
            "alternativas": ["Bob", "Longo em camadas", "Rabo de cavalo"],
            "correta": 0,
        },
        {
            "pergunta": "Qual destes pode ajudar a dar mais textura ao cabelo?",
            "alternativas": ["Cimento", "Pomada modeladora", "Detergente"],
            "correta": 1,
        },
        {
            "pergunta": "Qual corte geralmente deixa a nuca mais aparente?",
            "alternativas": ["Trança longa", "Cabelo até a cintura", "Pixie cut"],
            "correta": 2,
        },
        {
            "pergunta": "Qual acessório pode valorizar penteados em cabelo curto?",
            "alternativas": ["Presilha", "Capacete de obra", "Chave inglesa"],
            "correta": 0,
        },
        {
            "pergunta": "Qual profissional é o mais indicado para orientar um novo corte?",
            "alternativas": ["Dentista", "Cabeleireiro", "Mecânico"],
            "correta": 1,
        },
    ],
}
