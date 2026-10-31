"""Roteiro do tour de boas-vindas (onboarding guiado).

O texto é o mesmo para toda empresa; só o nome vem da instância. Cada passo diz:

- `rota`: o nome da URL da tela em que aparece;
- `alvo`: o elemento a destacar (seletor `[data-tour=...]` dos templates), ou None para
  um cartão centralizado;
- `acao`: "clicar" espera que a pessoa clique no elemento destacado (e só ele fica
  clicável); "proximo" mostra um botão para seguir.

O tour percorre as telas na ordem do roteiro. Se a pessoa sair dele, ele se encerra.
"""


def _alvo(nome: str) -> str:
    return f'[data-tour="{nome}"]'


def passos(empresa: str, administrador: bool) -> list[dict]:
    roteiro = [
        {
            "id": "boas-vindas", "rota": "listaFichas", "alvo": None, "acao": "proximo",
            "botao": "Começar",
            "titulo": f"Bem-vindo(a) ao {empresa}",
            "texto": (
                "Vamos fazer um passeio rápido pelas telas, passo a passo, para você "
                "montar sua primeira ficha técnica com tabela nutricional no padrão ANVISA."
            ),
        },
        {
            "id": "ingredientes", "rota": "listaFichas", "alvo": _alvo("nav-ingredientes"),
            "acao": "clicar",
            "titulo": "Comece pelos ingredientes",
            "texto": "Uma ficha só usa ingredientes já cadastrados. Clique em Ingredientes para ver a base.",
        },
        {
            "id": "cadastro-ingredientes", "rota": "listaIngredientes",
            "alvo": _alvo("ingredientes-acoes"), "acao": "proximo",
            "titulo": "Cadastre ou importe",
            "texto": "Use Novo ingrediente para cadastrar um item, ou Importar TXT para carregar vários de uma vez.",
        },
        {
            "id": "fichas", "rota": "listaIngredientes", "alvo": _alvo("nav-fichas"),
            "acao": "clicar",
            "titulo": "Agora, as fichas",
            "texto": "Clique em Fichas para voltar à lista de fichas.",
        },
        {
            "id": "nova-ficha", "rota": "listaFichas", "alvo": _alvo("nova-ficha"),
            "acao": "clicar",
            "titulo": "Crie uma ficha",
            "texto": "Clique em Nova ficha. O cadastro tem três etapas: dados base, receita e tabela nutricional.",
        },
        {
            "id": "pesos", "rota": "registrarFicha1", "alvo": _alvo("pesos"), "acao": "proximo",
            "titulo": "Informe os pesos primeiro",
            "texto": (
                "Preencha o peso total e o peso da porção. Sem eles não dá para adicionar "
                "ingredientes na etapa 2, e todo o cálculo parte desses valores."
            ),
        },
        {
            "id": "etapas", "rota": "registrarFicha1", "alvo": _alvo("etapas"), "acao": "proximo",
            "titulo": "Acompanhe as etapas",
            "texto": (
                "Depois dos dados base vêm a receita e a tabela nutricional. No fim, o rótulo "
                "final: copie o conteúdo para o Google Docs e marque a ficha como finalizada."
            ),
        },
    ]
    if administrador:
        roteiro.append(
            {
                "id": "membros", "rota": "registrarFicha1", "alvo": _alvo("nav-membros"),
                "acao": "proximo",
                "titulo": "Gerencie a equipe",
                "texto": (
                    "Em Membros você vê a chave de cadastro — quem a tiver cria a própria "
                    "conta na tela de login — e administra as pessoas da equipe."
                ),
            }
        )
    roteiro.append(
        {
            "id": "ajuda", "rota": "registrarFicha1", "alvo": _alvo("nav-ajuda"),
            "acao": "proximo", "botao": "Concluir",
            "titulo": "Ficou com dúvida?",
            "texto": "A Ajuda reúne as perguntas frequentes e tem o botão para refazer este passeio quando quiser.",
        }
    )
    return roteiro
