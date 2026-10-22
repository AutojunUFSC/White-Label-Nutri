"""Views do sistema.

Convenções: toda mutação exige login e método POST; registro inexistente
devolve 404 (get_object_or_404); o papel administrativo vem do grupo Django
configurado em GRUPO_ADMINISTRADORES.

Regras de negócio: ver docs/REGRAS_DE_NEGOCIO.md (BR-XXX citadas no código).
"""
import csv
import io

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.fichas import leitura_rotulo, servicos
from apps.fichas.busca import contem_palavras
from apps.fichas.dominio import rotulo
from apps.fichas.dominio.lupas_img import LUPAS_BASE64
from apps.fichas.dominio.nutrientes import (
    GRUPOS_CADASTRO,
    NUTRIENTES,
    POR_CHAVE,
    ROTULO_CADASTRO,
    unidade_armazenada,
)
from apps.fichas.forms import (
    ApagarMembroForm,
    ChaveForm,
    FichaFiltroForm,
    FichaFormBase,
    FormInformacoesComplementares,
    IngredienteFiltroForm,
    IngredienteForm,
    LoginForm,
    MembroForm,
    MudarSenhaForm,
    NutrienteForm,
    ReceitaForm,
)
from apps.fichas.models import (
    Chave,
    Ficha,
    Ficha_Ingrediente,
    Ingrediente,
    Membro,
    Nutriente,
)
from apps.plataforma.models import ConfiguracaoInstancia

# ---------------------------------------------------------------- autenticação


def login_user(request):
    logout(request)  # BR-027
    form = LoginForm(request.POST or None)
    if form.is_valid():
        user = authenticate(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None:
            login(request, user)
            return redirect("listaFichas")
        messages.error(request, "Não foi possível fazer login")
    return render(request, "login.html", {"form": form})


def logout_user(request):
    logout(request)
    return redirect("loginUser")


ITENS_POR_PAGINA = 25


def _paginar(request, queryset):
    """Pagina uma listagem preservando os filtros na querystring."""
    paginador = Paginator(queryset, ITENS_POR_PAGINA)
    pagina = paginador.get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)
    return pagina, parametros.urlencode()


# ---------------------------------------------------------------------- fichas


@login_required
def lista_fichas(request):
    """BR-028 — filtros por 'contains' combinados, mais recentes primeiro.
    Filtros migraram de POST para GET (decisão de UI): ficam na URL e permitem paginar."""
    fichas = Ficha.objects.select_related("autor").order_by("-dataCriacao", "-id")
    form_filtro = FichaFiltroForm(request.GET or None)
    if form_filtro.is_valid():
        dados = form_filtro.cleaned_data
        fichas = fichas.filter(
            contem_palavras("nomeFicha", dados["f_nomeFicha"])
            & contem_palavras("cliente", dados["f_cliente"])
            & contem_palavras("autor__nome", dados["f_autor"])
        )
    pagina, filtros = _paginar(request, fichas)
    return render(
        request,
        "fichas_registradas.html",
        {
            "fichas": pagina,
            "pagina": pagina,
            "filtrosQuery": filtros,
            "total": fichas.count(),
            "formFiltro": form_filtro,
        },
    )


@login_required
def registrar_ficha_base(request):
    """Passo 1/3 — cria a ficha e sua tabela com o mesmo pk (BR-015)."""
    form = FichaFormBase(request.POST or None)
    if form.is_valid():
        nova = form.save()
        servicos.obter_tabela(nova)
        return redirect("editarFicha2", pk=nova.pk)
    return render(request, "ficha_base.html", {"form": form, "passo": 1})


@login_required
def editar_ficha_base(request, pk):
    """Passo 1/3 em edição — salvar recalcula a tabela (pesos mudaram)."""
    ficha = get_object_or_404(Ficha, pk=pk)
    form = FichaFormBase(request.POST or None, instance=ficha)
    if request.method == "POST" and form.is_valid():
        form.save()
        servicos.recalcular_tabela(ficha)
        return redirect("editarFicha2", pk=pk)
    return render(request, "ficha_base.html", {"form": form, "fichaAtual": ficha, "passo": 1})


