# Interface

Layout único (`frontend/templates/base.html`): barra superior com **Fichas**, **Ingredientes**,
**Membros**, **Ajuda** e **Sair**, o nome e a cor da empresa vindos da configuração da
instância, e uma área de mensagens no topo do conteúdo. Bootstrap 5 servido pela própria
aplicação. As listagens são paginadas de 25 em 25 e os filtros viajam na URL, então uma
busca pode ser compartilhada por link.

## Criar uma ficha técnica

O fluxo tem três passos, com o progresso sempre visível.

### 1. Dados base — `/registrarFicha1`
Autor, cliente, nome da receita, peso total, peso da porção (cliente e ANVISA), medida
caseira e data. Os pesos alimentam todo o cálculo; sem peso total e peso da porção não é
possível montar a receita.

![Passo 1](imagens/criacao-receita/03-passo1-dados-base.png)

### 2. Receita — `/registrarFicha2/<pk>`
Cada item é um ingrediente do cadastro (campo com autocompletar, por nome exato), com nome
fantasia, pesos bruto e líquido e medida caseira. A cada item adicionado, os totais no topo
são recalculados.

![Passo 2](imagens/criacao-receita/06-passo2-receita-completa.png)

### 3. Tabela nutricional — `/registrarFicha3/<pk>`
Todos os nutrientes com valor total, por 100 g, por porção, arredondado e %VD. A coluna
"No rótulo" liga e desliga cada linha da versão final. Ao lado, o campo de informações
complementares (alérgicos) e o cadastro de nutrientes extras manuais.

![Passo 3](imagens/criacao-receita/07-passo3-tabela-nutricional.png)

### Rótulo final — `/fichaX/<pk>`
Pesos da preparação, os modelos **vertical** e **linear** da tabela, lista de ingredientes,
alérgicos e as lupas "ALTO EM" quando aplicável. O botão **Copiar conteúdo** leva o bloco
pronto para o Google Docs; **Marcar como finalizada** aplica o selo.

Quando os valores gravados não conferem com o cálculo atual dos pesos da ficha, a tela
mostra um aviso com as diferenças e um botão de recálculo explícito (D-017).

![Rótulo final](imagens/criacao-receita/09-ficha-final-rotulo.png)

## Ingredientes

### Listagem — `/listaIngredientes`
Filtros por nome, fonte/marca e autor, com a energia por 100 g de cada registro e ações de
editar e excluir.

![Ingredientes](imagens/cadastro-ingrediente/01-lista-ingredientes.png)

### Cadastro — `/registrarIngrediente`
Identificação (nome, autor, composição, fonte, **quantidade de referência**, data) e a
composição nutricional. Os valores são informados para a quantidade de referência: uma lata
de 395 g pode ser cadastrada como tal, e o sistema normaliza para 100 g.

![Composição](imagens/cadastro-ingrediente/04-composicao-nutricional.png)

### Importação em lote — `/upload`
TXT separado por TAB no layout da TACO, para carregar a base inicial de ingredientes de uma
vez (BR-023).

![Importação](imagens/cadastro-ingrediente/09-upload-em-lote-taco.png)

## Fichas, membros e ajuda

- **`/listaFichas`** — listagem inicial, com filtros por receita, cliente e autor e o selo
  das fichas finalizadas.
- **`/listaMembros`** — quem tem acesso à instância. Para administradores, mostra a chave
  de cadastro e permite trocá-la, redefinir a senha de um membro e excluir membros
  transferindo a autoria das fichas e ingredientes.
- **`/registrarMembro`** — auto-cadastro com a chave da instância.
- **`/ajuda`** — instruções de uso para a equipe e o botão **Ver o tour de novo**.
- **`/admin/`** — Django admin, restrito a superusuários; é onde se edita a
  **Configuração da instância** (nome, cor, ano de corte) e se envia o logotipo, com
  prévia e opção de remover. O logotipo aparece na barra superior e na tela de login,
  servido por `/branding/logotipo`.

## Tour de boas-vindas

Um passeio guiado para quem entra pela primeira vez: a tela escurece, o elemento do passo
fica em destaque e um cartão ao lado explica o que fazer. O passeio atravessa as telas na
ordem em que se usa o sistema:

1. boas-vindas (cartão centralizado);
2. **clique em Ingredientes** no menu;
3. em Ingredientes, os botões *Importar TXT* e *Novo ingrediente*;
4. **clique em Fichas** para voltar à lista;
5. **clique em Nova ficha**;
6. os campos de peso da etapa 1, que alimentam todo o cálculo;
7. o indicador das três etapas e o rótulo final;
8. *(só administradores)* **Membros**, onde ficam a chave de cadastro e a equipe;
9. **Ajuda**, onde o passeio pode ser refeito.

Nos passos "clique", só o elemento destacado responde ao clique, e o clique leva à tela do
passo seguinte, onde o tour continua sozinho. Nos demais há um botão **Próximo**. Em
qualquer passo dá para **Sair do tour** ou apertar `Esc`. Se a pessoa for para outra tela
fora do roteiro, o tour se encerra. No celular o menu recolhido abre sozinho para o
destaque ter onde cair.

O texto é o mesmo para toda empresa; só o nome vem da configuração da instância
(`apps/fichas/tour.py`).

- **Quando começa sozinho:** no primeiro login do usuário. O sistema usa o `last_login` do
  Django — vazio antes do primeiro acesso — e guarda uma marca na sessão que é consumida
  na primeira tela exibida, então ele não volta a começar sozinho. Quem já usava o sistema
  antes não vê o tour, e nenhuma migração é necessária.
- **Como rever:** botão **Ver o tour de novo** na página de Ajuda.
- **Onde fica o progresso:** na aba do navegador (`sessionStorage`), por até 30 minutos;
  sair do sistema o apaga.
- **Como apontar um elemento:** os templates marcam o que pode ser destacado com
  `data-tour="..."`; o roteiro referencia essas marcas. Um teste confere que cada marca do
  roteiro existe na tela do seu passo.
- **Código:** `apps/fichas/tour.py` (roteiro), `apps/fichas/context_processors.py` (quando
  entregar o roteiro), `frontend/static/js/tour.js` (destaque, cartão e navegação) e os
  estilos `.tour-*` em `app.css`.

As capturas completas de cada fluxo estão em `docs/imagens/criacao-receita/` e
`docs/imagens/cadastro-ingrediente/`, com legenda no `LEIA-ME.md` de cada pasta.
