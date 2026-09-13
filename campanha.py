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
