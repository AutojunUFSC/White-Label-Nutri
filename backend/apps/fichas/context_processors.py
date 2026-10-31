from apps.fichas.views import SESSAO_TOUR, eh_administrador


def tour(request):
    """Tour de boas-vindas: abre sozinho no primeiro acesso e sob demanda na Ajuda.

    A marca da sessão é consumida na primeira tela renderizada depois do login, então
    o tour não volta a abrir sozinho. Fora dessas duas situações o contexto fica vazio
    e o template não carrega nem o HTML nem o script do tour.
    """
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    automatico = bool(request.session.pop(SESSAO_TOUR, False))
    rota = request.resolver_match.url_name if request.resolver_match else None
    if not (automatico or rota == "ajuda"):
        return {}
    return {
        "tour_presente": True,
        "tour_automatico": automatico,
        "tour_administrador": eh_administrador(usuario),
    }
