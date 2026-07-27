# PROMPT — MayaAssinador 📝✍️

> Cole este prompt inteiro no Claude Code (VS Code). Leia TUDO antes de escrever qualquer linha de código.

---

## 1. QUEM SOU EU E COMO EU TRABALHO

Sou o Jeff, fundador da MayaCorp (fábrica de software). Este é mais um produto do portfólio, e ele DEVE seguir o padrão MayaCorp já consolidado nos outros produtos (Flicsales, MayaSec, PilatesFinal):

- **Backend:** Python + FastAPI + SQLAlchemy + Pydantic v2 + Alembic + PostgreSQL
- **Frontend:** Next.js + TypeScript + Tailwind + shadcn/ui + Zustand + TanStack Query + Zod
- **Auth:** JWT + multi-tenancy via slug na URL (`/[tenant]/...`) — hoje é 1 tenant (um escritório de advocacia), mas a arquitetura nasce multi-tenant
- **Regra de ouro:** CRUD completo em toda feature. NUNCA frontend sem backend, nunca backend sem frontend. Uma fase por vez, uma tela por vez, sempre funcional de ponta a ponta.
- **Fontes:** DM Sans + JetBrains Mono
- **Paleta:** Navy `#1E2D6B` (primária), Indigo `#7C8FFF` (accent), Teal `#1A8F5E` (sucesso), Amber `#F5A623` (alerta), Red `#C94343` (risco), Dark `#0F1729` (sidebar), Gray `#F7F8FC` (background)
- **Template obrigatório de tela CRUD:** Page Header → Toolbar (busca + filtros + botão novo) → Tabela (hover, badges, ações) → Empty state → Paginação → Modal de formulário → Modal de confirmação de delete → Toast

### ⚠️ AMBIENTE — LEIA COM ATENÇÃO

- **NADA de rodar/testar localmente.** Eu edito no Windows com VS Code, mas TODA execução acontece no servidor **prod2** (VM no GCP, usuário `mayacorp22`).
- PostgreSQL **já está rodando** no prod2 (outros produtos usam ele). Criar apenas um novo database `mayaassinador`.
- Nginx e systemd já existem no servidor servindo outros produtos. O MayaAssinador entra como mais um serviço + mais um server block.
- Todos os comandos que você me passar devem ser para eu rodar **via SSH no prod2**.

### 📦 GIT — REPOSITÓRIO OFICIAL

- Repositório (já criado, vazio): `https://github.com/Jeff1984Sor/mayaassinador.git`
- **Tudo vai pra lá.** Logo no início da F1: `git init`, configurar o remote, `.gitignore` completo (venv, node_modules, `.env`, `.next`, `__pycache__`, storage de arquivos) e primeiro push.
- **Fluxo de trabalho:** eu edito no Windows → commit + push pro GitHub → no prod2 faço `git pull` → deploy. O repositório é a ponte entre minha máquina e o servidor. Nunca editar código direto no servidor.
- **Ao final de cada fase:** commit com mensagem descritiva (ex: `F2: configurações do tenant completas`) + push. Me lembre de commitar — faz parte da entrega da fase.
- `.env` NUNCA vai pro repositório — criar um `.env.example` com todas as chaves documentadas.
- O diretório de storage (`/var/mayaassinador/storage/`) fica FORA do repositório.

---

## 2. FASE 0 — INVENTÁRIO DO SERVIDOR (OBRIGATÓRIO ANTES DE QUALQUER CÓDIGO)

Antes de escrever uma linha sequer, me entregue um checklist de comandos para eu rodar no prod2 e te devolver o resultado. O objetivo é descobrir o que JÁ EXISTE e o que precisa ser instalado. Verifique no mínimo:

```bash
python3 --version && pip3 --version
node --version && npm --version
psql --version && sudo -u postgres psql -c "\l"   # databases existentes
nginx -v && ls /etc/nginx/sites-enabled/
systemctl list-units --type=service | grep -E "fastapi|uvicorn|next|node|gunicorn"
libreoffice --version || soffice --version          # conversão DOCX → PDF
which qpdf pdftk gs                                  # ferramentas PDF
df -h                                                # espaço em disco p/ armazenar anexos
free -h                                              # memória (LibreOffice headless consome)
```

