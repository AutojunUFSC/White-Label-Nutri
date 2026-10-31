"""Verificações da instância, executadas pelo `manage.py check` e no deploy."""
from django.core.checks import Warning, register


@register()
def instancia_esta_configurada(app_configs, **kwargs):
    """Avisa quando a instância está sem configuração white-label.

    Sem ela o sistema assume os padrões — nome genérico e, principalmente,
    NENHUM ano de corte de ingredientes. A lista volta a mostrar itens antigos
    que a empresa esconde de propósito (BR-017). Como isso não quebra nada,
    passaria despercebido até alguém estranhar a lista; daí o aviso.
    """
    from django.db import DatabaseError, connection

    from apps.plataforma.models import ConfiguracaoInstancia

    try:
        # Em banco novo o check roda antes das migrations: não há o que conferir.
        if ConfiguracaoInstancia._meta.db_table not in connection.introspection.table_names():
            return []
        if ConfiguracaoInstancia.objects.exists():
            return []
    except DatabaseError:
        # Banco indisponível (ex.: build que só coleta estáticos). Sem veredito.
        return []

    return [
        Warning(
            "Esta instância não tem configuração white-label.",
            hint=(
                # Sem seta nem travessão: o console do Windows não os representa e
                # o aviso sai ilegível justamente onde precisa ser lido.
                "Crie em /admin/ -> Configuração da instância: nome da empresa, cor "
                "e, se ela esconde ingredientes antigos, o ano de corte. "
                "Em instância nova, o comando bootstrap_instancia já cria."
            ),
            id="plataforma.W001",
        )
    ]