@login_required
def editar_ficha_receita(request, pk):
    """Passo 2/3 — monta a receita (BR-016, BR-017)."""
    ficha = get_object_or_404(Ficha, pk=pk)
    tabela = servicos.obter_tabela(ficha)
    form_receita = ReceitaForm(request.POST or None)

    if request.method == "POST" and form_receita.is_valid():
        if not ficha.pesoTotal or not ficha.pesoPorcao:
            messages.error(
                request,
                "Informe o peso total e o peso da porção na etapa 1 antes de "
                "adicionar ingredientes.",
            )
            return redirect("editarFicha2", pk=pk)

        # o autocomplete envia o id; sem JS, vale o nome digitado
        escolhido = None
        if request.POST.get("ingId", "").isdigit():
            escolhido = Ingrediente.objects.filter(pk=request.POST["ingId"]).first()
        if escolhido is None:
            escolhido = Ingrediente.buscar_por_nome_exibicao(request.POST.get("ingExtra", ""))
        if escolhido is None:
            messages.error(request, "Ingrediente para adicionar a receita não foi encontrado")
            return redirect("editarFicha2", pk=pk)

        item = form_receita.save(commit=False)
        item.ficha = ficha
        item.ingrediente = escolhido
        item.save()
        servicos.recalcular_tabela(ficha)
        messages.success(request, f"{escolhido.nome_exibicao} adicionado à receita.")
        return redirect("editarFicha2", pk=pk)

    return render(
        request,
        "ficha_receita.html",
        {
            "fichaAtual": ficha,
            "formReceita": form_receita,
            "itensReceita": Ficha_Ingrediente.objects.filter(ficha=ficha).select_related(
                "ingrediente"
            ),
            "tabelaNutricional": tabela,
            "nutrientesExtras": Nutriente.objects.filter(origemTabela=tabela),
            "ingredientesBusca": [
                {"id": i.pk, "nome": i.nomeIng, "marca": i.origemDosDados}
                for i in _ingredientes_disponiveis().only("nomeIng", "origemDosDados")
            ],
            "passo": 2,
        },
    )


@login_required
@require_POST
def deletar_item_receita(request, pk, id):
    """BR-018: não remove o último item da receita."""
    ficha = get_object_or_404(Ficha, pk=pk)
    itens = Ficha_Ingrediente.objects.filter(ficha=ficha)
    if itens.count() > 1:
        get_object_or_404(Ficha_Ingrediente, pk=id, ficha=ficha).delete()
        servicos.recalcular_tabela(ficha)
    else:
        messages.error(request, "A receita precisa ter pelo menos um ingrediente.")
    return redirect("editarFicha2", pk=pk)


@login_required
def editar_item_receita(request, pk, id):
    """Edita um item da receita; salvar recalcula a tabela."""
    ficha = get_object_or_404(Ficha, pk=pk)
    item = get_object_or_404(Ficha_Ingrediente, pk=id, ficha=ficha)
    form = ReceitaForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        servicos.recalcular_tabela(ficha)
        messages.success(request, "Item da receita atualizado.")
        return redirect("editarFicha2", pk=pk)
    return render(
        request, "ficha_item_receita.html", {"item": item, "form": form, "fichaAtual": ficha}
    )


@login_required
def editar_ficha_tabela(request, pk):
    """Passo 3/3 — visibilidade dos nutrientes, extras e informações complementares."""
    ficha = get_object_or_404(Ficha, pk=pk)
    tabela = servicos.obter_tabela(ficha)
    form_nutriente = NutrienteForm(request.POST or None)
    form_info = FormInformacoesComplementares(instance=tabela)

    if request.method == "POST":
        if request.POST.get("acao") == "nutriente":
            if form_nutriente.is_valid():
                extra = form_nutriente.save(commit=False)
                extra.origemTabela = tabela
                extra.save()
                messages.success(request, "Nutriente adicionado à tabela.")
                return redirect("editarFicha3", pk=pk)
        else:
            form_info = FormInformacoesComplementares(request.POST, instance=tabela)
            if form_info.is_valid():
                form_info.save()
                return redirect("fichaX", pk=pk)

    return render(
        request,
        "ficha_tabela.html",
        {
            "fichaAtual": ficha,
            "tabelaNutricional": tabela,
            "linhasTabela": _linhas_edicao(tabela),
            "nutrientesExtras": Nutriente.objects.filter(origemTabela=tabela),
            "formNutriente": form_nutriente,
            "formInfComplementares": form_info,
            "passo": 3,
        },
    )


