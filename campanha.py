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

    "gancho": "VOCÊ SABE QUANTO CUSTA O CINEMA ESSA SEMANA?",

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
    "Semana do Cinema": [
        {
            "pergunta": "Até que dia acontece a Semana do Cinema de setembro de 2026?",
            "alternativas": [
                "16 de setembro",
                "20 de setembro",
                "30 de setembro"
            ],
            "correta": 0
        },

        {
            "pergunta": "Quanto custa o ingresso promocional nas sessões tradicionais antes das 17h?",
            "alternativas": [
                "R$ 8",
                "R$ 10",
                "R$ 15"
            ],
            "correta": 1
        },

        {
            "pergunta": "Qual é o valor promocional geral para sessões tradicionais depois das 17h?",
            "alternativas": [
                "R$ 10",
                "R$ 15",
                "R$ 12"
            ],
            "correta": 2
        },

        {
            "pergunta": "Qual destes cinemas de João Pessoa participa da Semana do Cinema?",
            "alternativas": [
                "Centerplex Mag Shopping",
                "Cinema Municipal de Sousa",
                "Cine Teatro Pax"
            ],
            "correta": 0
        },

        {
            "pergunta": "Em que ano a Semana do Cinema foi criada?",
            "alternativas": [
                "2020",
                "2024",
                "2022"
            ],
            "correta": 2
        }
    ]
}