**Só depois** de eu te mandar o resultado, você define o que instalar e seguimos. Não assuma nada sobre o servidor.

### Ferramentas do pipeline de documentos (proponha e justifique)

- **`python-docx`** → manipular o .docx: inserir cabeçalho e rodapé
- **LibreOffice headless (`soffice --headless --convert-to pdf`)** → conversão DOCX → PDF com fidelidade (instalar se não existir)
- **`pypdf` + `reportlab`** → carimbar rubrica em todas as páginas e assinatura na última página (overlay de imagem no PDF)
- **`Pillow`** → tratar as imagens de rubrica/assinatura (remover fundo branco → PNG transparente, redimensionar)
- **`qrcode`** → QR code de verificação (ver seção "surpresas")

Se preferir outra combinação, argumente antes. Mas a conversão DOCX→PDF via LibreOffice headless é praticamente obrigatória para manter a formatação do Word.

---

## 3. O PRODUTO — MayaAssinador

SaaS para escritórios de advocacia que transforma documentos Word em PDFs timbrados, rubricados e assinados, prontos para envio.

### Fluxo principal (o coração do sistema)

1. **Upload** — advogado sobe um arquivo `.docx` (drag-and-drop + clique). Validar extensão e tamanho máximo (ex: 20MB).
2. **Anexo original é SALVO** — o .docx original fica guardado intacto no storage, sempre. Nunca sobrescrever.
3. **Cabeçalho** — o sistema insere automaticamente o cabeçalho configurado do tenant (logo + texto do escritório) no início de **cada página** do documento.
4. **Rodapé** — insere o rodapé configurado (texto livre + numeração de página estilo "Página X de Y").
5. **Conversão** — DOCX → PDF via LibreOffice headless.
6. **Rubrica (opcional, escolha no momento do upload)** — toggle "Rubricar todas as páginas". Se ativo, carimba a imagem da rubrica (pequena, canto inferior) em **todas** as páginas.
7. **Assinatura** — na **última página**, aplica a imagem da assinatura do cliente (arquivo de imagem cadastrado nas configurações), em posição configurável (ou padrão: acima de uma linha com o nome).
8. **PDF final** gerado, salvo no storage, vinculado ao documento no banco.
9. **Envio por email (opcional)** — enviar o PDF final como anexo para um ou mais destinatários, com assunto e mensagem editáveis.

### Processamento assíncrono

O pipeline (passos 3–8) pode demorar alguns segundos. Não trave o request:
- Upload retorna imediatamente com o documento em status `processando`
- Pipeline roda em background (BackgroundTasks do FastAPI já resolve para 1 tenant; se argumentar por algo mais robusto, proponha)
- Frontend faz polling (TanStack Query com `refetchInterval`) e mostra o status mudando em tempo real
- Status: `enviado` → `processando` → `pronto` → `enviado_email` | `erro` (com mensagem do erro visível)

### Storage dos arquivos

- Diretório no prod2: `/var/mayaassinador/storage/{tenant}/{documento_id}/`
  - `original.docx` (o anexo que o cliente subiu — sagrado, nunca mexer)
  - `final.pdf` (o resultado do pipeline)
- Nomes internos padronizados; nome original do arquivo fica no banco.
- Downloads sempre via endpoint autenticado (nunca servir a pasta direto pelo nginx).

---

## 4. TELAS

### 4.1 Login
Padrão MayaCorp, JWT, tela limpa com a identidade do produto.

### 4.2 Dashboard / Documentos (a tela principal — o "CRUD bem legal")

Seguir o template obrigatório de CRUD, com capricho extra:

- **Cards de resumo no topo:** total de documentos, prontos, enviados por email, com erro
- **Toolbar:** busca por nome, filtro por status, filtro por período, botão primário **"+ Novo Documento"**
- **Tabela:** nome do arquivo, data, badge de status (com as cores da paleta), rubricado? (ícone), tamanho, ações
- **Ações por linha:**
  - 👁️ **Visualizar** — preview do PDF final inline (modal ou drawer com iframe/embed)
  - ⬇️ Baixar PDF final
  - 📎 Baixar o .docx original
  - ✉️ Enviar por email (abre modal: destinatários, assunto, mensagem — com valores padrão das configurações)
  - 🔄 Reprocessar (roda o pipeline de novo — útil se mudou cabeçalho/rodapé)
  - 🗑️ Excluir (soft delete + modal de confirmação)