@login_required
@require_POST
def deletar_nutriente_extra(request, pk):
    extra = get_object_or_404(Nutriente, pk=pk)
    ficha_pk = extra.origemTabela.origem.pk
    extra.delete()
    return redirect("editarFicha3", pk=ficha_pk)


@login_required
@require_POST
def atualizar_mostrar(request, pk, item):
    """Inverte a visibilidade de um nutriente na tabela final (BR-030)."""
    ficha = get_object_or_404(Ficha, pk=pk)
    tabela = servicos.obter_tabela(ficha)
    if item not in POR_CHAVE:
        messages.error(request, "Nutriente desconhecido.")
        return redirect("editarFicha3", pk=pk)
    campo = f"{item}_Mostrar"
    setattr(tabela, campo, not getattr(tabela, campo))
    tabela.save(update_fields=[campo])
    return redirect("editarFicha3", pk=pk)


@login_required
def ficha_x(request, pk):
    """Rótulo final (BR-009..BR-014, BR-030)."""
    ficha = get_object_or_404(Ficha, pk=pk)
    tabela = servicos.obter_tabela(ficha)  # cria a tabela se estiver faltando

    valores = {
        n.chave: rotulo.ValoresNutriente(
            arred=getattr(tabela, f"{n.chave}_Arred"),
            vd=getattr(tabela, f"{n.chave}_VD"),
            unidade=getattr(tabela, f"{n.chave}_unidadeMd"),
            por_100g=getattr(tabela, f"{n.chave}_100g"),
            mostrar=getattr(tabela, f"{n.chave}_Mostrar"),
        )
        for n in NUTRIENTES
    }
    extras = [
        (extra.nomeNutri, extra.qtde_Arred, extra.qtde_VD)
        for extra in Nutriente.objects.filter(origemTabela=tabela)
    ]
    linhas = rotulo.montar_linhas(valores, extras)

    itens = [
        {
            "nomeFantasia": item.nomeFantasia,
            "pesoLiquido": item.pesoLiquido,
            "composicao": item.ingrediente.composicao,
        }
        for item in Ficha_Ingrediente.objects.filter(ficha=ficha).select_related("ingrediente")
    ]

    # Confere se o que esta gravado corresponde ao calculo atual. Nao altera nada:
    # o rotulo continua mostrando os valores gravados (D-007), mas com aviso.
    conferencia = servicos.conferir_tabela(ficha, tabela)

    combinacao = rotulo.combinacao_lupa(
        rotulo.nutrientes_altos(
            tabela.acucaresadd_100g, tabela.gordSat_100g, tabela.sodio_100g
        )
    )

    return render(
        request,
        "ficha_rotulo.html",
        {
            "fichaAtual": ficha,
            "tabelaAtual": tabela,
            "linhas": linhas,
            "linhasIndentadas": rotulo.INDENTADOS,
            "pesoAnvisaSemZero": rotulo.peso_anvisa_sem_zero(
                ficha.pesoAnvisa, ficha.pesoPorcao
            ),
            "numPorcoesExibicao": rotulo.calcular_num_porcoes(
                ficha.pesoPorcao, ficha.pesoAnvisa
            ),
            "numPorcoes": rotulo.num_porcoes_exibicao(ficha.pesoPorcao, ficha.pesoAnvisa),
            "ordemIngredientes": rotulo.ordenar_ingredientes(itens),
            "lupa_img": LUPAS_BASE64.get(combinacao) if combinacao else None,
            "conferencia": conferencia,
        },
    )


@login_required
@require_POST
def recalcular_ficha(request, pk):
    """Recalcula a tabela de UMA ficha, por acao explicita do usuario.

    Existe porque o acervo tem fichas cuja tabela foi gravada com pesos ou
    ingredientes diferentes dos atuais (BR-005b).
    Nunca acontece em massa: os valores gravados sao os rotulos emitidos (D-007).
    """
    ficha = get_object_or_404(Ficha, pk=pk)
    servicos.recalcular_tabela(ficha)
    messages.success(
        request,
        "Tabela recalculada com os pesos e ingredientes atuais. "
        "Confira os valores antes de emitir o rotulo.",
    )
    return redirect("fichaX", pk=pk)


