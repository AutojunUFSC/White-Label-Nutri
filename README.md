# White-Label-Nutri

Sistema de **fichas técnicas de preparações e tabelas nutricionais no padrão ANVISA**,
entregue como produto white-label: **uma instância por empresa**, cada cliente com banco
de dados e hospedagem próprios.

O que o sistema faz e para quem: [docs/VISAO_GERAL.md](docs/VISAO_GERAL.md).

## Stack
Django 5.2 LTS · PostgreSQL · Bootstrap 5 · pytest — detalhes em
[docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## Estrutura
- `backend/` — a aplicação Django: `config/`, `apps/`, `tests/` e o `manage.py`
- `frontend/` — `templates/` e `static/` (CSS, JS, Bootstrap), renderizados e servidos pelo próprio Django
- na raiz — dependências, `Procfile`, `pytest.ini` e `.env`; os comandos rodam daqui

## Rodando localmente

Requisitos: **Python 3.12+** e **PostgreSQL 14+**.

**1. Prepare o ambiente**
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

**2. Aponte para o seu PostgreSQL.** Copie `.env.example` para `.env` e ajuste a
`DATABASE_URL` com o host, a **porta** e a senha da sua instalação (o padrão é `5432`,
mas pode ser outra):
```
DATABASE_URL=postgres://postgres:SUA-SENHA@localhost:5432/nutri
```
Se a senha tiver caracteres como `@`, `#` ou `/`, codifique-os na URL (`@` vira `%40`).

**3. Crie a empresa e suba o sistema.** O script cria o banco, aplica as migrações,
configura a instância e oferece subir o servidor:
```bash
python scripts/provisionar_empresa.py
```

A aplicação sobe em <http://localhost:8000>; entre com o administrador que você definiu
nas perguntas. Nas próximas vezes, `python scripts/provisionar_empresa.py --rodar SEU-IDENTIFICADOR`.
Detalhes do script em [Provisionar uma empresa nova](#provisionar-uma-empresa-nova).

Para popular a base de ingredientes, use a tela **Ingredientes → Importar TXT** com
um arquivo da TACO (TXT separado por TAB), ou cadastre um a um.

## Banco de teste (empresa demo)
Para desenvolver sem preencher nada: uma empresa pronta, com 3 usuários, 31 ingredientes e 2 fichas
(valores aproximados da TACO — só para teste, não servem para rótulo real).
```bash
python scripts/banco_teste.py             # cria o banco `nutri_demo`, popula e sobe em :8000
python scripts/banco_teste.py --resetar   # apaga e recria do zero
python scripts/banco_teste.py --sem-servidor
```
Usuários `admin` (administrador), `nutri` e `aluno` — senha `demo1234`; chave de cadastro
`DEMO-2026`. É idempotente e recusa rodar com `DEBUG=False`. Para popular outro banco de
teste já migrado: `python backend/manage.py seed_demo`.

## Testes
```bash
pytest -q
```
Precisam de um PostgreSQL acessível pela `DATABASE_URL` — o pytest-django cria e
destrói o banco de teste sozinho. Cobertura por camada em [docs/TESTES.md](docs/TESTES.md).

## Provisionar uma empresa nova
Um script interativo cria o banco da empresa, gera as variáveis dela (com `SECRET_KEY`
própria), aplica as migrações e configura a instância:

```bash
python scripts/provisionar_empresa.py
```

Requer o ambiente e o `.env` de [Rodando localmente](#rodando-localmente). Ele pergunta nome, identificador, domínio, administrador (usuário, e-mail e senha), cor
primária, chave de cadastro e ano de corte, mostra um resumo e só cria depois da sua
confirmação. Cada pergunta tem um padrão; no caso comum basta informar nome, e-mail e senha.

O servidor PostgreSQL é o da `DATABASE_URL` do `.env` (só host, porta e credenciais são
usados). Cada empresa ganha um banco `nutri_<identificador>`, e suas variáveis ficam em
`instancias/<identificador>.env`, fora do Git.

```bash
python scripts/provisionar_empresa.py --rodar SEU-IDENTIFICADOR    # sobe o servidor da empresa
python scripts/provisionar_empresa.py --remover SEU-IDENTIFICADOR  # apaga banco e variáveis
```

O `--remover` mostra o que será apagado, oferece um backup em `backups/` e exige que você
digite o identificador para confirmar. Só apaga empresas criadas pelo próprio script.

O script cobre a preparação do banco e da instância. A publicação (Gunicorn, Nginx, HTTPS e
variáveis em produção) é independente por empresa e está em [docs/OPERACAO.md](docs/OPERACAO.md);
o `Procfile` já traz o `migrate` de release e o gunicorn.

## Manutenção da base
```bash
python backend/manage.py auditar_tabelas            # fichas com tabela defasada ou incoerente
python backend/manage.py auditar_tabelas --limite 0 --detalhar
```

## Configuração
As variáveis de ambiente estão documentadas em `.env.example` e em
[docs/OPERACAO.md](docs/OPERACAO.md). Em produção, `SECRET_KEY` e `ALLOWED_HOSTS` são
obrigatórias — a aplicação falha no boot sem elas.

## Identidade visual da empresa (white-label)

Nome, cor e logotipo ficam em **Configuração da instância**, no Django admin
(`/admin/`). O logotipo é guardado **no banco desta instância** — não em arquivo —
porque plataformas de disco efêmero apagariam o upload no próximo restart.

Aceita PNG, JPG ou WEBP até 1 MB, validados pelo conteúdo do arquivo. Aparece na
tela de login e no topo do sistema. Para trocar, basta enviar outro; a marca antiga
some do cache do navegador na hora.

O primeiro administrador criado pelo `bootstrap_instancia` é superusuário, então já
enxerga *Configuração da instância* em <http://localhost:8000/admin/>.

### Cores sugeridas

A cor primária é um código hexadecimal (`#RRGGBB`), passado em `--cor` no provisionamento
ou editado depois no admin. Prefira tons médios a escuros: o texto branco precisa de
contraste sobre a cor.

| Cor | Código | Cor | Código |
| --- | --- | --- | --- |
| Verde (padrão) | `#198754` | Azul | `#0d6efd` |
| Azul-marinho | `#0b3c8a` | Ciano | `#0891b2` |
| Roxo | `#6f42c1` | Índigo | `#4f46e5` |
| Rosa | `#d63384` | Vermelho | `#dc3545` |
| Laranja | `#e8590c` | Âmbar | `#b45309` |
| Verde-escuro | `#166534` | Turquesa | `#0f766e` |
| Cinza-grafite | `#374151` | Marrom | `#7c4a2d` |

```bash
python backend/manage.py bootstrap_instancia --nome "SUA-EMPRESA" --admin admin \
    --chave SUA-CHAVE-2026 --cor "#0f766e"
```

## Documentação
- [docs/VISAO_GERAL.md](docs/VISAO_GERAL.md) — o produto, o modelo white-label e o índice
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — stack, estrutura do código, segurança, decisões
- [docs/REGRAS_DE_NEGOCIO.md](docs/REGRAS_DE_NEGOCIO.md) — BR-001..BR-030 (cálculo, rótulo, fichas)
- [docs/BANCO_DE_DADOS.md](docs/BANCO_DE_DADOS.md) — modelo de dados e invariantes
- [docs/INTERFACE.md](docs/INTERFACE.md) — as telas, com capturas
- [docs/OPERACAO.md](docs/OPERACAO.md) — provisionar, publicar, configurar e manter
- [docs/TESTES.md](docs/TESTES.md) — como rodar a suíte e o que ela cobre
- [docs/FLUXO_DE_TRABALHO.md](docs/FLUXO_DE_TRABALHO.md) — branches `main`, `develop` e `features`, e como publicar
