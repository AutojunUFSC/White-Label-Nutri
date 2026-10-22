# Operação

Cada empresa cliente tem um deploy próprio, com banco e variáveis próprias. O artefato é
o mesmo repositório para todas.

## Provisionar uma empresa nova

```bash
createdb nutri_acme

export DATABASE_URL=postgres://usuario:senha@host:5432/nutri_acme
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
export ALLOWED_HOSTS=nutri.acme.com.br
export DJANGO_SETTINGS_MODULE=config.settings.prod

python backend/manage.py migrate
python backend/manage.py bootstrap_instancia \
    --nome "Nutri Acme" --admin ana --email ana@acme.com \
    --chave ACME-2026 --cor "#198754"
```

O `bootstrap_instancia` cria, numa transação: a configuração da instância, o grupo
`administradores`, o primeiro usuário administrador (com o membro correspondente) e a
chave de auto-cadastro. Ele **recusa** rodar sobre uma instância já configurada.

A senha vem por `--senha`, pela variável `INSTANCIA_ADMIN_SENHA` ou, na ausência das duas,
é pedida no terminal. Prefira as duas últimas: `--senha` fica no histórico do shell.

Opções úteis:

| Opção | Efeito |
| --- | --- |
| `--cor "#198754"` | cor primária da interface |
| `--ano-corte 2024` | esconde ingredientes cadastrados antes desse ano (0 = sem corte, padrão) |

Depois disso: a equipe se cadastra em `/registrarMembro` com a chave, e o administrador
ajusta cores e logotipo em `/admin/` → *Configuração da instância*. O logotipo é enviado
como arquivo (PNG, JPEG ou WEBP até 1 MB), guardado no banco e servido em
`/branding/logotipo` — aparece na barra superior e na tela de login.

### A instância precisa ter configuração

Sem a linha de configuração o sistema assume os padrões, e o mais silencioso deles é o ano
de corte vazio: a lista de ingredientes passa a exibir cargas antigas que a empresa talvez
esconda de propósito (BR-017). Nada quebra — por isso passaria despercebido.

Para não depender da memória, `backend/manage.py check` avisa enquanto ela não existir, e o aviso
aparece também no deploy:

```
?: (plataforma.W001) Esta instância não tem configuração white-label.
```

O `bootstrap_instancia` já cria a linha; o aviso serve para bancos que chegaram por outro
caminho.

## Publicar

O `Procfile` já traz o necessário para um PaaS (Heroku, Render, Fly e semelhantes):

```
release: python backend/manage.py migrate
web: gunicorn config.wsgi --log-file -
```

Requisitos do ambiente: Python 3.12+, um PostgreSQL acessível e as variáveis abaixo. Os
arquivos estáticos são servidos pelo WhiteNoise — rode `python backend/manage.py collectstatic`
no build se o seu provedor não o fizer.

### Variáveis de ambiente

| Variável | Obrigatória | Observação |
| --- | --- | --- |
| `SECRET_KEY` | sim | valor longo e aleatório, único por instância |
| `ALLOWED_HOSTS` | sim | domínios da instância, separados por vírgula |
| `DATABASE_URL` | sim | `postgres://usuario:senha@host:5432/banco` |
| `DJANGO_SETTINGS_MODULE` | sim em produção | `config.settings.prod` |
| `DEBUG` | não | nunca ligar em produção |
| `LOG_LEVEL` | não | padrão `INFO` |
| `SECURE_SSL_REDIRECT` | não | padrão ligado |
| `SECURE_HSTS_SECONDS` | não | padrão 3600 |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | não | só ligue se **todos** os subdomínios servirem HTTPS |
| `SESSION_COOKIE_AGE` | não | padrão 12 h |
| `CONN_MAX_AGE` | não | padrão 60 s |
| `SESSION_COOKIE_SECURE` | não | padrão ligado; só desligue para testar em `localhost` |
| `CSRF_COOKIE_SECURE` | não | idem |
| `GEMINI_API_KEY` | não | liga a leitura da tabela nutricional por foto; sem ela o botão não aparece |
| `GEMINI_MODELO` | não | padrão `gemini-3.6-flash` (testado: rápido e lê todos os campos; o `3.8-flash` estava sobrecarregado e o `3.5-flash-lite` omitia nutrientes) |
| `GEMINI_RACIOCINIO` | não | `minimal`, `low` (padrão), `medium` ou `high`; mais alto = mais lento |
| `GEMINI_TIMEOUT` | não | padrão 45 s (o gunicorn do `Procfile` espera até 60 s) |

Em desenvolvimento, um arquivo `.env` na raiz substitui as variáveis exportadas —
modelo em `.env.example`.

## Manutenção

### Conferir tabelas desatualizadas

```bash
python backend/manage.py auditar_tabelas               # resumo + 30 fichas
python backend/manage.py auditar_tabelas --limite 0 --detalhar
python backend/manage.py auditar_tabelas --so-incoerentes
```

Somente leitura. Separa as fichas em três situações: em dia, **valores defasados** (a
ficha foi calculada antes de o ingrediente mudar) e **rótulo incoerente** (o cabeçalho
declara um peso de porção e as colunas correspondem a outro — BR-005b). As incoerentes são
defeito de documento e devem ser recalculadas antes de qualquer nova emissão; as defasadas
são consequência esperada de a ficha congelar o cálculo do momento em que foi feita.

O recálculo é sempre explícito, pelo botão na tela do rótulo da ficha (D-007/D-017).

### Carregar a base de ingredientes

Pela tela **Ingredientes → Importar TXT**, com um arquivo da TACO separado por TAB
(BR-023). Numa instância nova é o primeiro passo depois do provisionamento.

### Cópias de segurança

Use o backup automático do provedor de banco. O dump contém dados de cliente: guarde-o
como material confidencial e nunca no repositório.

### Atualizar uma instância

```bash
git pull
pip install -r requirements.txt
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Rode `pytest` antes de publicar — ver [TESTES.md](TESTES.md).