@login_required
@require_POST
def atualizar_finalizada(request, pk):
    """BR-021: selo de finalizada é um toggle livre."""
    ficha = get_object_or_404(Ficha, pk=pk)
    ficha.finalizada = not ficha.finalizada
    ficha.save(update_fields=["finalizada"])
    return redirect("fichaX", pk=ficha.pk)


@login_required
@require_POST
def deletar_ficha(request, pk):
    """BR-020: exclusão em cascata (tabela, itens da receita, nutrientes extras)."""
    ficha = get_object_or_404(Ficha, pk=pk)
    nome = ficha.nomeFicha
    ficha.delete()
    messages.success(request, f'Ficha "{nome}" excluída.')
    return redirect("listaFichas")


# --------------------------------------------------------------------- membros


def eh_administrador(user) -> bool:
    """Papel administrativo da instância, definido por grupo do Django."""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name=settings.GRUPO_ADMINISTRADORES).exists()
    )


administrador_requerido = user_passes_test(eh_administrador, login_url="loginUser")


def registrar_membro(request):
    """BR-024 — auto-cadastro protegido pela chave da instância."""
    logout(request)  # BR-027: abrir a tela encerra a sessão atual
    form = MembroForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            usuario = User.objects.create_user(
                form.cleaned_data["nome"],
                password=form.cleaned_data["senha1"],
                email=form.cleaned_data["email"],
            )
            membro = form.save(commit=False)
            membro.usuario = usuario
            membro.save()
        messages.success(
            request, "Cadastro realizado com sucesso. Entre com seu nome e senha."
        )
        return redirect("loginUser")
    return render(request, "membro_form.html", {"form": form})


@login_required
def lista_membros(request):
    admin = eh_administrador(request.user)
    chave = Chave.objects.last() if admin else None
    return render(
        request,
        "membros_registrados.html",
        {
            "membros": Membro.objects.select_related("usuario").order_by(Lower("nome")),
            "ehAdmin": admin,
            "chave": chave.key if chave else None,
            "formChave": ChaveForm(),
            "formTrocaSenha": MudarSenhaForm(),
            "formApagaMembro": ApagarMembroForm(),
        },
    )


@administrador_requerido
@require_POST
def muda_chave(request):
    """BR-025 — trocar a chave insere uma nova linha (histórico preservado)."""
    form = ChaveForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Chave alterada com sucesso!")
    else:
        messages.error(request, "A chave não pôde ser alterada.")
    return redirect("listaMembros")


@administrador_requerido
@require_POST
def troca_senha(request):
    """BR-025 — administrador redefine a senha de qualquer membro."""
    form = MudarSenhaForm(request.POST)
    if form.is_valid():
        usuario = form.cleaned_data["usuario"]
        usuario.set_password(form.cleaned_data["nova_senha"])
        usuario.save()
        messages.success(request, f"Senha de {usuario.username} alterada com sucesso!")
    else:
        messages.error(request, f"A senha não pôde ser alterada: {_erros(form)}")
    return redirect("listaMembros")


@administrador_requerido
@require_POST
def deleta_membro(request):
    """BR-026 — exclui o membro transferindo fichas e ingredientes."""
    form = ApagarMembroForm(request.POST)
    if not form.is_valid():
        messages.error(request, f"O membro não pôde ser excluído: {_erros(form)}")
        return redirect("listaMembros")

    excluido = form.cleaned_data["membroExcluido"]
    destino = form.cleaned_data["membroDestino"]
    with transaction.atomic():
        ingredientes = Ingrediente.objects.filter(autorIng=excluido).update(autorIng=destino)
        fichas = Ficha.objects.filter(autor=excluido).update(autor=destino)
        excluido.usuario.delete()  # CASCADE remove o Membro
    messages.success(
        request,
        f"Transferidos {fichas} fichas e {ingredientes} ingredientes de "
        f"{excluido.nome} para {destino.nome}!",
    )
    return redirect("listaMembros")


def _erros(form) -> str:
    partes = []
    for campo, erros in form.errors.items():
        rotulo = form.fields[campo].label if campo in form.fields else campo
        partes.append(f"{rotulo}: {erros[0]}")
    return "; ".join(partes)