- **Empty state** bonito com CTA para o primeiro upload
- **Toast** em toda ação

### 4.3 Novo Documento (modal ou página)

- Drag-and-drop do .docx com feedback visual
- Toggle: **"Rubricar todas as páginas"** (default vem das configurações)
- Após confirmar: mostrar o **pipeline visual** — stepper com as etapas (Cabeçalho → Rodapé → Conversão → Rubrica → Assinatura → Pronto) acendendo conforme o status avança. Esse é um momento "uau" do produto — capriche.

### 4.4 Configurações do Tenant

A tela de configurações é organizada em **abas** (padrão MayaCorp), e a primeira delas é o cadastro central do escritório:

- **Dados do Escritório (aba 1 — fonte única da verdade):**
  - Razão social / nome do escritório
  - CNPJ
  - OAB (número e seccional)
  - Endereço completo (logradouro, cidade, UF, CEP)
  - Telefone e WhatsApp
  - Email de contato e site
  - Upload do **logo** do escritório (com preview)
  - Esses dados alimentam automaticamente: cabeçalho dos documentos, rodapé, template do email e página pública de verificação. Cadastra uma vez, reflete em tudo. Nada de digitar o nome do escritório em três lugares.
- **Cabeçalho:** montado a partir dos Dados do Escritório (logo + campos selecionáveis via checkboxes: quais dados aparecem), com preview em tempo real
  - **Tipografia do cabeçalho:** fonte (dropdown com fontes seguras p/ documentos: Arial, Times New Roman, Calibri, Georgia, Garamond...), tamanho (pt), alinhamento (esquerda / centro / direita), negrito/itálico, cor do texto
  - Posição do logo em relação ao texto (esquerda, direita, acima, sem logo)
- **Rodapé:** texto livre, toggle de numeração de página
  - **Tipografia do rodapé:** mesmas opções do cabeçalho (fonte, tamanho, alinhamento, negrito/itálico, cor) — configurável de forma independente
  - Alinhamento da numeração de página (pode ficar num lado e o texto no outro)
- ⚠️ Toda mudança de tipografia reflete **no preview em tempo real** antes de salvar — e o `python-docx` deve aplicar exatamente essas escolhas ao gerar o documento

#### 🖥️ Preview ao vivo (peça central da tela de configurações)

- Layout em **duas colunas**: formulário à esquerda, preview à direita (fixo/sticky ao rolar)
- O preview renderiza uma **página A4 simulada** com cabeçalho e rodapé montados com os dados reais do escritório + as escolhas de tipografia, e um texto de exemplo (lorem jurídico: trecho de petição fictícia) no miolo
- Atualização **instantânea** a cada mudança: trocou a fonte, mudou na hora; mudou alinhamento, moveu na hora — sem clicar em nada (render no frontend, sem chamar o backend a cada tecla)
- Mostrar também a **última página** simulada: assinatura posicionada + rubrica no canto + QR code de verificação, pra ver o conjunto completo
- Botão **"Gerar PDF de teste"**: roda o pipeline real no servidor com um .docx de exemplo embutido e devolve o PDF pra download/visualização — a prova final de que preview e documento real são idênticos
- No mobile/tela estreita: preview vira aba ou colapsa abaixo do formulário
- **Rubrica:** upload da imagem, preview, toggle "rubricar por padrão"
- **Assinatura:** upload da imagem da assinatura do cliente, preview
- **Email (SMTP):** host, porta, usuário, senha (criptografada no banco — Fernet), nome do remetente, assunto padrão, mensagem padrão. Botão **"Enviar email de teste"**.
- Imagens de rubrica/assinatura: ao subir, tratar com Pillow (fundo branco → transparente) e mostrar o antes/depois

### 4.5 Histórico de envios (dentro do documento)

Cada documento tem sua trilha: quando foi criado, processado, para quem foi enviado por email e quando. Auditoria simples, mas advogado adora rastro.

---

## 5. MODELAGEM (proposta inicial — refine se necessário)

