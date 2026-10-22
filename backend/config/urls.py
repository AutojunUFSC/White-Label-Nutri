"""Rotas da aplicação."""
from django.contrib import admin
from django.urls import path

from apps.fichas import views
from apps.plataforma import views as views_plataforma

urlpatterns = [
    path("admin/", admin.site.urls),
    # Identidade visual da instância (guardada no banco — ver apps/plataforma).
    path("branding/logotipo", views_plataforma.logotipo_instancia, name="logotipoInstancia"),
    # Autenticação
    path("", views.login_user, name="loginUser"),
    path("loginUser", views.login_user, name="loginUser"),
    path("logoutUser", views.logout_user, name="logoutUser"),
    # Membros
    path("registrarMembro", views.registrar_membro, name="registrarMembro"),
    path("listaMembros", views.lista_membros, name="listaMembros"),
    path("mudaChave", views.muda_chave, name="mudaChave"),
    path("trocaSenha", views.troca_senha, name="trocaSenha"),
    path("deletaMembro", views.deleta_membro, name="deletaMembro"),
    # Fichas
    path("listaFichas", views.lista_fichas, name="listaFichas"),
    path("registrarFicha1", views.registrar_ficha_base, name="registrarFicha1"),
    path("registrarFicha1/<int:pk>", views.editar_ficha_base, name="editarFicha1"),
    path("registrarFicha2/<int:pk>", views.editar_ficha_receita, name="editarFicha2"),
    path("registrarFicha3/<int:pk>", views.editar_ficha_tabela, name="editarFicha3"),
    path("fichaX/<int:pk>", views.ficha_x, name="fichaX"),
    path("deletarFicha/<int:pk>", views.deletar_ficha, name="deletarFicha"),
    path("atualizarFinalizada/<int:pk>", views.atualizar_finalizada, name="atualizarFinalizada"),
    path("recalcularFicha/<int:pk>", views.recalcular_ficha, name="recalcularFicha"),
    # Receita
    path(
        "deletarItemReceita/<int:pk>/<int:id>/",
        views.deletar_item_receita,
        name="deletarItemReceita",
    ),
    path(
        "editarItemReceita/<int:pk>/<int:id>/",
        views.editar_item_receita,
        name="editarItemReceita",
    ),
    # Nutrientes da tabela
    path(
        "deletarNutrienteExtra/<int:pk>",
        views.deletar_nutriente_extra,
        name="deletarNutrienteExtra",
    ),
    path(
        "atualizarMostrar/<int:pk>/<str:item>/",
        views.atualizar_mostrar,
        name="atualizarMostrar",
    ),
    # Ingredientes
    path("listaIngredientes", views.lista_ingredientes, name="listaIngredientes"),
    path("registrarIngrediente", views.registrar_ingrediente, name="registrarIngrediente"),
    path("editarIngrediente/<int:pk>", views.editar_ingrediente, name="editarIngrediente"),
    path("deletarIngrediente/<int:pk>", views.deletar_ingrediente, name="deletarIngrediente"),
    path("lerRotuloIngrediente", views.ler_rotulo_ingrediente, name="lerRotuloIngrediente"),
    path("upload", views.upload, name="upload"),
    # Outros
    path("ajuda", views.ajuda, name="ajuda"),
]