# ---------------------------------------------------------------- ingredientes


def _ingredientes_disponiveis():
    """BR-017/D-010: corte por ano é configuração da instância."""
    qs = Ingrediente.objects.all()
    config = ConfiguracaoInstancia.atual()
    if config and config.ano_corte_ingredientes:
        qs = qs.filter(dataCriacao__year__gte=config.ano_corte_ingredientes)
    return qs.order_by(Lower("nomeIng"))


@login_required
def lista_ingredientes(request):
    ingredientes = _ingredientes_disponiveis().select_related("autorIng")
    form_filtro = IngredienteFiltroForm(request.GET or None)
    if form_filtro.is_valid():
        # o filtro respeita o mesmo recorte da listagem (BR-017)
        dados = form_filtro.cleaned_data
        ingredientes = ingredientes.filter(
            contem_palavras("nomeIng", dados["f_nomeIng"])
            & contem_palavras("origemDosDados", dados["f_origemDosDados"])
            & contem_palavras("autorIng__nome", dados["f_autorIng"])
        )
    pagina, filtros = _paginar(request, ingredientes)
    return render(
        request,
        "ingredientes_registrados.html",
        {
            "ingredientes": pagina,
            "pagina": pagina,
            "filtrosQuery": filtros,
            "total": ingredientes.count(),
            "formFiltro": form_filtro,
        },
    )


def _campos_nutrientes(form):
    """Campos de nutrientes do formulário agrupados como numa tabela nutricional
    (GRUPOS_CADASTRO), com a unidade em que o valor é guardado."""
    def item(chave):
        n = POR_CHAVE[chave]
        return {
            "campo": form[chave],
            "rotulo": ROTULO_CADASTRO.get(chave) or n.rotulo,
            "unidade": unidade_armazenada(n),
        }

    grupos = [
        {"titulo": titulo, "campos": [item(c) for c in chaves if c in form.fields]}
        for titulo, chaves in GRUPOS_CADASTRO
    ]
    agrupados = {c for _, chaves in GRUPOS_CADASTRO for c in chaves}
    restantes = [item(n.chave) for n in NUTRIENTES
                 if n.chave in form.fields and n.chave not in agrupados]
    if restantes:
        grupos.append({"titulo": "Outros", "campos": restantes})
    return grupos


def _mesmo_nome_e_marca(form):
    """O mesmo nome pode existir com fontes/marcas diferentes."""
    return Ingrediente.objects.filter(
        nomeIng=form.cleaned_data["nomeIng"],
        origemDosDados=form.cleaned_data["origemDosDados"],
    )


MSG_INGREDIENTE_DUPLICADO = (
    "Já existe um ingrediente com esse nome e essa fonte / marca. "
    "Não foi possível realizar o cadastro."
)


@login_required
def registrar_ingrediente(request):
    form = IngredienteForm(request.POST or None)
    if form.is_valid():
        if _mesmo_nome_e_marca(form).exists():
            messages.error(request, MSG_INGREDIENTE_DUPLICADO)
        else:
            ingrediente = form.save(commit=False)
            servicos.normalizar_100g(ingrediente)
            ingrediente.save()
            messages.success(request, f"Ingrediente {ingrediente.nome_exibicao} cadastrado.")
            return redirect("listaIngredientes")
    return render(
        request,
        "ingrediente_form.html",
        {
            "form": form,
            "camposNutrientes": _campos_nutrientes(form),
            "leituraRotulo": leitura_rotulo.leitura_habilitada(),
        },
    )


