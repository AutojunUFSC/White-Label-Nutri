from django.urls import reverse

from apps.fichas.tour import passos
from apps.fichas.views import SESSAO_TOUR, eh_administrador
from apps.plataforma.context_processors import instancia


def tour(request):
    """Entrega o roteiro do tour de boas-vindas quando ele pode começar.

    Isso acontece no primeiro acesso (a marca da sessão é consumida na primeira tela
    exibida depois do login, então o tour não volta a começar sozinho) e na página de
    Ajuda, onde o botão "Ver o tour de novo" o reinicia. Fora daí o contexto fica vazio:
    o script do tour só retoma um passeio que já começou, guardado na aba do navegador.
    """
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    automatico = bool(request.session.pop(SESSAO_TOUR, False))
    rota = request.resolver_match.url_name if request.resolver_match else None
    if not (automatico or rota == "ajuda"):
        return {}
    return {
        "tour_dados": {
            "automatico": automatico,
            "inicio": reverse("listaFichas"),
            "passos": passos(instancia(request)["instancia_nome"], eh_administrador(usuario)),
        }
    }