- `tenants` — id, nome, slug, ativo, criado_em
- `usuarios` — id, tenant_id, nome, email, senha_hash, ativo
- `escritorios` — 1:1 com tenant: razão social, CNPJ, OAB, endereço, telefone, whatsapp, email, site, caminho do logo (fonte única dos dados institucionais)
- `configuracoes_tenant` — 1:1 com tenant: caminhos das imagens (rubrica, assinatura), composição do cabeçalho (quais campos do escritório exibir), textos de rodapé, tipografia do cabeçalho e do rodapé (JSONB: fonte, tamanho, alinhamento, negrito, itálico, cor — um objeto p/ cada), posição do logo, flags, SMTP criptografado
- `documentos` — id, tenant_id, usuario_id, nome_original, status, rubricado (bool), caminho_original, caminho_final, hash_sha256, tamanho, paginas, erro_msg, deleted_at, timestamps
- `envios_email` — id, documento_id, destinatarios, assunto, status, enviado_em
- `eventos_documento` — id, documento_id, tipo, detalhe, criado_em (trilha de auditoria)

---

## 6. SURPRESAS (o toque MayaCorp ✨)

Implemente estes diferenciais — são eles que vendem o produto pro advogado:

1. **Hash SHA-256 + QR code de verificação** — todo PDF final ganha, no rodapé da última página, um QR code + código curto. O QR aponta para uma **página pública de verificação** (`/verificar/{codigo}`) que mostra: nome do documento, data de assinatura, escritório, e confirma a integridade pelo hash. Advogado pode provar que o documento não foi alterado. Isso é OURO para o nicho jurídico.
2. **Pipeline visual animado** no processamento (o stepper da tela 4.3).
3. **Preview lado a lado** nas configurações: mini-render de como fica cabeçalho/rodapé antes de salvar.
4. **Email caprichado:** template HTML limpo com a identidade do escritório (logo do cabeçalho), não um email texto puro.

> Nota importante: a "assinatura" aqui é a **imagem** da assinatura aplicada ao PDF + trilha de auditoria + hash. Não é assinatura digital ICP-Brasil (certificado A1/A3). Deixe a arquitetura preparada para, numa fase futura, plugar assinatura criptográfica PAdES (ex: pyHanko) — mas NÃO implemente isso agora.

---

## 7. FASES DE EXECUÇÃO

Trabalhe fase por fase. Ao final de cada fase, me entregue os comandos de deploy/teste no prod2 e **espere minha confirmação** antes de seguir.

- **F0 — Inventário do servidor** (seção 2) + decisões de ferramentas
- **F1 — Fundação:** git init + remote + `.gitignore` + primeiro push; estrutura do projeto, database `mayaassinador`, models, Alembic, auth JWT, tenant seed (o escritório do meu cliente), `.env` + `.env.example`, systemd + nginx + subdomínio, clone no prod2 e deploy do esqueleto funcionando
- **F2 — Configurações do Tenant:** CRUD completo da tela 4.4 (backend + frontend), uploads de imagens funcionando, SMTP com email de teste
- **F3 — Pipeline de documentos:** upload, storage do original, cabeçalho/rodapé, conversão, rubrica, assinatura, hash, QR code, processamento assíncrono com status
- **F4 — CRUD de Documentos:** tela 4.2 completa com preview, downloads, reprocessar, soft delete
- **F5 — Email + auditoria:** envio com template HTML, histórico de envios, página pública de verificação
- **F6 — Polimento:** empty states, toasts, responsivo, revisão de UX no padrão MayaCorp

---

## 8. REGRAS FINAIS

1. Antes de codar qualquer coisa: **Fase 0**. Sem exceção.
2. Todo comando é para o **prod2**. Se você me mandar rodar algo local, errou.
3. CRUD completo sempre. Nada de tela sem API, nada de API sem tela.
4. O anexo original do cliente é sagrado: salvo sempre, intacto, para sempre (até o delete explícito).
5. Código e comentários em português onde fizer sentido; nomes de variáveis podem ser em inglês (padrão da casa).
6. Secrets só em `.env` — nunca hardcoded, nunca commitados.
7. Ao final de cada fase: resumo do que foi feito + **commit e push pro GitHub** + comandos de `git pull` e deploy no prod2 + como eu testo no navegador.

Bora ser feliz. 🚀
