# Deploy — MayaAssinador

## Coordenadas

| | |
|---|---|
| Servidor | prod2 (Hostinger), usuario `deploy` |
| IP | `2.25.130.240` (sem DNS ainda) |
| Frontend | `http://2.25.130.240:3030` |
| API | `http://2.25.130.240:8030` · docs em `/docs` |
| Codigo | `/home/deploy/mayaassinador` |
| Storage | `/var/mayaassinador/storage` (fora do repo) |
| Banco | `mayaassinador` / role `mayaassinador_user` |
| Repo | `git@github-mayaassinador:Jeff1984Sor/mayaassinador.git` |

O remote usa o **apelido** `github-mayaassinador` (definido em `~/.ssh/config` no
prod2), porque a deploy key do MayaAssinador e diferente da do flicsales.

## Fluxo de trabalho

Windows (edicao) -> commit + push -> prod2 (`git pull`) -> deploy.
Nunca editar codigo direto no servidor.

## Servicos (nomes exatos — nao chutar)

| Servico | Unit systemd | Porta |
|---|---|---|
| API | `mayaassinador-api` | 8030 |
| Worker do pipeline | `mayaassinador-worker` | — |
| Frontend | `mayaassinador-frontend` | 3030 |

O prod2 hospeda outros produtos da casa, com prefixo parecido —
`mayapost-*` e `mayasec-*`. Um `grep maya` distraido pega servico de outro
cliente: filtre por `mayaassinador-` inteiro antes de reiniciar qualquer
coisa. Para achar o processo do nosso frontend entre as varias aplicacoes
Next do servidor: `pgrep -af "next start -p 3030"`.

## Deploy do backend

```bash
cd ~/mayaassinador && git pull
cd backend
.venv/bin/pip install -r requirements.txt   # so se requirements mudou
.venv/bin/alembic upgrade head              # so se ha migration nova
sudo systemctl restart mayaassinador-api
curl -s http://127.0.0.1:8030/api/health; echo
```

## Deploy do frontend

```bash
cd ~/mayaassinador && git pull
cd frontend
npm install        # so se package.json mudou
npm run build      # SEMPRE: variaveis NEXT_PUBLIC_* sao embutidas no build
sudo systemctl restart mayaassinador-frontend   # OBRIGATORIO — ver armadilha abaixo
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3030/escritorio/login
```

### Armadilha: build sem restart derruba a tela inteira

Esquecer o `restart` depois do `npm run build` **nao** deixa a versao antiga
no ar — quebra tudo. Cada build gera nomes com hash novo para o CSS e para
os chunks de JS; o processo que ficou rodando so conhece o build anterior e
responde **400 Bad Request** (nao 404) a qualquer estatico que nao esteja no
manifesto dele. Sem o JS, o React nao hidrata e a pagina mostra
"Application error: a client-side exception has occurred".

O sintoma engana: parece erro de codigo ou de Tailwind, e o build passa
limpo. O teste que resolve em um comando — os dois caminhos tem que ser
iguais e a resposta 200:

```bash
C=$(curl -s http://127.0.0.1:3030/escritorio/login | grep -o '/_next/static/css/[^"]*' | head -1)
echo "HTML pede: $C"
echo "no disco : /_next/static/css/$(ls .next/static/css/ | head -1)"
curl -s -o /dev/null -w "resposta : %{http_code}\n" "http://127.0.0.1:3030$C"
```

Depois de corrigir, recarregue com Ctrl+Shift+R: o navegador guarda o HTML
antigo, que aponta para arquivos que ja nao existem.

O `buildId` nao aparece no HTML das telas (isso e do Pages Router; usamos
App Router) — nao tente conferir por ali.

## Logs

```bash
sudo journalctl -u mayaassinador-api -n 50 --no-pager
sudo journalctl -u mayaassinador-frontend -n 50 --no-pager
```

## Decisoes de infraestrutura (F0)

- **Fila no Postgres**, nao Redis. O unico Redis do prod2 pertence ao container
  do Evolution API; nao dependemos de infra de outro produto. A tabela
  `documentos` tem indice parcial `ix_documentos_fila` para o `SKIP LOCKED`.
- **Concorrencia do worker = 1.** O prod2 nao tem swap e cada LibreOffice
  headless consome ~400MB. Varias conversoes simultaneas derrubariam os outros
  14 servicos da VM por OOM.
- **Dropdown de fontes limitado a 6** (`FONTES_DISPONIVEIS` em
  `app/models/configuracao.py`): so o que esta instalado no servidor. Qualquer
  outra fonte seria substituida pelo LibreOffice e o PDF sairia diferente do
  preview. Garamond ficou de fora por nao ter substituto de metrica identica.
- **Nginx e HTTPS ficam para quando houver DNS.** Ate la, IP:porta com as
  portas 3030/8030 liberadas no ufw.

## Quando voltar ao DNS

1. Apontar `assinador.mayacorp.com.br` para `2.25.130.240`
2. Criar o server block em `/etc/nginx/sites-available/` (proxy 3030 e 8030)
3. `sudo certbot --nginx -d assinador.mayacorp.com.br`
4. Trocar `PUBLIC_BASE_URL` / `CORS_ORIGINS` no `backend/.env` e
   `NEXT_PUBLIC_API_URL` no `frontend/.env.local`, rebuildar o frontend
5. Fechar 3030/8030 no ufw
