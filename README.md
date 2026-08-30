# JUH QUIZ — GitHub Actions

Este pacote roda o gerador do **JUH QUIZ V5** no GitHub e envia os vídeos para o Google Drive.

## Arquivos que vão para o GitHub

- `gerar_videos.py` — gerador do vídeo, baseado na V5.
- `requirements.txt` — bibliotecas Python.
- `.github/workflows/gerar-videos.yml` — botão **Run workflow**.
- `.gitignore` — impede credenciais e vídeos temporários de irem para o Git.
- `.env.example` — mostra apenas os nomes das configurações.
- `notebooks/JUH_QUIZ_V5_ORIGINAL.ipynb` — cópia de referência do notebook.

## 1. Coloque tudo no repositório

A estrutura precisa ficar assim:

```text
JUH-QUIZ/
├── .github/
│   └── workflows/
│       └── gerar-videos.yml
├── notebooks/
│   └── JUH_QUIZ_V5_ORIGINAL.ipynb
├── .env.example
├── .gitignore
├── gerar_videos.py
├── requirements.txt
└── README.md
```

## 2. Crie os Secrets no GitHub

No repositório:

**Settings → Secrets and variables → Actions → New repository secret**

Crie:

### `GOOGLE_SERVICE_ACCOUNT_JSON`
Cole o JSON inteiro da conta de serviço do Google Cloud.

Depois compartilhe com o **e-mail da conta de serviço**:
- a planilha do JUH QUIZ;
- a pasta onde estão as imagens;
- a pasta onde os vídeos serão salvos.

> Para Google Drive pessoal, se o Google bloquear upload por quota/propriedade da conta de serviço, use `GOOGLE_AUTHORIZED_USER_JSON` com credencial OAuth de usuário ou uma pasta em Shared Drive.

### `GOOGLE_DRIVE_OUTPUT_FOLDER_ID`
É somente o ID da pasta onde o GitHub deverá criar as pastas `VIDEOS_GITHUB_...`.

Exemplo:

```text
https://drive.google.com/drive/folders/ABC123XYZ
```

Secret:

```text
ABC123XYZ
```

### `SHEET_ID`
É opcional, porque o código já tem a planilha atual como padrão.

## 3. Gerar vídeos

Abra:

**Actions → Gerar videos JUH QUIZ → Run workflow**

No campo `videos`, pode colocar:

```text
1
1-5
61-65
1,3,69,75
ALL
```

O código continua respeitando a coluna `gerar_video = SIM` da aba **Config**.

## 4. Resultado

No final da execução:

1. os MP4 são enviados para uma nova pasta `VIDEOS_GITHUB_AAAAMMDD_HHMM` dentro da pasta do Drive configurada;
2. o GitHub também guarda uma cópia temporária em **Artifacts** por 7 dias.

## Segurança

Nunca coloque no repositório:
- JSON real da conta de serviço;
- `client_secret`;
- `refresh_token`;
- arquivos `.env` com credenciais.

Eles devem existir somente em **GitHub Secrets**.