@login_required
def editar_ingrediente(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    form = IngredienteForm(request.POST or None, instance=ingrediente)
    if request.method == "POST" and form.is_valid():
        if _mesmo_nome_e_marca(form).exclude(pk=ingrediente.pk).exists():
            messages.error(request, MSG_INGREDIENTE_DUPLICADO)
        else:
            atualizado = form.save(commit=False)
            servicos.normalizar_100g(atualizado)
            atualizado.save()
            # D-007: fichas existentes NÃO são recalculadas.
            messages.success(request, "Ingrediente atualizado.")
            return redirect("listaIngredientes")
    return render(
        request,
        "ingrediente_form.html",
        {
            "form": form,
            "ingrediente": ingrediente,
            "camposNutrientes": _campos_nutrientes(form),
        },
    )


@login_required
@require_POST
def ler_rotulo_ingrediente(request):
    """Lê a foto da tabela nutricional e devolve os campos para pré-preencher o
    formulário (JSON). Não salva nada: a pessoa revisa e salva."""
    foto = request.FILES.get("foto")
    if foto is None:
        return JsonResponse({"erro": "Envie a foto da tabela nutricional."}, status=400)
    if foto.size > settings.LEITURA_ROTULO_MAX_BYTES:
        return JsonResponse({"erro": "A foto passa de 15 MB. Envie uma menor."}, status=400)
    try:
        return JsonResponse(leitura_rotulo.ler_rotulo(foto.read()))
    except leitura_rotulo.LeituraIndisponivel:
        return JsonResponse({"erro": "A leitura por foto não está configurada."}, status=503)
    except leitura_rotulo.FalhaNaLeitura as erro:
        return JsonResponse({"erro": str(erro)}, status=422)


@login_required
@require_POST
def deletar_ingrediente(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    em_uso = Ficha_Ingrediente.objects.filter(ingrediente=ingrediente).count()
    nome = ingrediente.nome_exibicao
    ingrediente.delete()
    if em_uso:
        messages.warning(
            request,
            f'"{nome}" foi excluído e removido de {em_uso} receita(s) que o utilizavam.',
        )
    else:
        messages.success(request, f'Ingrediente "{nome}" excluído.')
    return redirect("listaIngredientes")


# Mapeamento fixo das colunas do TXT da TACO (BR-023)
COLUNAS_TACO = {
    "energiakcal": 4, "energiaKJ": 5, "proteinas": 6, "gordTotais": 7,
    "colesterol": 8, "carboidratos": 9, "fibras": 10, "calcio": 12,
    "magnesio": 13, "manganes": 15, "fosforo": 16, "ferro": 17, "sodio": 18,
    "potassio": 19, "cobre": 20, "zinco": 21, "retinol": 22, "RE": 23,
    "vitaminaARAE": 24, "tiamina": 25, "riboflavina": 26, "piridoxina": 27,
    "niancina": 28, "vitaminaC": 29, "gordSat": 31, "gordMono": 32, "gordPoli": 33,
}


@login_required
def upload(request):
    """BR-023 — importação em lote de ingredientes (TXT separado por TAB)."""
    if request.method != "POST":
        return render(request, "upload.html")

    arquivo = request.FILES.get("files")
    if arquivo is None or not arquivo.name.endswith(".txt"):
        messages.error(
            request, "Coloque um arquivo TXT separado por TAB (extraído do Excel desktop)."
        )
        return render(request, "upload.html")

    autor = Membro.objects.filter(usuario=request.user).first() or Membro.objects.first()
    if autor is None:
        messages.error(request, "Cadastre um membro antes de importar ingredientes.")
        return render(request, "upload.html")

    try:
        conteudo = arquivo.read().decode("utf-8")
    except UnicodeDecodeError:
        messages.error(request, "Não foi possível ler o arquivo: use codificação UTF-8.")
        return render(request, "upload.html")

    leitor = csv.reader(io.StringIO(conteudo), delimiter="\t", quotechar="|")
    next(leitor, None)  # cabeçalho

    criados = atualizados = 0
    erros: list[str] = []
    for numero, coluna in enumerate(leitor, start=2):
        if not coluna or not any(coluna):
            continue
        try:
            valores = {
                chave: float((coluna[indice] or "0").replace(",", "."))
                for chave, indice in COLUNAS_TACO.items()
            }
            # Gorduras trans = 18:1t + 18:2t (BR-023)
            valores["gordTrans"] = float((coluna[52] or "0").replace(",", ".")) + float(
                (coluna[53] or "0").replace(",", ".")
            )
            _, criado = Ingrediente.objects.update_or_create(
                nomeIng=coluna[2],
                origemDosDados=coluna[0],
                defaults={
                    "autorIng": autor,
                    "addManualmente": True,
                    "numRef": int(float(coluna[1] or 0)),
                    "dataCriacao": "2019-09-26",
                    **valores,
                },
            )
            criados += criado
            atualizados += not criado
        except (IndexError, ValueError) as erro:
            erros.append(f"linha {numero}: {erro}")

    for ingrediente in Ingrediente.objects.all():
        servicos.normalizar_100g(ingrediente)
        ingrediente.save()

    if criados or atualizados:
        messages.success(
            request,
            f"Importação concluída: {criados} ingrediente(s) criado(s), "
            f"{atualizados} atualizado(s).",
        )
    if erros:
        messages.warning(
            request,
            f"{len(erros)} linha(s) ignorada(s) por dados inválidos: " + "; ".join(erros[:5]),
        )
    return render(request, "upload.html")


# ---------------------------------------------------------------------- outros


PERGUNTAS_AJUDA = [
    {
        "pergunta": "Como cadastrar um novo usuário no sistema?",
        "resposta": [
            "Saia do usuário atual clicando em “Sair” no menu. Na tela de login, "
            "clique em “Cadastre-se”.",
            "Preencha os dados e informe a chave de cadastro — peça ao administrador.",
        ],
    },
    {
        "pergunta": "Como criar uma nova ficha?",
        "resposta": [
            "Na lista de fichas, clique em “Nova ficha”. O cadastro tem três etapas: "
            "dados base, receita e tabela nutricional.",
            "Os pesos informados na etapa 1 (peso total e peso da porção) são "
            "obrigatórios para adicionar ingredientes na etapa 2.",
        ],
    },
    {
        "pergunta": "Como adicionar novos ingredientes?",
        "resposta": [
            "Em “Ingredientes”, clique em “Novo ingrediente”. Você também pode cadastrar "
            "direto da etapa 2 da ficha, pelo botão “Cadastrar novo ingrediente”.",
            "Informe os nutrientes contidos na quantidade indicada — o sistema normaliza "
            "os valores para 100 g automaticamente.",
        ],
    },
    {
        "pergunta": "Posso editar uma ficha finalizada?",
        "resposta": [
            "Sim. O selo “Finalizada” é informativo e pode ser alternado a qualquer "
            "momento na tela do rótulo; ele não bloqueia a edição.",
        ],
    },
    {
        "pergunta": "Editar um ingrediente altera as fichas já criadas?",
        "resposta": [
            "Não. As fichas existentes preservam os valores calculados no momento em que "
            "foram editadas, para que rótulos já emitidos não mudem sozinhos.",
            "Para atualizar uma ficha com os novos valores do ingrediente, abra a ficha e "
            "salve novamente qualquer etapa — o recálculo acontece nesse momento.",
        ],
    },
    {
        "pergunta": "Como levar o rótulo para o Google Docs?",
        "resposta": [
            "Na tela do rótulo, use “Copiar conteúdo”: as duas tabelas (vertical e linear), "
            "a lista de ingredientes, os alérgicos e as lupas são copiados com formatação.",
            "Cole no documento com Ctrl+V (ou Cmd+V).",
        ],
    },
    {
        "pergunta": "O que são as lupas “ALTO EM”?",
        "resposta": [
            "São os selos de rotulagem frontal exigidos pela ANVISA. Aparecem "
            "automaticamente quando, por 100 g, o produto tem 15 g ou mais de açúcares "
            "adicionados, 6 g ou mais de gorduras saturadas, ou 600 mg ou mais de sódio.",
        ],
    },
]


@login_required
def ajuda(request):
    return render(request, "ajuda.html", {"perguntas": PERGUNTAS_AJUDA})


def _linhas_edicao(tabela):
    """Linhas da tela de edição da tabela (passo 3), a partir do registro."""
    linhas = []
    for n in NUTRIENTES:
        linhas.append(
            {
                "chave": n.chave,
                "rotulo": n.rotulo or "Valor energético (kJ)",
                "total": getattr(tabela, n.chave),
                "por_100g": getattr(tabela, f"{n.chave}_100g"),
                "por_porcao": getattr(tabela, f"{n.chave}_Porcao"),
                "arred": getattr(tabela, f"{n.chave}_Arred"),
                "vd": getattr(tabela, f"{n.chave}_VD"),
                "unidade": getattr(tabela, f"{n.chave}_unidadeMd"),
                "mostrar": getattr(tabela, f"{n.chave}_Mostrar"),
            }
        )
    return linhas
