# Fluxo de trabalho com branches

O repositório usa só três branches. O código anda sempre no mesmo sentido:

```
features  ──PR──▶  develop  ──PR──▶  main
(trabalho)        (integração)       (no ar)
```

| Branch | Para que serve | Quem escreve nela |
|---|---|---|
| `main` | O programa principal, o que está publicado. Os deploys das empresas saem daqui. | Só recebe PR vindo de `develop`. Ninguém faz commit direto. |
| `develop` | Desenvolvimento geral: junta as funcionalidades prontas antes de irem ao ar. | Só recebe PR vindo de `features`. |
| `features` | Onde as funcionalidades novas são feitas. | Todos os commits do dia a dia. |

Não se criam outras branches. As antigas `claude/*` ficam só como histórico.

## Dia a dia

1. Comece com a `features` atualizada em relação à `develop`:

   ```bash
   git checkout features
   git pull
   git merge origin/develop
   ```

2. Faça os commits na `features`. Rode a suíte antes de enviar (`python -m pytest`).
3. `git push` e abra um PR **`features` → `develop`**.
4. O CI (`.github/workflows/testes.yml`) roda em todo push e PR. Só faça o merge com ele verde.

## Publicar (levar para a `main`)

1. Abra um PR **`develop` → `main`** com o resumo do que entra.
2. Com o CI verde, faça o merge.
3. No deploy, rode `python backend/manage.py migrate` se o PR trouxer migrações. A descrição do PR deve avisar quando trouxer.

## Correção urgente em produção

Segue o mesmo caminho, só que sem esperar outras funcionalidades: corrija na
`features`, PR para `develop`, e logo em seguida PR de `develop` para `main`.
Se a `develop` tiver coisas que ainda não podem ir ao ar, combine antes de publicar.

## Mensagens de commit

Em português, com prefixo do tipo da mudança, como no histórico:

- `feat:` funcionalidade nova
- `fix:` correção
- `refactor:` reorganização sem mudar comportamento
- `test:` testes
- `docs:` documentação
