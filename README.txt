JUH QUIZ — FOLHA ANIMADA COM MÃO E MARCA-TEXTO
=================================================

ARQUIVOS
--------
gerar_videos_folha_juh.py
dados_quiz.py
requirements.txt

assets/
  fundo_folha_juh_quiz.png
  mao_marca_texto.png

.github/workflows/
  gerar-videos-folha-juh.yml


COMO FUNCIONA
-------------
- O tema é escrito na faixa azul.
- Todas as perguntas ficam impressas na folha.
- A voz masculina lê SOMENTE a pergunta.
- Enquanto a pergunta é lida, a mão se move e o marca-texto verde risca a pergunta.
- Depois acontece a contagem 3, 2, 1.
- A alternativa correta é destacada.
- A voz lê SOMENTE a resposta correta.
- A mão passa para a pergunta seguinte.


COMO RODAR NO GITHUB
--------------------
1. Envie todos os arquivos mantendo as pastas.
2. Vá em Actions.
3. Abra "Gerar Juh Quiz Folha Animada".
4. Clique em Run workflow.
5. Baixe o Artifact JUH-QUIZ-FOLHA-...


PARA TESTAR SÓ O VISUAL
-----------------------
python gerar_videos_folha_juh.py --preview

Ele cria:
preview_folha_limpa.png
preview_mao_riscando.png
preview_resposta.png


DADOS DAS PERGUNTAS
-------------------
Edite somente dados_quiz.py.

correta:
0 = A
1 = B
2 = C

O modelo suporta até 6 perguntas por tema.
